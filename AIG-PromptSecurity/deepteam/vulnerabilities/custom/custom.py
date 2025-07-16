from typing import List, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.custom.custom_types import CustomVulnerabilityType
from deepteam.metrics import BaseRedTeamingMetric


class CustomVulnerability(BaseVulnerability):
    """
    Custom vulnerability class that allows users to define their own vulnerability types.
    """

    def __init__(
        self,
        name: str,
        types: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None,
        metric: Optional[BaseRedTeamingMetric] = None,
    ):
        self.name = name
        self.types = types
        self.raw_types = types or []
        self.custom_prompt = custom_prompt
        self.metric = metric
        super().__init__(self.types)

    def get_name(self) -> str:
        return self.name

    def get_custom_prompt(self) -> Optional[str]:
        return self.custom_prompt

    def get_metric(self) -> Optional[BaseRedTeamingMetric]:
        return self.metric

    def get_raw_types(self) -> List[str]:
        return self.raw_types
