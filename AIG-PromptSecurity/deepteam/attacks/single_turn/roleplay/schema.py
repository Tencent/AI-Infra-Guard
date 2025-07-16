from pydantic import BaseModel


class EnhancedAttack(BaseModel):
    input: str


class ComplianceData(BaseModel):
    non_compliant: bool


class IsRoleplay(BaseModel):
    is_roleplay: bool
