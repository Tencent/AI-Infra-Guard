from enum import Enum
from typing import Literal


class UnauthorizedAccessType(Enum):
    BFLA = "bfla"
    BOLA = "bola"
    RBAC = "rbac"
    DEBUG_ACCESS = "debug access"
    SHELL_INJECTION = "shell injection"
    SQL_INJECTION = "sql injection"
    SSRF = "ssrf"


UnauthorizedAccessTypes = Literal[
    UnauthorizedAccessType.BFLA.value,
    UnauthorizedAccessType.BOLA.value,
    UnauthorizedAccessType.RBAC.value,
    UnauthorizedAccessType.DEBUG_ACCESS.value,
    UnauthorizedAccessType.SHELL_INJECTION.value,
    UnauthorizedAccessType.SQL_INJECTION.value,
    UnauthorizedAccessType.SSRF.value,
]
