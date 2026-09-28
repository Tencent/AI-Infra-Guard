"""Local HuggingFace ``transformers`` backend.

Loads a model locally and generates text. ``torch`` and ``transformers``
are imported lazily so the core install needs nothing.

Install with::

    pip install pikit[hf]
"""

from __future__ import annotations

from typing import Optional

from .base import Target


class HuggingFaceTarget(Target):
    """Local text-generation backend via ``transformers``.

    Uses the chat template when the tokenizer provides one, otherwise falls
    back to feeding the raw prompt.

    Parameters
    ----------
    model:
        HuggingFace model id (e.g. ``"meta-llama/Llama-3.1-8B-Instruct"``).
    device:
        ``"cpu"``, ``"cuda"``, ``"auto"`` (default), …
    max_new_tokens:
        Default generation length.
    """

    def __init__(
        self,
        model: str,
        device: str = "auto",
        max_new_tokens: int = 256,
        **model_kwargs,
    ) -> None:
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ImportError(
                "'torch' and 'transformers' are required for hf targets; "
                "install with: pip install pikit[hf]"
            ) from exc

        self.model_id = model
        self.name = f"hf:{model}"
        self.max_new_tokens = max_new_tokens
        self._tokenizer = AutoTokenizer.from_pretrained(model)
        self._model = AutoModelForCausalLM.from_pretrained(
            model, device_map=device, **model_kwargs
        )

    def _build_inputs(self, prompt: str, system: Optional[str]):
        tok = self._tokenizer
        if tok.chat_template:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            text = f"{system}\n{prompt}" if system else prompt
        return tok(text, return_tensors="pt").to(self._model.device)

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        import torch

        inputs = self._build_inputs(prompt, system)
        kwargs.setdefault("max_new_tokens", self.max_new_tokens)
        with torch.no_grad():
            out = self._model.generate(**inputs, **kwargs)
        # Decode only the newly generated tokens.
        gen = out[0][inputs["input_ids"].shape[-1]:]
        return self._tokenizer.decode(gen, skip_special_tokens=True)
