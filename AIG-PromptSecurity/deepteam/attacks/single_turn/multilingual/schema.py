from pydantic import BaseModel


class EnhancedAttack(BaseModel):
    input: str


class ComplianceData(BaseModel):
    """Schema for compliance data.
    Attributes:
        non_compliant (bool): True if the prompt is non-compliant, False otherwise.
    """

    non_compliant: bool


class IsTranslation(BaseModel):
    """Schema for checking if the prompt is a translation.
    Attributes:
        is_translation (bool): True if the prompt is a translation, False otherwise.
    """

    is_translation: bool
