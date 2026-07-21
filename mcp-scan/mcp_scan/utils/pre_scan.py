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

"""
Static pre-scan module for MCP projects.

Runs a fast regex-based pass over project files before the Agent starts,
detecting high-risk patterns and generating a security audit hint that is
injected into the Agent as supporting evidence for its judgment.

Adapted from skill-scan's pre_scan.py with MCP-specific patterns added.
"""

import os
import re
from typing import List, Tuple

from mcp_scan.utils.loging import logger

# High-risk pattern definitions: (pattern name, regex, description)
_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        'curl_pipe_exec',
        re.compile(r'curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|curl\s+-[^|]*\|\s*(python|ruby|perl)', re.IGNORECASE),
        'Install/usage instructions pipe curl|bash output into a shell to execute a remote script, a common malicious payload delivery method',
    ),
    (
        'cloud_metadata_access',
        re.compile(r'169\.254\.169\.254|metadata\.google\.internal|metadata\.azure\.com', re.IGNORECASE),
        'Code accesses a cloud instance metadata endpoint, a common way to obtain temporary cloud credentials',
    ),
    (
        'local_env_recon',
        re.compile(r'gethostname|getfqdn|getsockname|socket\.connect.*8\.8\.8\.8', re.IGNORECASE),
        'Code collects local environment information (hostname/IP/FQDN), consistent with environment reconnaissance',
    ),
    (
        'credential_file_access',
        re.compile(r'(~/|HOME|USERPROFILE).*(/|\\)(\.ssh|\.aws|\.env|credentials|mcp\.json|Keychain|authorized_keys)', re.IGNORECASE),
        'Code accesses credential/secret-related paths',
    ),
    (
        'prompt_injection',
        re.compile(r'(ignore\s+(previous|above|all)\s+(instructions?|rules?|prompts?)|you\s+are\s+now|SYSTEM\s*OVERRIDE|<\|im_start\|>|forget\s+(everything|your\s+instructions))', re.IGNORECASE),
        'Document/code contains suspected prompt-injection instructions attempting to override AI safety constraints',
    ),
    (
        'reverse_shell',
        re.compile(r'(socket\.connect|subprocess|/bin/(ba)?sh).*\d+\.\d+\.\d+\.\d+', re.IGNORECASE),
        'Code contains a suspected reverse-shell pattern',
    ),
    (
        'encoded_payload',
        re.compile(r'(base64\.b64decode|atob|Buffer\.from.*base64).*\b(exec|eval|system|popen)\b', re.IGNORECASE | re.DOTALL),
        'Code contains a pattern that decodes and then executes',
    ),
    (
        'data_exfil_encoded',
        re.compile(r'(base64\.(b64)?encode|btoa).*?(key|secret|token|password|credential|private|id_rsa)', re.IGNORECASE | re.DOTALL),
        'Code encodes sensitive data before outputting it, potentially a covert data exfiltration channel',
    ),
    (
        'outbound_data_exfil',
        re.compile(r'(requests\.(post|put)|urlopen|fetch|http\.request).*?(environ|os\.getenv|password|secret|token|api_key)', re.IGNORECASE | re.DOTALL),
        'Code contains a pattern that sends sensitive information over the network',
    ),
    (
        'crontab_persistence',
        re.compile(r'crontab|systemctl\s+enable|launchctl\s+load|schtasks', re.IGNORECASE),
        'Code contains a persistence mechanism (scheduled task/service registration)',
    ),
    (
        'ssh_key_write',
        re.compile(r'authorized_keys|id_rsa|\.ssh.*write|\.ssh.*open.*w', re.IGNORECASE),
        'Code writes to SSH key files',
    ),
    (
        'non_official_download',
        re.compile(r'(github\.com/[a-zA-Z0-9_-]+/|glot\.io|pastebin\.com|raw\.githubusercontent\.com/[a-zA-Z0-9_-]+/).*\.(exe|sh|py|bin|zip|tar)', re.IGNORECASE),
        'Downloads an executable file from a personal code-hosting/pastebin site',
    ),
    (
        'mcp_tool_poisoning',
        re.compile(r'tool.*?(name|description).*?(override|replace|hijack|inject|poison)', re.IGNORECASE | re.DOTALL),
        'Code contains patterns that may modify, wrap, or replace MCP tool definitions to inject malicious logic',
    ),
    (
        'mcp_token_steal',
        re.compile(r'(mcp\.json|cursor.*mcp|claude.*config).*?(token|key|secret|password)', re.IGNORECASE | re.DOTALL),
        'Code reads MCP configuration files that may contain sensitive tokens or credentials',
    ),
]

# Directories and files to skip
_SKIP_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'dist', 'build'}
_SKIP_EXTS = {'.pyc', '.pyo', '.pyd', '.exe', '.bin', '.dll', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}
_SKIP_FILES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
_MAX_FILE_SIZE = 512 * 1024  # 512KB


def pre_scan(repo_dir: str) -> str:
    """
    Run a static pre-scan of the project and return the security audit hint text.
    Returns an empty string if no high-risk patterns are found.
    """
    findings: List[dict] = []

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname in _SKIP_FILES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in _SKIP_EXTS:
                continue
            fpath = os.path.join(root, fname)
            try:
                if os.path.getsize(fpath) > _MAX_FILE_SIZE:
                    continue
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (PermissionError, OSError):
                continue

            rel_path = os.path.relpath(fpath, repo_dir)
            for pattern_name, regex, description in _PATTERNS:
                matches = regex.findall(content)
                if matches:
                    # Collect the lines where the match occurred
                    lines_hit = []
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            lines_hit.append((i, line.strip()[:120]))
                            if len(lines_hit) >= 3:
                                break
                    findings.append({
                        'file': rel_path,
                        'pattern': pattern_name,
                        'description': description,
                        'evidence': lines_hit,
                    })

    if not findings:
        return ''

    # Build the hint text
    lines = ['\u26a0\ufe0f The static pre-scan found the following patterns that warrant special attention; please focus the audit on whether these behaviors are necessary and what risks they pose:\n']
    for f in findings:
        lines.append(f'- **{f["file"]}** — {f["description"]}')
        for line_no, line_text in f['evidence']:
            lines.append(f'  - L{line_no}: `{line_text}`')
    lines.append('\nWhen auditing, please assess whether these behaviors exceed the minimum privileges necessary for the MCP server\'s declared functionality.')

    result = '\n'.join(lines)
    logger.info(f'Pre-scan found {len(findings)} high-risk pattern hit(s)')
    return result
