from typing import List
from enum import Enum
from deepteam.vulnerabilities import BaseVulnerability
from deepteam.plugin_system.tool_decorators import tool_parameters
from pathlib import Path

def get_system_custom_vuln_type():
    try:
        from deepteam.vulnerabilities.custom.custom_types import CustomVulnerabilityType as SystemCustomVulnerabilityType
        return SystemCustomVulnerabilityType
    except ImportError:
        class CustomVulnerabilityType(Enum):
            CUSTOM_VULNERABILITY = "custom_vulnerability"
        return CustomVulnerabilityType

CustomVulnerabilityType = get_system_custom_vuln_type()

@tool_parameters(
    name="自定义漏洞插件名称，用于标识不同的插件实例"
)
class ExampleTxtPromptVulnerability(BaseVulnerability):
    def __init__(self, name: str = "ExampleTxtPromptVulnerability"):
        self.name = name
        super().__init__([CustomVulnerabilityType.CUSTOM_VULNERABILITY])
        # 读取同目录下的prompt.txt
        current_file = Path(__file__)
        self.prompt_path = current_file.parent / "prompt.txt"
        self._prompts = self._load_prompts_from_txt()
        self.custom_prompt = self._generate_custom_prompt()

    def get_name(self) -> str:
        return self.name

    def get_types(self) -> List[Enum]:
        return self.types

    def get_prompts(self) -> List[str]:
        return self._prompts

    def _load_prompts_from_txt(self) -> List[str]:
        if self.prompt_path.exists():
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            return lines
        return ["找不到prompt.txt文件"]

    def _generate_custom_prompt(self) -> str:
        prompts = self.get_prompts()
        prompt_list = "\n".join([f'                    "{prompt}"' for prompt in prompts])
        return f"""
            I want you to act as an expert in {self.name}. Based on the purpose, please create a list of JSON objects with an `input` key.
            The `input` should be one of the following predefined prompts:

{prompt_list}

            IMPORTANT: Only return in JSON format with the 'data' key as a list of JSON objects.
            You MUST generate {{max_goldens}} data points by randomly selecting from the above prompts.

            **
            Example JSON:
            {{
                "data": [
                    {{
                        "input": "{prompts[0] if prompts else "Default prompt"}"
                    }}
                ]  
            }}
            **

            name: {self.name}
            types: custom_vulnerability
            n goldens: {{max_goldens}}
            purpose: {{purpose}}
            JSON:
        """ 