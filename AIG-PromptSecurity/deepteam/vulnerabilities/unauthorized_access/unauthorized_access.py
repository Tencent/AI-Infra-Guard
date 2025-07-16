from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.unauthorized_access import UnauthorizedAccessType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

UnauthorizedAccessLiteral = Literal[
    "bfla",
    "bola",
    "rbac",
    "debug access",
    "shell injection",
    "sql injection",
    "ssrf",
]


class UnauthorizedAccess(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[UnauthorizedAccessLiteral]] = [
            type.value for type in UnauthorizedAccessType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=UnauthorizedAccessType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Unauthorized Access"
