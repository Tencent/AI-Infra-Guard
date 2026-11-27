"""Result models shared by recognizers, the scanner and the reporters."""
from dataclasses import dataclass
from typing import Optional

CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
LEVEL_MAP = {"high": "error", "medium": "warning", "low": "note"}


@dataclass
class Hit:
    """A raw recognizer hit before line/column/masking are computed."""

    type: str
    start: int          # code-point offset, inclusive
    end: int            # code-point offset, exclusive
    confidence: str     # low | medium | high
    value: str          # raw matched text


@dataclass
class Finding:
    type: str
    start: int
    end: int
    line: int           # 1-based
    column: int         # 1-based, code points
    confidence: str
    masked_sample: str
    source: str
    raw: Optional[str] = None  # populated only when masking is disabled

    def to_dict(self) -> dict:
        d = {
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "line": self.line,
            "column": self.column,
            "confidence": self.confidence,
            "masked_sample": self.masked_sample,
            "source": self.source,
        }
        if self.raw is not None:
            d["raw_sample"] = self.raw
        return d
