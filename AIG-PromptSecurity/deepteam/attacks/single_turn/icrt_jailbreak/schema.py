from typing import Literal, Optional
from pydantic import BaseModel


class IntentData(BaseModel):
    structural_intent: str | None = None
    harmful_behavior: str | None = None

class ConceptDecompositionData(BaseModel):
    sub_concepts: list | None = None

class SafeConstraintData(BaseModel):
    filtered_sub_concepts: list | None = None

class ConceptReassemblyData(BaseModel):
    selected_sub_concepts: list | None = None
