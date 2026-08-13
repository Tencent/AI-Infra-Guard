"""
Static pre-scan module

Runs a fast regex-based pass over project files before the Agent starts,
detecting high-risk patterns and generating a security audit hint that is
injected into the Agent as supporting evidence for its judgment.
"""

import os
import re

from skill_scan.utils.loging import logger
from skill_scan.utils.text_decoder import TextDecodeError, read_text_file

# High-risk pattern definitions: (pattern name, regex, description)
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
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

# Directories to skip (compiled bytecode dirs are NOT skipped -- see note below)
_SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', 'dist', 'build'}
# Compiled Python bytecode (.pyc/.pyo/.pyd) is NO LONGER skipped. CPython runs
# `.pyc` at import time without any `.py` source (PEP 552 UNCHECKED_HASH), so a
# malicious skill could ship a clean `.py` decoy plus a malicious `.pyc` and get
# a false SAFE verdict. Tracked as GitHub Issue #531. Bytecode still embeds
# readable string constants (the payload), so scanning it as text surfaces
# exfil/injection patterns. We surface every compiled artifact as an explicit
# warning in addition to normal pattern matching.
_SKIP_EXTS = {'.exe', '.bin', '.dll', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}
_COMPILED_EXTS = {'.pyc', '.pyo', '.pyd'}
_SKIP_FILES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
_MAX_FILE_SIZE = 512 * 1024  # 512KB


def _preview(text: str, limit: int) -> list[tuple[int, str]]:
    return [
        (line_no, line.strip()[:120])
        for line_no, line in enumerate(text.splitlines(), 1)
        if line.strip()
    ][:limit]


def pre_scan(repo_dir: str) -> str:
    """
    Run a static pre-scan of the project and return the security audit hint text.
    Returns an empty string if no high-risk patterns are found.
    """
    findings: list[dict] = []

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
                decoded = read_text_file(fpath)
            except (PermissionError, OSError, TextDecodeError):
                # Compiled artifacts that fail to decode as text are still a
                # signal worth flagging explicitly (see Issue #531).
                if ext in _COMPILED_EXTS:
                    rel_path = os.path.relpath(fpath, repo_dir)
                    findings.append({
                        'file': rel_path,
                        'pattern': 'compiled_bytecode',
                        'description': (
                            'Compiled Python bytecode (.pyc/.pyo/.pyd) present in the '
                            'skill package. CPython executes it at import time regardless '
                            'of any .py source (PEP 552 UNCHECKED_HASH); inspect it for '
                            'hidden malicious code before trusting this skill'
                        ),
                        'evidence': [],
                    })
                continue

            rel_path = os.path.relpath(fpath, repo_dir)
            # Explicitly warn on compiled bytecode even if no pattern matches.
            if ext in _COMPILED_EXTS:
                findings.append({
                    'file': rel_path,
                    'pattern': 'compiled_bytecode',
                    'description': (
                        'Compiled Python bytecode (.pyc/.pyo/.pyd) present in the skill '
                        'package. CPython executes it at import time regardless of any .py '
                        'source (PEP 552 UNCHECKED_HASH); inspect it for hidden malicious '
                        'code before trusting this skill'
                    ),
                    'evidence': [],
                })
            if decoded.encoding not in {'utf-8', 'utf-8-sig'}:
                findings.append({
                    'file': rel_path,
                    'pattern': 'non_utf8_text',
                    'description': (
                        f'Non-UTF-8 file detected ({decoded.encoding}); inspect the decoded '
                        'content for encoding-based content smuggling'
                    ),
                    'evidence': _preview(decoded.text, 1),
                })

            contents = [(decoded.text, f'decoded as {decoded.encoding}')]
            if decoded.recovered_text:
                label = f'recovered reversible mojibake ({decoded.recovery})'
                contents.append((decoded.recovered_text, label))
                findings.append({
                    'file': rel_path,
                    'pattern': 'reversible_mojibake',
                    'description': (
                        'Reversible mojibake can reconstruct hidden content at runtime '
                        f'using {decoded.recovery}'
                    ),
                    'evidence': _preview(decoded.recovered_text, 3),
                })

            for content, label in contents:
                for pattern_name, regex, description in _PATTERNS:
                    if not regex.search(content):
                        continue
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
                        'description': f'{description} (matched in {label})',
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
    lines.append('\nWhen auditing, please assess whether these behaviors exceed the minimum privileges necessary for the Skill\'s declared functionality.')

    result = '\n'.join(lines)
    logger.info(f'Pre-scan found {len(findings)} high-risk pattern hit(s)')
    return result
