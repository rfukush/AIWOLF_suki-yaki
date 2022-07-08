#
# sample.py
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

from aiwolf import AbstractPlayer, Agent, Content, GameInfo, GameSetting, Role, Status

from bodyguard import SampleBodyguard
from medium import SampleMedium
from possessed import SamplePossessed
from seer import SampleSeer
from villager import SampleVillager
from werewolf import SampleWerewolf
import logging
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('suki-yaki/test.log/sample')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s  %(asctime)s  [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) 

class SamplePlayer(AbstractPlayer):

    villager: AbstractPlayer
    bodyguard: AbstractPlayer
    medium: AbstractPlayer
    seer: AbstractPlayer
    possessed: AbstractPlayer
    werewolf: AbstractPlayer
    player: AbstractPlayer

    def __init__(self) -> None:
        self.villager = SampleVillager()
        self.bodyguard = SampleBodyguard()
        self.medium = SampleMedium()
        self.seer = SampleSeer()
        self.possessed = SamplePossessed()
        self.werewolf = SampleWerewolf()
        self.player = self.villager
        self.firstgameflag =   1
        self.countflag = 1


    def attack(self) -> Agent:
        return self.player.attack()

    def day_start(self) -> None:
        self.player.day_start()

    def divine(self) -> Agent:
        return self.player.divine()

    def finish(self) -> None:
        df_t = self.w_win.T
        self.w_p = (df_t/df_t.sum()).T
        df_t1 = self.v_win.T
        self.v_p = (df_t1/df_t1.sum()).T
        self.countflag += 1
        self.player.finish(self.w_win,self.v_win,self.w_p, self.v_p,self.countflag)

    def guard(self) -> Agent:
        return self.player.guard()

    def initialize(self, game_info: GameInfo, game_setting: GameSetting) -> None:
        role: Role = game_info.my_role
        logger.debug('initialize0')
        self.winner = 'villagers'
        self.finish_flag = 0
        if self.firstgameflag == 1:
            self.w_win = pd.DataFrame(index=game_info.agent_list, columns=['werewolves_win','werewolves_lose'], dtype=float)
            self.w_win[:] = 0
            self.v_win = pd.DataFrame(index=game_info.agent_list, columns=['villagers_win','villagers_lose'], dtype=float)
            self.v_win[:] = 0
            self.firstgameflag = 0
            df_t = self.w_win.T
            self.w_p = (df_t/df_t.sum()).T
            df_t1 = self.w_win.T
            self.v_p = (df_t1/df_t1.sum()).T

        if role == Role.VILLAGER:
            self.player = self.villager
        elif role == Role.BODYGUARD:
            self.player = self.bodyguard
        elif role == Role.MEDIUM:
            self.player = self.medium
        elif role == Role.SEER:
            self.player = self.seer
        elif role == Role.POSSESSED:
            self.player = self.possessed
        elif role == Role.WEREWOLF:
            self.player = self.werewolf
        self.player.initialize(game_info, game_setting)
        #logger.debug(self.win)

    def talk(self) -> Content:
        return self.player.talk()

    def update(self, game_info: GameInfo) -> None:

        for agent in game_info.status_map:
            #logger.debug(agent)
            status = game_info.status_map[agent]
            if agent in game_info.role_map:
                role = game_info.role_map[agent]
                if len(game_info.role_map) == len(game_info.agent_list):
                    logger.debug('finish')
                    self.finish_flag = 1
                    #logger.debug(status)
                    if status == Status.ALIVE and ( role == Role.WEREWOLF or role == Role.POSSESSED ):
                        self.winner = 'werewolves'
                

        if self.finish_flag == 1 :
            logger.debug('finish')
            logger.debug(f'me {game_info.me}')
            for agent in game_info.status_map:
                status = game_info.status_map[agent]
                role = game_info.role_map[agent]
                logger.debug(agent)
                logger.debug(status)
                logger.debug(role)
                if  role == Role.WEREWOLF or role == Role.POSSESSED :
                    if self.winner == 'werewolves':
                        self.w_win.at[agent, 'werewolves_win'] += 1

                    else:
                        self.w_win.at[agent, 'werewolves_lose'] += 1
                else:
                    if self.winner == 'villagers':
                        self.v_win.at[agent, 'villagers_win'] += 1
                    else:
                        self.v_win.at[agent, 'villagers_lose'] += 1

        self.player.update(game_info, self.w_p, self.v_p)

    def vote(self) -> Agent:
        return self.player.vote()

    def whisper(self) -> Content:
        return self.player.whisper()
