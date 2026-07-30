# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
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
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

from pydantic import BaseModel
from tqdm import tqdm

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.actor_attack.schema import (
    ActorNetwork,
    FollowUpQuestion,
    NonRefusal,
    Rating,
)
from deepteam.attacks.multi_turn.actor_attack.template import (
    ActorAttackTemplate,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType


class ActorAttack(BaseAttack):
    """
    ActorAttack / ActorBreaker (Ren et al., 2024)
    参考: https://arxiv.org/abs/2410.10700

    基于行动者网络理论构造若干与攻击目标存在隐性关联、但表面完全无关的『行动者』
    话题分支；从中选取一条分支，沿其逐步展开多轮追问，利用已建立的良性叙事语境，
    在最后一轮把问题收束到真正的隐藏目标上。相比 Crescendo 的单路径升温，
    ActorAttack 强调先探索多条候选路径（多个 actor），再选择最合适的一条深挖。
    """

    def __init__(
        self,
        weight: int = 1,
        num_actors: int = 3,
        max_turns_per_actor: int = 4,
    ):
        self.weight = weight
        self.num_actors = max(num_actors, 1)
        self.max_turns_per_actor = max(max_turns_per_actor, 2)

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=self.max_turns_per_actor * 3,
            desc="...... 🎭 ActorAttack",
            leave=False,
        )

        try:
            # 1st step: 构造行动者网络，选取第一个候选分支深挖
            network_prompt = ActorAttackTemplate.generate_actor_network(
                attack, self.num_actors
            )
            actor_network: ActorNetwork = self._generate_schema(
                network_prompt, ActorNetwork
            )
            pbar.update(1)

            if not actor_network.actors:
                pbar.close()
                return attack

            actor = actor_network.actors[0]
            current_message = actor.opening_question
            best_message = attack
            best_score = 0
            last_response = ""

            for turn_num in range(1, self.max_turns_per_actor + 1):
                try:
                    target_response = model_callback(current_message)
                    pbar.update(1)

                    non_refusal_prompt = ActorAttackTemplate.non_refusal(
                        attack, target_response
                    )
                    non_refusal_res: NonRefusal = self._generate_schema(
                        non_refusal_prompt, NonRefusal
                    )

                    if non_refusal_res.classification == "Refusal":
                        score = 1
                    else:
                        judge_prompt = ActorAttackTemplate.judge(
                            attack, current_message, target_response
                        )
                        rating_res: Rating = self._generate_schema(
                            judge_prompt, Rating
                        )
                        score = rating_res.rating
                    pbar.update(1)

                    if score > best_score:
                        best_score = score
                        best_message = current_message

                    last_response = target_response
                    if score >= 10 or turn_num == self.max_turns_per_actor:
                        break

                    probe_prompt = ActorAttackTemplate.next_probe_prompt(
                        attack,
                        actor.actor_name,
                        actor.relation_to_goal,
                        turn_num + 1,
                        self.max_turns_per_actor,
                        last_response,
                    )
                    follow_up: FollowUpQuestion = self._generate_schema(
                        probe_prompt, FollowUpQuestion
                    )
                    current_message = follow_up.next_question
                    pbar.update(1)
                except Exception:
                    continue

            pbar.close()
            return best_message
        except Exception:
            pbar.close()
            return attack

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=self.max_turns_per_actor * 3,
            desc="...... 🎭 ActorAttack",
            leave=False,
        )

        try:
            network_prompt = ActorAttackTemplate.generate_actor_network(
                attack, self.num_actors
            )
            actor_network: ActorNetwork = await self._a_generate_schema(
                network_prompt, ActorNetwork
            )
            pbar.update(1)

            if not actor_network.actors:
                pbar.close()
                return attack

            actor = actor_network.actors[0]
            current_message = actor.opening_question
            best_message = attack
            best_score = 0
            last_response = ""

            for turn_num in range(1, self.max_turns_per_actor + 1):
                try:
                    target_response = await model_callback(current_message)
                    pbar.update(1)

                    non_refusal_prompt = ActorAttackTemplate.non_refusal(
                        attack, target_response
                    )
                    non_refusal_res: NonRefusal = await self._a_generate_schema(
                        non_refusal_prompt, NonRefusal
                    )

                    if non_refusal_res.classification == "Refusal":
                        score = 1
                    else:
                        judge_prompt = ActorAttackTemplate.judge(
                            attack, current_message, target_response
                        )
                        rating_res: Rating = await self._a_generate_schema(
                            judge_prompt, Rating
                        )
                        score = rating_res.rating
                    pbar.update(1)

                    if score > best_score:
                        best_score = score
                        best_message = current_message

                    last_response = target_response
                    if score >= 10 or turn_num == self.max_turns_per_actor:
                        break

                    probe_prompt = ActorAttackTemplate.next_probe_prompt(
                        attack,
                        actor.actor_name,
                        actor.relation_to_goal,
                        turn_num + 1,
                        self.max_turns_per_actor,
                        last_response,
                    )
                    follow_up: FollowUpQuestion = await self._a_generate_schema(
                        probe_prompt, FollowUpQuestion
                    )
                    current_message = follow_up.next_question
                    pbar.update(1)
                except Exception:
                    continue

            pbar.close()
            return best_message
        except Exception:
            pbar.close()
            return attack

    ##################################################
    ### Utils ########################################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "ActorAttack"
