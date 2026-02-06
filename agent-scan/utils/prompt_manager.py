import os
from datetime import datetime
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
            path = os.path.join(base_dir, "prompt", "system", f"{name}.md")

            if not os.path.exists(path):
                raise FileNotFoundError(f"Prompt template '{name}' not found.")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self._templates[name] = content

        return self._templates[name]

    def format_prompt(self, template_name: str, **kwargs) -> str:
        template = self.load_template(template_name)
        if "${NOWTIME}" in template:
            kwargs.setdefault("NOWTIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        formatted = template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))
            alt_placeholder = "${" + key + "}"
            if alt_placeholder in formatted:
                formatted = formatted.replace(alt_placeholder, str(value))

        return formatted


prompt_manager = PromptManager()
