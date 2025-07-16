from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.graphic_content import GraphicContentType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

GraphicContentLiteral = Literal[
    "sexual content", "graphic content", "pornographic content"
]


class GraphicContent(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[GraphicContentLiteral]] = [
            type.value for type in GraphicContentType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=GraphicContentType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Graphic Content"
