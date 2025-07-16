from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.robustness import RobustnessType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

RobustnessLiteral = Literal["input overreliance", "hijacking"]


class Robustness(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[RobustnessLiteral]] = [
            type.value for type in RobustnessType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=RobustnessType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Robustness"
