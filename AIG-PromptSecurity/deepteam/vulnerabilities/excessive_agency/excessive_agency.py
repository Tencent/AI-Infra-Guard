from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.excessive_agency import ExcessiveAgencyType
from deepteam.vulnerabilities.utils import validate_vulnerability_types


ExcessiveAgencyLiteral = Literal["functionality", "permissions", "autonomy"]


class ExcessiveAgency(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[ExcessiveAgencyLiteral]] = [
            type.value for type in ExcessiveAgencyType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=ExcessiveAgencyType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Excessive Agency"
