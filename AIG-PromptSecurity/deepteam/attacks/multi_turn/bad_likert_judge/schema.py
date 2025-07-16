from typing import Literal
from pydantic import BaseModel


class LikertScore(BaseModel):
    score: int
    reasoning: str


class LikertExamples(BaseModel):
    score_1_example: str
    score_3_example: str


class RefinedExample(BaseModel):
    refined_example: str


class NonRefusal(BaseModel):
    classification: Literal["Non-refusal", "Refusal"]


class BLJJudge(BaseModel):
    classification: Literal["Harmful", "Not harmful"]
    reasoning: str 