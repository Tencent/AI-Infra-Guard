from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.prompt_leakage import PromptLeakageType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

PromptLeakageLiteral = Literal[
    "secrets and credentials",
    "instructions",
    "guard exposure",
    "permissions and roles",
]


class PromptLeakage(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[PromptLeakageLiteral]] = [
            type.value for type in PromptLeakageType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=PromptLeakageType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Prompt Leakage"
