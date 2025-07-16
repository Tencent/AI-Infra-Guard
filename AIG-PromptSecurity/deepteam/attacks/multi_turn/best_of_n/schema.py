from typing import Literal
from pydantic import BaseModel

class NonRefusal(BaseModel):
    answer: Literal["Yes", "No"] 
