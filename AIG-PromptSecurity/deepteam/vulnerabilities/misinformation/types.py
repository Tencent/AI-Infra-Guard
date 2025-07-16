from enum import Enum
from typing import Literal


class MisinformationType(Enum):
    FACTUAL_ERRORS = "factual errors"
    UNSUPPORTED_CLAIMS = "unsupported claims"
    EXPERTIZE_MISREPRESENTATION = "expertize misrepresentation"


MisinformationTypes = Literal[
    MisinformationType.FACTUAL_ERRORS.value,
    MisinformationType.UNSUPPORTED_CLAIMS.value,
    MisinformationType.EXPERTIZE_MISREPRESENTATION.value,
]
