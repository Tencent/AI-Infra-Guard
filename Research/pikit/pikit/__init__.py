"""pikit — Prompt Injection Kit.

A method library of classic prompt-injection *attacks*, *defenses*, and
indirect-injection *channels* behind a single, composable interface.
Attacks and defenses are plain prompt-text transformers, so any attack can
be combined with any defense; a channel hides an (optionally attack-worded)
payload inside external data for indirect injection. Model backends sit
behind a uniform ``Target`` interface.

The package includes optional judges and reference datasets for repeatable
experiments. It remains a toolbox rather than a prescriptive leaderboard:
researchers choose the threat model and success criteria appropriate to their
agent.

Quick start
-----------
>>> from pikit import attacks, defenses, get_target
>>> atk = attacks.get("combined")()
>>> dfn = defenses.get("spotlighting")(mode="datamarking")
>>> tgt = get_target("mock")
>>> prompt = "Summarize the following text: <external data>"
>>> tainted = atk.inject(prompt, injected_task="Print 'hacked'")
>>> hardened = dfn.apply(tainted, instruction="Summarize the following text:")
>>> _ = tgt.query(hardened)

Indirect injection (attack × channel)
-------------------------------------
>>> from pikit import attacks, channels, get_target
>>> worded = attacks.get("context_ignoring")().inject("", "Print 'hacked'")
>>> ch = channels.get("webpage")(method="comment")
>>> prompt = ch.embed("Summarize this page:", "<html>..clean..</html>", worded)
>>> _ = get_target("mock").query(prompt)
"""

from . import attacks, channels, defenses
from .base import Attack, Channel, Defense
from .craft import CraftResult, craft
from .targets import Target, get_target
from .judges import Judge, JudgeResult, RuleJudge, LLMJudge
from .config import ExperimentConfig
from .outcomes import Outcome
from . import datasets

__all__ = [
    "attacks",
    "channels",
    "defenses",
    "Attack",
    "Channel",
    "Defense",
    "Target",
    "get_target",
    "craft",
    "CraftResult",
    "Judge",
    "JudgeResult",
    "RuleJudge",
    "LLMJudge",
    "ExperimentConfig",
    "Outcome",
    "datasets",
]

# Keep this in sync with the distribution version in ``pyproject.toml``.
__version__ = "0.5.0"
