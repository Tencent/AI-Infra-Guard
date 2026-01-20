import os
from datetime import datetime
from typing import Optional
from utils.config import base_dir


class PromptManager:
    _instance = None
    _templates = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
        return cls._instance

    def load_template(self, name: str) -> str:
        if name not in self._templates:
            # Try different possible paths or standard locations
            possible_paths = [
                os.path.join(base_dir, "prompt", "system", f"{name}.md"),
                os.path.join(base_dir, "prompt", "system", "agents", f"{name}.md"),
            ]

            content = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    break

            if content is None:
                raise FileNotFoundError(f"Prompt template '{name}' not found.")

            self._templates[name] = content

        return self._templates[name]

    def format_prompt(self, template_name: str, **kwargs) -> str:
        template = self.load_template(template_name)

        # Standard variables
        if "${NOWTIME}" in template:
            kwargs.setdefault("NOWTIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Handle some nested formatting if needed, but keep it simple
        formatted = template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))

            # Support some alternate placeholder formats if they exist
            alt_placeholder = "${" + key + "}"
            if alt_placeholder in formatted:
                formatted = formatted.replace(alt_placeholder, str(value))

        return formatted


prompt_manager = PromptManager()
