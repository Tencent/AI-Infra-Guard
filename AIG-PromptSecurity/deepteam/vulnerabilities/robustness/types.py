from enum import Enum
from typing import Literal


class RobustnessType(Enum):
    INPUT_OVERRELIANCE = "input overreliance"
    HIJACKING = "hijacking"


RobustnessTypes = Literal[
    RobustnessType.INPUT_OVERRELIANCE.value, RobustnessType.HIJACKING.value
]
