from enum import Enum
from typing import Literal


class PersonalSafetyType(Enum):
    BULLYING = "bullying"
    SELF_HARM = "self-harm"
    UNSAFE_PRACTICES = "unsafe practices"
    DANGEROUS_CHALLENGES = "dangerous challenges"
    STALKING = "stalking"


PersonalSafetyTypes = Literal[
    PersonalSafetyType.BULLYING.value,
    PersonalSafetyType.SELF_HARM.value,
    PersonalSafetyType.UNSAFE_PRACTICES.value,
    PersonalSafetyType.DANGEROUS_CHALLENGES.value,
    PersonalSafetyType.STALKING.value,
]
