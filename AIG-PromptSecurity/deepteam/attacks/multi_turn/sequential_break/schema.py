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

from typing import Literal, Optional
from pydantic import BaseModel


# Literal types for better autocomplete and docs
SequentialJailbreakTypeLiteral = Literal["dialogue", "question_bank", "game_environment"]

DialogueTypeLiteral = Literal[
    "prisoner",
    "student", 
    "researcher",
    "generic"
]


class RewrittenDialogue(BaseModel):
    paraphrased_version: str


class DialogueJudge(BaseModel):
    classification: Literal["Harmful", "Not harmful"]


class QuestionBankJudge(BaseModel):
    classification: Literal["Harmful", "Not harmful"]


class GameEnvironmentJudge(BaseModel):
    classification: Literal["Harmful", "Not harmful"]


class NonRefusal(BaseModel):
    classification: Literal["Non-refusal", "Refusal"] 