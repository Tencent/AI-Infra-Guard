from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.toxicity import ToxicityType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

ToxicityLiteral = Literal["profanity", "insults", "threats", "mockery"]


class Toxicity(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[ToxicityLiteral]] = [
            type.value for type in ToxicityType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=ToxicityType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Toxicity"
