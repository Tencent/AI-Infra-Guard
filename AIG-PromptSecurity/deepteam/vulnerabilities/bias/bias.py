from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.bias import BiasType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

BiasLiteralType = Literal["religion", "politics", "gender", "race"]


class Bias(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[BiasLiteralType]] = [
            type.value for type in BiasType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=BiasType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Bias"
