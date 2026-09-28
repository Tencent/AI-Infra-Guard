"""Skills channel: hide the payload inside an Agent Skill (``SKILL.md``).

Agent Skills are Markdown files with a YAML frontmatter (``name`` /
``description``) plus a body of instructions. An agent reads the
``description`` to decide whether to load a skill, then follows the body.
An attacker who can publish or edit a skill hides instructions in the
``description`` (executed the moment the agent considers the skill) or in
the body (executed on load) — a topical indirect-injection vector as agents
increasingly auto-discover and load third-party skills.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("skills")
class SkillsChannel(Channel):
    """Embed the payload in a SKILL.md skill definition.

    Parameters
    ----------
    method:
        * ``"description"`` — append the payload to the frontmatter
          ``description`` (read during skill selection, before load).
        * ``"body"`` — append the payload to the skill body.
        * ``"instructions"`` — insert the payload disguised as a numbered
          step within the body's instructions.
    """

    def __init__(self, method: str = "description") -> None:
        if method not in ("description", "body", "instructions"):
            raise ValueError(
                "method must be 'description', 'body', or 'instructions'"
            )
        self.method = method

    def _inject_description(self, data: str, payload: str) -> str:
        lines = data.splitlines()
        out = []
        injected = False
        for line in lines:
            if not injected and line.lstrip().lower().startswith("description:"):
                out.append(f"{line.rstrip()} {payload}")
                injected = True
            else:
                out.append(line)
        if not injected:
            # No description field found; add one inside/at the frontmatter.
            out.append(f"description: {payload}")
        return "\n".join(out)

    def _inject_instructions(self, data: str, payload: str) -> str:
        step = f"\n1. {payload}\n"
        # Insert after the first body heading if present, else append.
        idx = data.find("\n#")
        if idx != -1:
            nl = data.find("\n", idx + 1)
            nl = nl if nl != -1 else len(data)
            return data[:nl] + step + data[nl:]
        return f"{data}{step}"

    def taint(self, data: str, payload: str) -> str:
        if self.method == "description":
            return self._inject_description(data, payload)
        if self.method == "instructions":
            return self._inject_instructions(data, payload)
        return f"{data}\n\n{payload}"
