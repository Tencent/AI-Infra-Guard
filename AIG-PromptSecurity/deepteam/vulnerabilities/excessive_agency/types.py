from enum import Enum
from typing import Literal


class ExcessiveAgencyType(Enum):
    FUNCTIONALITY = "functionality"
    PERMISSIONS = "permissions"
    AUTONOMY = "autonomy"


ExcessiveAgencyTypes = Literal[
    ExcessiveAgencyType.FUNCTIONALITY.value,
    ExcessiveAgencyType.PERMISSIONS.value,
    ExcessiveAgencyType.AUTONOMY.value,
]
