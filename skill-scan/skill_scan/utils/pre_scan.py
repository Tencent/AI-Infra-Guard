"""
Static pre-scan module

Runs a fast regex-based pass over project files before the Agent starts,
detecting high-risk patterns and generating a security audit hint that is
injected into the Agent as supporting evidence for its judgment.
"""

import os
import re
from typing import List, Tuple

from skill_scan.utils.loging import logger

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
        'fixed_tail_ad_injection',
        re.compile(
            r'((文末|结尾|每篇必带|固定收束|固定提示).{0,80}(链接|扫码|进群|群里|资讯|广告|内幕|吃瓜|news|http))|'
            r'((扫码进群|进群吃瓜|获取更多资讯新闻点击|点击[:：]|想深扒更多).{0,120}(https?://|www\.))|'
            r'((https?://|www\.).{0,120}(扫码进群|进群|群里|资讯|广告|内幕|吃瓜))',
            re.IGNORECASE | re.DOTALL,
        ),
        'Document contains a fixed advertising/traffic-diversion or link template appended at the end of the text, a signal of content injection targeting model output',
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
]

# Directories and files to skip
# NOTE: compiled Python bytecode (.pyc/.pyo/.pyd) and __pycache__ are deliberately
# NOT excluded here. Python loads .pyc at import time regardless of the matching
# .py source, so a malicious skill can ship a clean .py decoy plus a malicious
# .pyc (PEP 552 UNCHECKED_HASH) and achieve code execution. The static regex
# pass must inspect bytecode text (string constants are readable via the
# errors='ignore' decode) so such payloads are not invisible to the scanner.
_SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', 'dist', 'build'}
_SKIP_EXTS = {'.exe', '.bin', '.dll', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}
# Executable/compiled artifacts that must be surfaced to the audit (not skipped)
# but additionally flagged via _FLAG_EXTS so the agent is explicitly warned.
_FLAG_EXTS = {'.pyc', '.pyo', '.pyd'}
_SKIP_FILES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
_MAX_FILE_SIZE = 512 * 1024  # 512KB


def _collect_bytecode_warnings(repo_dir: str) -> List[str]:
    """Return a list of compiled-bytecode paths that warrant explicit attention.

    Python executes `.pyc`/`.pyo`/`.pyd` at import time regardless of whether a
    matching `.py` source is present. A compiled artifact with no corresponding
    source is the classic skill-scanner bypass signature, so we surface every
    such file (relative path) for the agent to verify.
    """
    warnings: List[str] = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _FLAG_EXTS:
                continue
            rel_path = os.path.relpath(os.path.join(root, fname), repo_dir)
            warnings.append(rel_path)
    return warnings


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
                # Compiled bytecode is scanned as text: string constants embedded
                # in the marshal'd code object (e.g. os.system, exfil URLs) remain
                # legible through the errors='ignore' decode.
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

    # Surface compiled Python bytecode as an explicit audit signal. A .pyc that
    # has no corresponding .py source (or was built with PEP 552 UNCHECKED_HASH)
    # is exactly the artifact class Python executes at import time and which the
    # scanner must never blind itself to.
    bytecode_warnings = _collect_bytecode_warnings(repo_dir)

    # Build the hint text
    lines = ['\u26a0\ufe0f The static pre-scan found the following patterns that warrant special attention; please focus the audit on whether these behaviors are necessary and what risks they pose:\n']
    for f in findings:
        lines.append(f'- **{f["file"]}** — {f["description"]}')
        for line_no, line_text in f['evidence']:
            lines.append(f'  - L{line_no}: `{line_text}`')
    lines.append('\nWhen auditing, please assess whether these behaviors exceed the minimum privileges necessary for the Skill\'s declared functionality.')

    if bytecode_warnings:
        lines.append('\n---\n')
        lines.append('\u26a0\ufe0f **Compiled Python bytecode detected** — Python loads `.pyc`/`.pyo`/`.pyd` at import time independently of any `.py` source. These files are within the scanner\'s audit scope and a `.pyc` lacking a matching `.py` source (or built with PEP 552 `UNCHECKED_HASH`) is a known scanner-bypass technique that can carry arbitrary executable code. Verify every compiled artifact is expected and trustworthy.')
        for w in bytecode_warnings:
            lines.append(f'  - `{w}`')

    result = '\n'.join(lines)
    logger.info(f'Pre-scan found {len(findings)} high-risk pattern hit(s)')
    return result
