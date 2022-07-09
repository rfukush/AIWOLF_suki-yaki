#
# villager.py
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

import random
import numpy as np
import pandas as pd
from typing import Dict, List


from aiwolf import (AbstractPlayer, Agent, Content, GameInfo, GameSetting,
                    Judge, Role, Species, Status, Talk, Topic,
                    VoteContentBuilder)
from aiwolf.constant import AGENT_NONE

from const import CONTENT_SKIP
import logging



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('suki-yaki/test.log/villager')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s  %(asctime)s  [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class SampleVillager(AbstractPlayer):
    """Sample villager agent."""

    me: Agent
    """Myself."""
    my_role: Role
    "My role"
    vote_candidate: Agent
    """Candidate for voting."""
    game_info: GameInfo
    """Information about current game."""
    game_setting: GameSetting
    """Settings of current game."""
    comingout_map: Dict[Agent, Role]
    """Mapping between an agent and the role it claims that it is."""
    divination_reports: List[Judge]
    """Time series of divination reports."""
    identification_reports: List[Judge]
    """Time series of identification reports."""
    talk_list_head: int
    """Index of the talk to be analysed next."""

    def __init__(self) -> None:
        """Initialize a new instance of SampleVillager."""

        self.me = AGENT_NONE
        self.vote_candidate = AGENT_NONE
        self.game_info = None  # type: ignore
        self.comingout_map = {}
        self.divination_reports = []
        self.identification_reports = []
        self.talk_list_head = 0
        self.strong_agent_v = AGENT_NONE
        self.strong_agent_w = AGENT_NONE

    def is_alive(self, agent: Agent) -> bool:
        """Return whether the agent is alive.

        Args:
            agent: The agent.

        Returns:
            True if the agent is alive, otherwise false.
        """
        return self.game_info.status_map[agent] == Status.ALIVE

    def get_others(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of agents excluding myself from the given list of agents.

        Args:
            agent_list: The list of agent.

        Returns:
            A list of agents excluding myself from agent_list.
        """
        return [a for a in agent_list if a != self.me]

    def get_alive(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of alive agents contained in the given list of agents.

        Args:
            agent_list: The list of agents.

        Returns:
            A list of alive agents contained in agent_list.
        """
        return [a for a in agent_list if self.is_alive(a)]

    def get_alive_others(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of alive agents that is contained in the given list of agents
        and is not equal to myself.

        Args:
            agent_list: The list of agents.

        Returns:
            A list of alive agents that is contained in agent_list
            and is not equal to mysef.
        """
        return self.get_alive(self.get_others(agent_list))

    def random_select(self, agent_list: List[Agent]) -> Agent:
        """Return one agent randomly chosen from the given list of agents.

        Args:
            agent_list: The list of agents.

        Returns:
            A agent randomly chosen from agent_list.
        """
        return random.choice(agent_list) if agent_list else AGENT_NONE

    def initialize(self, game_info: GameInfo, game_setting: GameSetting) -> None:
        self.game_info = game_info
        self.game_setting = game_setting
        self.me = game_info.me
        self.my_role = game_info.role_map[self.me]
        self.winner = 'villagers'
        self.first_updateflag = 1
        if len(self.game_info.agent_list) == 5:
            self.role_list = [Role.VILLAGER, Role.SEER, Role.POSSESSED, Role.WEREWOLF]
            self.prob = pd.DataFrame(index=self.game_info.agent_list, columns=self.role_list, dtype=float)
            self.prob[:] = 0.5
            self.prob.at[self.me, self.my_role] = 1
        else:
            self.role_list = [Role.VILLAGER, Role.SEER, Role.MEDIUM, Role.BODYGUARD, Role.WEREWOLF, Role.POSSESSED]
            self.prob = pd.DataFrame(index=self.game_info.agent_list, columns=self.role_list, dtype=float)
            self.prob[:] = 0.5
            self.prob.at[self.me, self.my_role] = 1

        """logger.debug('initialize')
        logger.debug(f'me {self.me}')
        logger.debug(f'my role {self.my_role}')
        logger.debug(f'prob  {self.prob}') """
        # Clear fields not to bring in information from the last game.
        self.comingout_map.clear()
        self.divination_reports.clear()
        self.identification_reports.clear()


    def day_start(self) -> None:
        self.talk_list_head = 0
        self.vote_candidate = AGENT_NONE
        self.strong_vote = []
        self.strong_vote_w = []
        for agent in self.game_info.agent_list:
            if agent not in self.get_alive(self.game_info.agent_list):
                #logger.debug(agent)
                #logger.debug(self.prob.loc[agent])
                self.prob.loc[agent] = np.nan
            
    def update(self, game_info: GameInfo, w_p, v_p, countflag) -> None:
        if self.first_updateflag == 1:
            self.first_updateflag *= 0
            #logger.debug(f'wp {w_p}')
            #logger.debug(f'vp {v_p}')
            self.strong_agent_v = v_p["villagers_win"].idxmax()
            self.strong_agent_w = w_p["werewolves_win"].idxmax()
        self.game_info = game_info  # Update game information.
        """ logger.debug('update')
        logger.debug(f'me {self.game_info.me}')
        logger.debug(f'day {self.game_info.day}')
        logger.debug(f'attacked_agent {self.game_info.attacked_agent}') """
        for i in range(self.talk_list_head, len(game_info.talk_list)):  # Analyze talks that have not been analyzed yet.
            tk: Talk = game_info.talk_list[i]  # The talk to be analyzed.
            talker: Agent = tk.agent
            if talker == self.me:  # Skip my talk.
                continue
            content: Content = Content.compile(tk.text)
            if content.topic == Topic.COMINGOUT:
                self.comingout_map[talker] = content.role
            elif content.topic == Topic.DIVINED:
                self.divination_reports.append(Judge(talker, game_info.day, content.target, content.result))
            elif content.topic == Topic.IDENTIFIED:
                self.identification_reports.append(Judge(talker, game_info.day, content.target, content.result))
            #elif content.topic == Topic.OPERATOR:
                #self.strong_agent = talker
                #logger.debug(f'strong agent {self.strong_agent}')
            elif content.topic == Topic.VOTE:
                if content.subject == self.strong_agent_v:
                    logger.debug(self)
                    logger.debug(self.strong_vote)
                    self.strong_vote.append(content.target)
                elif content.subject == self.strong_agent_w:
                    self.strong_vote_w.append(content.target)
        self.talk_list_head = len(game_info.talk_list)  # All done.

    def talk(self) -> Content:
        #logger.debug(f'candidate {self.vote_candidate}')
        # Choose an agent to be voted for while talking.
        #
        # The list of fake seers that reported me as a werewolf.
        self.fake_seers: List[Agent] = [j.agent for j in self.divination_reports
                                   if j.target == self.me and j.result == Species.WEREWOLF]
        # Vote for one of the alive agents that were judged as werewolves by non-fake seers.
        self.reported_wolves: List[Agent] = [j.target for j in self.divination_reports
                                        if j.agent not in self.fake_seers and j.result == Species.WEREWOLF]
        candidates: List[Agent] = self.get_alive_others(self.fake_seers)
        #logger.debug(candidates)
        for candidate in candidates:
            self.prob.at[candidate, Role.WEREWOLF] = 0.8
            self.vote_candidate = candidate
        
        if self.my_role == Role.VILLAGER:
            for fake_seer in self.fake_seers:
                self.prob.at[fake_seer, Role.WEREWOLF] = 1

        # Declare which to vote for if not declare yet or the candidate is changed.
        if self.vote_candidate == AGENT_NONE or self.vote_candidate not in candidates:
            """self.vote_candidate = self.prob[Role.WEREWOLF].idxmax()
            type00=type(self.vote_candidate).__name__
            if type00 == 'Series':
                self.vote_candidate = self.vote_candidate[0] """
            if self.strong_vote:
                self.vote_candidate = self.strong_vote[-1]
            else:
                self.vote_candite = self.strong_agent_w
            if self.vote_candidate != AGENT_NONE:
                return Content(VoteContentBuilder(self.vote_candidate))
        return CONTENT_SKIP

    def vote(self) -> Agent:
        if self.vote_candidate == AGENT_NONE:
            if self.strong_vote:
                self.vote_candidate = self.strong_vote[-1]
            else:
                self.vote_candite = self.strong_agent_w
        type00=type(self.vote_candidate).__name__
        if type00 == 'Series':
            self.vote_candidate = self.vote_candidate[0]
        return self.vote_candidate if self.vote_candidate != AGENT_NONE else self.me

    def attack(self) -> Agent:
        raise NotImplementedError()

    def divine(self) -> Agent:
        raise NotImplementedError()

    def guard(self) -> Agent:
        raise NotImplementedError()

    def whisper(self) -> Content:
        raise NotImplementedError()

    def finish(self,w_win,v_win,w_p,v_p, countflag) -> None:
        self.w_win = w_win
        self.v_win = v_win
        self.countflag = countflag
