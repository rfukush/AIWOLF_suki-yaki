#
# seer.py
#
# Copyright 2022 OTSUKI Takashi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import deque
from typing import Deque, List, Optional

from aiwolf import (Agent, ComingoutContentBuilder, Content,
                    DivinedResultContentBuilder, GameInfo, GameSetting, Judge,
                    Role, Species, VoteContentBuilder)
from aiwolf.constant import AGENT_NONE

from const import CONTENT_SKIP
from villager import SampleVillager
import logging



""" logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('test.log/seer')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s  %(asctime)s  [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) """


class SampleSeer(SampleVillager):
    """Sample seer agent."""

    co_date: int
    """Scheduled comingout date."""
    has_co: bool
    """Whether or not comingout has done."""
    my_judge_queue: Deque[Judge]
    """Queue of divination results."""
    not_divined_agents: List[Agent]
    """Agents that have not been divined."""
    werewolves: List[Agent]
    """Found werewolves."""

    def __init__(self) -> None:
        """Initialize a new instance of SampleSeer."""
        super().__init__()
        self.co_date = 0
        self.has_co = False
        self.my_judge_queue = deque()
        self.not_divined_agents = []
        self.werewolves = []
        self.divine_candidate = AGENT_NONE

    def initialize(self, game_info: GameInfo, game_setting: GameSetting) -> None:
        super().initialize(game_info, game_setting)
        self.co_date = 3
        self.has_co = False
        self.my_judge_queue.clear()
        self.not_divined_agents = self.get_others(self.game_info.agent_list)
        self.werewolves.clear()

    def day_start(self) -> None:
        super().day_start()
        # Process a divination result.
        judge: Optional[Judge] = self.game_info.divine_result
        """ logger.debug(judge)
        logger.debug(f'judge_queue  {self.my_judge_queue}') """
        if judge is not None:
            self.my_judge_queue.append(judge)
            if judge.target in self.not_divined_agents:
                self.not_divined_agents.remove(judge.target)
            if judge.result == Species.WEREWOLF:
                self.werewolves.append(judge.target)
                self.prob.at[judge.target, Role.WEREWOLF] = 1
            else:
                if len(self.game_info.agent_list) == 5:
                    self.prob.at[judge.target, Role.VILLAGER] = 0.7
                    self.prob.at[judge.target, Role.WEREWOLF] = 0
                else:
                    self.prob.at[judge.target, Role.VILLAGER] = 0.9
                    self.prob.at[judge.target, Role.WEREWOLF] = 0

    def update(self, game_info) -> None:
        super().update(game_info)
        if Role.SEER in self.comingout_map.values():
            self.fake_seers = [k for k, v in self.comingout_map.items() if v == Role.SEER]
            for fake_seer in self.fake_seers:
                if fake_seer in self.not_divined_agents:
                    self.not_divined_agents.remove(fake_seer)

    def talk(self) -> Content:
        # Do comingout if it's on scheduled day or a werewolf is found.
        if not self.has_co and (self.game_info.day == self.co_date or self.werewolves):
            self.has_co = True
            return Content(ComingoutContentBuilder(self.me, Role.SEER))
        # Report the divination result after doing comingout.
        if self.has_co and self.my_judge_queue:
            judge: Judge = self.my_judge_queue.popleft()
            return Content(DivinedResultContentBuilder(judge.target, judge.result))
        # Vote for one of the alive werewolves.
        candidates: List[Agent] = self.get_alive(self.werewolves)
        # Vote for one of the alive fake seers if there are no candidates.
        if not candidates:
            candidates = self.get_alive([a for a in self.comingout_map
                                         if self.comingout_map[a] == Role.SEER])
        # Vote for one of the alive agents if there are no candidates.
        # Declare which to vote for if not declare yet or the candidate is changed.
        if self.vote_candidate == AGENT_NONE or self.vote_candidate not in candidates:
            if candidates:
                self.vote_candidate = self.random_select(candidates)
            else:
                if self.strong_vote:
                    self.vote_candidate = self.strong_vote[-1]
                else:
                    self.vote_candite = self.strong_agent
            if self.vote_candidate != AGENT_NONE:
                return Content(VoteContentBuilder(self.vote_candidate))
        return CONTENT_SKIP

        
    def divine(self) -> Agent:
        # Divine a agent randomly chosen from undivined agents.[]
        if self.strong_agent in self.not_divined_agents:
            self.divine_candidate = self.strong_agent
        else:
            self.divine_candidate = self.random_select(self.not_divined_agents)
        type00=type(self.divine_candidate).__name__
        if type00 == 'Series':
            self.divine_candidate = self.divine_candidate[0]
        """logger.debug(self.prob)
        logger.debug(f'divine_candidate {self.divine_candidate}') """
        #target: Agent = self.random_select(self.not_divined_agents)
        #return target if target != AGENT_NONE else self.me
        return self.divine_candidate if self.divine_candidate != AGENT_NONE else self.random_select(self.not_divined_agents)
