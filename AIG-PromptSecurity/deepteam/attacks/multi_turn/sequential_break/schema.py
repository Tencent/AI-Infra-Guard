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