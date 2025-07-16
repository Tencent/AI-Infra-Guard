from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.intellectual_property import (
    IntellectualPropertyType,
)
from deepteam.vulnerabilities.utils import validate_vulnerability_types

IntellectualPropertyLiteral = Literal[
    "imitation",
    "copyright violations",
    "trademark infringement",
    "patent disclosure",
]


class IntellectualProperty(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[IntellectualPropertyLiteral]] = [
            type.value for type in IntellectualPropertyType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=IntellectualPropertyType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Intellectual Property"
