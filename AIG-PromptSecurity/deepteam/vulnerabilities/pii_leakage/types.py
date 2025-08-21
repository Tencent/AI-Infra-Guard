from enum import Enum
from typing import Literal


class PIILeakageType(Enum):
    DATABASE_ACCESS = "api and database access"
    DIRECT = "direct disclosure"
    SESSION_LEAK = "session leak"
    SOCIAL_MANIPULATION = "social manipulation"


PIILeakageTypes = Literal[
    PIILeakageType.DATABASE_ACCESS.value,
    PIILeakageType.DIRECT.value,
    PIILeakageType.SESSION_LEAK.value,
    PIILeakageType.SOCIAL_MANIPULATION.value,
]
