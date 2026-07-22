# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""Standalone connectivity test script for the AIG Web backend.

This script is invoked by the Go backend (HandleAgentConnect / HandleAgentPromptTest)
via `uv run test_client_connect.py --client_file <yaml> [--prompt <text>]`.

It loads an agent provider config, sends a test prompt, and prints a JSON
result to stdout matching the ConnectResultUpdate schema expected by the Go side.
"""

import argparse
import traceback

from agent_scan.utils.aig_logger import scanLogger
from agent_scan.core.agent_adapter.adapter import AIProviderClient, ProviderTestResult


def is_client_connect(file_path: str, prompt: str) -> ProviderTestResult:
    # Enable structured JSON output so the Go backend can parse the result.
    scanLogger.enable()
    client = AIProviderClient()
    agent_provider = client.load_config_from_file(file_path)[0]
    try:
        response = client.call_provider(agent_provider, prompt)
    except Exception as e:
        tb = traceback.format_exc()
        response = ProviderTestResult(
            success=False,
            message=f"Error during execution: {e}\n{tb}",
        )
    scanLogger.result_update(content=response.model_dump())
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent CLI Runner")
    parser.add_argument("--client_file", type=str, help="Client config file")
    parser.add_argument("--prompt", type=str, default="Only return 1", help="Prompt to send to the agent")
    args = parser.parse_args()

    is_client_connect(args.client_file, args.prompt)
