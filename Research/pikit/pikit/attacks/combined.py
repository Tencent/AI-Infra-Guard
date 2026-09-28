"""Combined attack: stack fake-completion + escape + context-ignoring.

This is the strongest baseline in Open Prompt Injection. It first forges a
completion of the original task, then uses escape characters to break the
context, then explicitly tells the model to ignore prior instructions
before issuing the injected task.
"""

from __future__ import annotations

from ..base import Attack
from . import register
from .context_ignoring import ContextIgnoringAttack
from .escape import EscapeCharacterAttack
from .fake_completion import FakeCompletionAttack


@register("combined")
class CombinedAttack(Attack):
    """Compose fake-completion, escape, and context-ignoring in sequence.

    The sub-attacks are applied as nested transforms so the layering is
    explicit and each stage stays independently configurable.
    """

    def __init__(
        self,
        fake_response: str = FakeCompletionAttack.DEFAULT_RESPONSE,
        escape: str = "\n\n\n",
        ignore_text: str = ContextIgnoringAttack.DEFAULT_IGNORE,
    ) -> None:
        self._fake = FakeCompletionAttack(
            fake_response=fake_response, follow_up=""
        )
        self._escape = EscapeCharacterAttack(escape=escape)
        self._ignore = ContextIgnoringAttack(
            ignore_text=ignore_text, separator=""
        )

    def inject(self, prompt: str, injected_task: str) -> str:
        # 1) forge a completion of the original task (no follow-up text yet)
        staged = self._fake.inject(prompt, "")
        # 2) break context with escape characters, then
        # 3) tell the model to ignore prior instructions before the payload.
        staged = self._escape.inject(staged, "")
        return self._ignore.inject(staged, injected_task)
