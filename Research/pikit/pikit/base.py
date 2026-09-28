"""Abstract base classes for attacks, defenses, and channels.

An :class:`Attack` and a :class:`Defense` are *prompt-text transformers*:
they take a prompt string and return a new prompt string. Keeping them on
the same shape is what lets callers freely compose any attack with any
defense.

A :class:`Channel` models *indirect* injection — it hides a payload inside
an external data artifact (web page, document, email) and returns the full
prompt the target would receive after reading it. Channels are orthogonal
to attacks: word a payload with an attack, then embed it with a channel.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class Attack(ABC):
    """An injection technique that embeds an attacker task into a prompt.

    Subclasses implement :meth:`inject`. The free-form signature takes the
    full prompt (instruction + untrusted data, already assembled by the
    caller) and the attacker-controlled ``injected_task`` to smuggle in.

    Note
    ----
    An :class:`Attack` controls how the payload is *worded* (direct
    injection). To model *indirect* injection — hiding the payload inside an
    external data artifact such as a web page or document — pair an attack
    with a :class:`Channel`. The two are orthogonal and compose freely.
    """

    #: Stable identifier used by the registry and in results/logs.
    name: str = "attack"

    @abstractmethod
    def inject(self, prompt: str, injected_task: str) -> str:
        """Return ``prompt`` with ``injected_task`` smuggled in.

        Parameters
        ----------
        prompt:
            The full prompt the target would otherwise receive, typically a
            benign instruction followed by untrusted external data.
        injected_task:
            The instruction the attacker wants the model to follow instead.
        """
        raise NotImplementedError

    def __call__(self, prompt: str, injected_task: str) -> str:
        return self.inject(prompt, injected_task)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(name={self.name!r})"


class Defense(ABC):
    """A prevention-style defense that hardens a prompt before querying.

    Subclasses implement :meth:`apply`. Defenses operate purely on the
    prompt text (no extra model calls), e.g. wrapping untrusted data in
    delimiters, re-stating the instruction after the data (sandwich), or
    spotlighting the data so the model can tell instructions from content.
    """

    #: Stable identifier used by the registry and in results/logs.
    name: str = "defense"

    @abstractmethod
    def apply(self, prompt: str, instruction: Optional[str] = None) -> str:
        """Return a hardened version of ``prompt``.

        Parameters
        ----------
        prompt:
            The (possibly tainted) prompt containing untrusted data.
        instruction:
            The original benign instruction, when the caller can separate it
            from the data. Defenses that need to re-assert the task
            (sandwich, instructional) use it; others may ignore it. When
            omitted, the whole prompt is treated as untrusted data.
        """
        raise NotImplementedError

    def __call__(self, prompt: str, instruction: Optional[str] = None) -> str:
        return self.apply(prompt, instruction)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(name={self.name!r})"


class Channel(ABC):
    """An *indirect* injection carrier.

    Where an :class:`Attack` controls how a payload is *worded*, a Channel
    controls *where and how* the payload is hidden — inside an external data
    artifact the model later reads (a web page, a retrieved document, an
    email). The two are orthogonal and compose freely: word a payload with an
    attack, then embed it with a channel.

    Subclasses implement :meth:`taint`, which returns the tainted data
    artifact itself (the web page / document / email). This is what an
    attacker actually controls and what an agent's compromised tool would
    return. The concrete :meth:`embed` is a convenience that prepends an
    instruction to the tainted artifact to form a full prompt.

    Two delivery modes are supported:

    * **text mode** (:meth:`taint`) — operates on a plain-text representation
      of the artifact. This is the simulation default and requires no real
      files.
    * **file mode** (:meth:`taint_file`) — operates on a *real file*
      (``.html``, ``.eml``, ``.pdf``, ``.ics``, …). The tainted output is a
      file whose format matches what a real agent would encounter. For binary
      formats (PDF, XLSX) subclasses may use helper libraries; the default
      implementation reads the file as text and delegates to :meth:`taint`.
    """

    #: Stable identifier used by the registry and in results/logs.
    name: str = "channel"

    @abstractmethod
    def taint(self, data: str, payload: str) -> str:
        """Hide ``payload`` inside ``data``, returning the tainted artifact.

        Parameters
        ----------
        data:
            The clean external data (page HTML, document body, email text).
        payload:
            The injected instruction to hide. May be the raw attacker task
            or the output of an :class:`Attack` (e.g. ``attack.inject("", task)``)
            to combine wording with carrier.

        Returns
        -------
        str
            The tainted artifact — the data with the payload hidden inside,
            **not** a full prompt. Feed this to an agent's compromised tool,
            or use :meth:`embed` to turn it into a prompt.
        """
        raise NotImplementedError

    def taint_file(self, path: str, payload: str, output_path: Optional[str] = None) -> str:
        """Hide ``payload`` inside a *real file*, returning the output path.

        Reads the carrier file at *path*, injects the payload, and writes
        the tainted file. For text-based formats (HTML, Markdown, YAML,
        CSV, Python, etc.) the default implementation reads the file as
        text, calls :meth:`taint`, and writes the result. Subclasses that
        target binary formats (PDF, XLSX) override this to use format-
        specific libraries.

        Parameters
        ----------
        path:
            Path to the clean carrier file.
        payload:
            The injected instruction to hide.
        output_path:
            Where to write the tainted file. When ``None``, writes to
            ``<path>.tainted.<ext>``.

        Returns
        -------
        str
            The path to the tainted file.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        tainted = self.taint(data, payload)
        if output_path is None:
            base, ext = os.path.splitext(path)
            output_path = f"{base}.tainted{ext}"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tainted)
        return output_path

    def extract(self, tainted_data: str) -> str:
        """Extract the visible text a model would see from a tainted artifact.

        In text mode this is typically the identity (the artifact *is* text).
        Subclasses for structured formats may parse the artifact to produce
        the model-visible text. Useful for defenders and for verifying that
        a payload is present.
        """
        return tainted_data

    def extract_file(self, path: str) -> str:
        """Read a tainted file and return the text a model would see.

        Default implementation reads the file as text and calls
        :meth:`extract`. Binary-format subclasses override to parse.
        """
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return self.extract(f.read())

    def embed(self, instruction: str, data: str, payload: str) -> str:
        """Taint ``data`` and prepend ``instruction`` to form a full prompt.

        Convenience for the non-agent case: returns ``instruction`` followed
        by the tainted artifact — the full prompt a target would receive.
        """
        return f"{instruction}\n{self.taint(data, payload)}"

    def __call__(self, instruction: str, data: str, payload: str) -> str:
        return self.embed(instruction, data, payload)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(name={self.name!r})"
