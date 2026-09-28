"""``craft()`` — the single entry point for building attack content.

It unifies the two delivery paths so the rest of the toolkit (and the user)
deals with one object:

* **direct** — the worded payload is the *user message* sent to the agent.
* **indirect** — the worded payload is hidden in a data artifact (via a
  channel); that tainted artifact is what a compromised tool returns.

In both cases :attr:`CraftResult.delivery` is the single field the agent
consumes — as the user message (direct) or as a ``taint`` map value
(indirect).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import attacks, channels


@dataclass
class CraftResult:
    """The product of :func:`craft`.

    Attributes
    ----------
    mode:
        ``"direct"`` or ``"indirect"``.
    payload:
        The worded attacker instruction (the attack's output).
    delivery:
        What actually gets injected — the user message (direct) or the
        tainted artifact (indirect).
    instruction, attack, channel:
        Reference metadata about how it was built.
    """

    mode: str
    payload: str
    delivery: str
    instruction: Optional[str] = None
    attack: Optional[str] = None
    channel: Optional[str] = None
    output_path: Optional[str] = None

    def __str__(self) -> str:
        return self.delivery


def craft(
    task: str,
    *,
    attack: str = "naive",
    attack_kwargs: Optional[dict] = None,
    channel: Optional[str] = None,
    channel_kwargs: Optional[dict] = None,
    data: Optional[str] = None,
    instruction: Optional[str] = None,
    mode: str = "text",
    carrier_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> CraftResult:
    """Build attack content for direct or indirect injection.

    Parameters
    ----------
    task:
        The instruction the attacker wants the model to follow.
    attack:
        Registry key of the wording technique (see ``pikit.attacks``).
    attack_kwargs:
        Constructor kwargs for the attack.
    channel:
        Registry key of the carrier (see ``pikit.channels``). When ``None``
        the result is *direct*; when set the result is *indirect*.
    channel_kwargs:
        Constructor kwargs for the channel.
    data:
        The clean artifact (page HTML, document, email body) to taint.
        Required for indirect injection in **text mode**. Ignored in
        **file mode** (use *carrier_path* instead).
    instruction:
        The benign user request. For **direct** injection, when provided it
        is prepended so ``delivery`` is the realistic *benign + payload*
        message the agent receives (e.g. "Search the weather. Ignore all
        previous instructions. Instead, ..."); omit it to get the payload
        alone. For **indirect** injection it is kept for reference (the
        carrier hides only the payload, as in a real artifact).
    mode:
        ``"text"`` (default) — operate on a plain-text representation of the
        artifact (simulation). ``"file"`` — operate on a *real file* whose
        format matches what a real agent encounters (``.html``, ``.eml``,
        ``.pdf``, ``.ics``, …).
    carrier_path:
        Path to the clean carrier file. Required in **file mode**. When
        ``None`` in file mode, the default carrier from ``pikit.carriers``
        is used.
    output_path:
        Where to write the tainted file in **file mode**. When ``None``,
        the channel chooses a default (typically ``<carrier>.tainted.<ext>``).

    Returns
    -------
    CraftResult

    Examples
    --------
    >>> craft("Print HACKED", attack="context_ignoring").mode
    'direct'
    >>> r = craft("Print HACKED", attack="naive",
    ...           instruction="Summarize this article.")
    >>> r.delivery.startswith("Summarize this article.")
    True
    >>> craft("Print HACKED", channel="webpage",
    ...       data="<html><body>hi</body></html>").mode
    'indirect'
    """
    if mode not in {"text", "file"}:
        raise ValueError("mode must be 'text' or 'file'")

    if channel is None:
        if mode != "text":
            raise ValueError("file mode requires an indirect injection channel")
        # Direct: prepend the benign request when given, so `delivery` is the
        # realistic message the agent receives.
        base = instruction or ""
        attack_method = attacks.get(attack)(**(attack_kwargs or {}))
        worded = attack_method.inject(base, task)
        return CraftResult(
            mode="direct",
            payload=attack_method.inject("", task),
            delivery=worded,
            instruction=instruction,
            attack=attack,
        )

    ch = channels.get(channel)(**(channel_kwargs or {}))
    worded = attacks.get(attack)(**(attack_kwargs or {})).inject("", task)

    if mode == "file":
        # File mode: operate on a real carrier file.
        from .carriers import carrier_path as _default_carrier

        cpath = carrier_path if carrier_path is not None else _default_carrier(channel)
        out = ch.taint_file(cpath, worded, output_path=output_path)
        # Let the channel parse binary carriers before presenting their
        # model-visible text.  Reading a PDF/XLSX as UTF-8 would otherwise
        # discard precisely the metadata/cell content this mode is meant to
        # exercise.
        artifact = ch.extract_file(out)
        return CraftResult(
            mode="indirect",
            payload=worded,
            delivery=artifact,
            instruction=instruction,
            attack=attack,
            channel=channel,
            output_path=out,
        )

    # Text mode (default).
    if data is None:
        raise ValueError("indirect injection (channel set) requires `data`")

    # Indirect: the carrier hides only the payload (as in a real artifact).
    artifact = ch.taint(data, worded)
    return CraftResult(
        mode="indirect",
        payload=worded,
        delivery=artifact,
        instruction=instruction,
        attack=attack,
        channel=channel,
    )
