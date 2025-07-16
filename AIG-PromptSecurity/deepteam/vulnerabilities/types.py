from typing import Union

from deepteam.metrics.excessive_agency.template import ExcessiveAgencyTemplate
from deepteam.metrics.intellectual_property.template import (
    IntellectualPropertyTemplate,
)
from deepteam.vulnerabilities.bias.template import BiasTemplate
from deepteam.vulnerabilities.competition.template import CompetitionTemplate
from deepteam.vulnerabilities.graphic_content.template import (
    GraphicContentTemplate,
)
from deepteam.vulnerabilities.illegal_activity.template import (
    IllegalActivityTemplate,
)
from deepteam.vulnerabilities.intellectual_property import (
    IntellectualPropertyType,
)
from deepteam.vulnerabilities.misinformation.template import (
    MisinformationTemplate,
)
from deepteam.vulnerabilities.personal_safety.template import (
    PersonalSafetyTemplate,
)
from deepteam.vulnerabilities.pii_leakage.template import PIILeakageTemplate
from deepteam.vulnerabilities.prompt_leakage.template import (
    PromptLeakageTemplate,
)
from deepteam.vulnerabilities.robustness.template import RobustnessTemplate
from deepteam.vulnerabilities.toxicity.template import ToxicityTemplate
from deepteam.vulnerabilities.unauthorized_access import UnauthorizedAccessType
from deepteam.vulnerabilities.illegal_activity import IllegalActivityType
from deepteam.vulnerabilities.excessive_agency import ExcessiveAgencyType
from deepteam.vulnerabilities.personal_safety import PersonalSafetyType
from deepteam.vulnerabilities.graphic_content import GraphicContentType
from deepteam.vulnerabilities.misinformation import MisinformationType
from deepteam.vulnerabilities.prompt_leakage import PromptLeakageType
from deepteam.vulnerabilities.competition import CompetitionType
from deepteam.vulnerabilities.pii_leakage import PIILeakageType
from deepteam.vulnerabilities.robustness import RobustnessType
from deepteam.vulnerabilities.toxicity import ToxicityType
from deepteam.vulnerabilities.bias import BiasType
from deepteam.vulnerabilities.custom import CustomVulnerabilityType
from deepteam.vulnerabilities.unauthorized_access.template import (
    UnauthorizedAccessTemplate,
)

# 导入我们的自定义漏洞类型
from deepteam.vulnerabilities.custom_prompt import CustomPromptType
from deepteam.vulnerabilities.multi_dataset import MultiDatasetVulnerabilityType

VulnerabilityType = Union[
    UnauthorizedAccessType,
    IllegalActivityType,
    ExcessiveAgencyType,
    PersonalSafetyType,
    GraphicContentType,
    MisinformationType,
    PromptLeakageType,
    CompetitionType,
    PIILeakageType,
    RobustnessType,
    ToxicityType,
    BiasType,
    IntellectualPropertyType,
    CustomVulnerabilityType,
    # 添加我们的自定义类型
    CustomPromptType,
    MultiDatasetVulnerabilityType
]

TemplateType = Union[
    BiasTemplate,
    CompetitionTemplate,
    ExcessiveAgencyTemplate,
    GraphicContentTemplate,
    IllegalActivityTemplate,
    IntellectualPropertyTemplate,
    MisinformationTemplate,
    PersonalSafetyTemplate,
    PIILeakageTemplate,
    PromptLeakageTemplate,
    RobustnessTemplate,
    ToxicityTemplate,
    UnauthorizedAccessTemplate,
]
