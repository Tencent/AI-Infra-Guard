from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.illegal_activity import IllegalActivityType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

IllegalActivityLiteral = Literal[
    "weapons",
    "illegal drugs",
    "violent crimes",
    "non violent crimes",
    "sex crimes",
    "cybercrime",
    "child exploitation",
]


class IllegalActivity(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[IllegalActivityLiteral]] = [
            type.value for type in IllegalActivityType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=IllegalActivityType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Illegal Activity"
