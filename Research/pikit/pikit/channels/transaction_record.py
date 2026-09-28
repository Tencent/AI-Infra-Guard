"""Transaction-record channel: hide the payload inside a bank transaction.

Models an indirect-injection vector where the payload is embedded in a
financial transaction description or merchant name. The transaction looks
normal in a banking UI but contains hidden instructions the model reads
when processing transaction history.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("transaction_record")
class TransactionRecordChannel(Channel):
    """Embed the payload in a financial transaction record.

    Parameters
    ----------
    method:
        * ``"description"`` — payload in the transaction description field.
        * ``"merchant"`` — payload disguised as the merchant name.
        * ``"memo"`` — payload in the memo/reference field.
    """

    def __init__(self, method: str = "description") -> None:
        if method not in ("description", "merchant", "memo"):
            raise ValueError(
                "method must be 'description', 'merchant', or 'memo'"
            )
        self.method = method

    def _hide(self, payload: str) -> str:
        if self.method == "description":
            return f"Payment - {payload}"
        if self.method == "merchant":
            return payload
        # memo
        return f"REF: {payload}"

    def taint(self, data: str, payload: str) -> str:
        hidden = self._hide(payload)
        # Append a new transaction entry containing the payload.
        lines = data.strip().splitlines()
        if lines and any("transaction" in l.lower() or "|" in l for l in lines[:3]):
            # Looks like a transaction list — append a new entry.
            return f"{data.rstrip()}\n6. 2025-07-08 | {hidden} | -$0.01 | Balance: unchanged"
        return f"{data}\n\n[Transaction]\n{hidden}"
