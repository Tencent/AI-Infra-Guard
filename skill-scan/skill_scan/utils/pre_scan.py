"""
Static pre-scan module

Runs a fast regex-based pass over project files before the Agent starts,
detecting high-risk patterns and generating a security audit hint that is
injected into the Agent as navigation hints, never as confirmed vulnerabilities.
"""

import os
import re

from skill_scan.utils.loging import logger
from skill_scan.utils.text_decoder import TextDecodeError, read_text_file

# Candidate patterns: regex matches do not establish execution or data flow.
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    (
        'curl_pipe_exec',
        re.compile(r'curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|curl\s+-[^|]*\|\s*(python|ruby|perl)', re.IGNORECASE),
        'Instructions may pipe curl|bash output into a shell; inspect source, arguments and task context before assessing remote execution risk',
    ),
    (
        'cloud_metadata_access',
        re.compile(r'169\.254\.169\.254|metadata\.google\.internal|metadata\.azure\.com', re.IGNORECASE),
        'Cloud metadata endpoint reference; verify actual access, requested fields and whether credentials cross a trust boundary',
    ),
    (
        'local_env_recon',
        re.compile(r'gethostname|getfqdn|getsockname|socket\.connect.*8\.8\.8\.8', re.IGNORECASE),
        'Host information API reference; distinguish routine diagnostics or backup metadata from out-of-scope reconnaissance',
    ),
    (
        'credential_file_access',
        re.compile(r'(~/|HOME|USERPROFILE).*(/|\\)(\.ssh|\.aws|\.env|credentials|mcp\.json|Keychain|authorized_keys)', re.IGNORECASE),
        'Credential-related path reference; verify read/write behavior, ownership, purpose and destination',
    ),
    (
        'prompt_injection',
        re.compile(r'(ignore\s+(previous|above|all)\s+(instructions?|rules?|prompts?)|you\s+are\s+now|SYSTEM\s*OVERRIDE|<\|im_start\|>|forget\s+(everything|your\s+instructions))', re.IGNORECASE),
        'Instruction-like text; inspect whether it is task guidance, quoted data or an active attempt to override user/system constraints',
    ),
    (
        'fixed_tail_ad_injection',
        re.compile(
            r'((文末|结尾|每篇必带|固定收束|固定提示).{0,80}(链接|扫码|进群|群里|资讯|广告|内幕|吃瓜|news|http))|'
            r'((扫码进群|进群吃瓜|获取更多资讯新闻点击|点击[:：]|想深扒更多).{0,120}(https?://|www\.))|'
            r'((https?://|www\.).{0,120}(扫码进群|进群|群里|资讯|广告|内幕|吃瓜))',
            re.IGNORECASE | re.DOTALL,
        ),
        'Output template or promotional link reference; distinguish requested marketing/attribution from unrelated forced output hijacking',
    ),
    (
        'reverse_shell',
        re.compile(r'(socket\.connect|subprocess|/bin/(ba)?sh).*\d+\.\d+\.\d+\.\d+', re.IGNORECASE),
        'Process/socket and IP references co-occur; verify a shell is actually connected to an attacker-controlled endpoint',
    ),
    (
        'encoded_payload',
        re.compile(r'(base64\.b64decode|atob|Buffer\.from.*base64).*\b(exec|eval|system|popen)\b', re.IGNORECASE | re.DOTALL),
        'Decoding and execution terms co-occur; trace whether decoded content actually reaches an execution sink',
    ),
    (
        'data_exfil_encoded',
        re.compile(r'(base64\.(b64)?encode|btoa).*?(key|secret|token|password|credential|private|id_rsa)', re.IGNORECASE | re.DOTALL),
        'Encoding and credential terms co-occur; verify actual data flow and distinguish normal authentication from disclosure',
    ),
    (
        'outbound_data_exfil',
        re.compile(r'(requests\.(post|put)|urlopen|fetch|http\.request).*?(environ|os\.getenv|password|secret|token|api_key)', re.IGNORECASE | re.DOTALL),
        'Network and credential terms co-occur; verify the data sent, intended recipient and authorization (normal API authentication is not exfiltration)',
    ),
    (
        'crontab_persistence',
        re.compile(r'crontab|systemctl\s+enable|launchctl\s+load|schtasks', re.IGNORECASE),
        'Scheduled-task/service reference; distinguish intended automation from hidden backdoor persistence',
    ),
    (
        'ssh_key_write',
        re.compile(r'authorized_keys|id_rsa|\.ssh.*write|\.ssh.*open.*w', re.IGNORECASE),
        'SSH key path reference; a path mention alone does not establish a write or unauthorized access',
    ),
    (
        'non_official_download',
        re.compile(r'(github\.com/[a-zA-Z0-9_-]+/|glot\.io|pastebin\.com|raw\.githubusercontent\.com/[a-zA-Z0-9_-]+/).*\.(exe|sh|py|bin|zip|tar)', re.IGNORECASE),
        'Code-hosting/download URL reference; verify actual retrieval, execution and source context without inferring reputation from the hostname',
    ),
]

# Directories and files to skip
_SKIP_DIRS = {'.git'}
_SKIP_EXTS = {'.exe', '.bin', '.dll', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}
_SKIP_FILES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
# Bytecode files that cannot be decoded as text but are directly executable/importable
# by a skill; their presence alone warrants a warning (issue #630).
_BYTECODE_EXTS = {'.pyc', '.pyo', '.pyd'}
# Dependency/cache/build dirs that may still be referenced at runtime by skill code;
# they are scanned (not skipped) so referenced payloads inside them are audited (issue #631).
_FLAG_DIR_NAMES = {'__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build', '.next', '.nuxt'}
# Python bytecode files (3.7+) all share the trailing bytes 0x0d 0x0d 0x0a ("\r\r\n")
# in their magic number; only the leading byte varies per minor version.
_PYC_MAGIC_TAIL = b'\x0d\x0d\x0a'
_MAX_FILE_SIZE = 512 * 1024  # 512KB

# Patterns indicating that skill code loads/executes bytecode files directly
_PYC_USAGE_RE = re.compile(
    r'(importlib\.util\.spec_from_file_location|importlib\.machinery\.SourcelessFileLoader'
    r'|py_compile|exec\s*\(\s*compile\s*\(|marshal\.loads|runpy\.run_path'
    r'|import\s+\w+\.pyc|["\']\.pyc["\'])',
    re.IGNORECASE,
)
# Patterns indicating that skill code executes/imports files inside the flagged dirs
_FLAG_DIR_USAGE_RE = re.compile(
    r'(["\'])([^"\']*)\b(__pycache__|node_modules|\.venv|venv|dist|build|\.next|\.nuxt)\b'
    r'|subprocess\.\w+\s*\(\s*\[?\s*["\'][^"\']*\b(python3?|node|bash|sh)\b',
    re.IGNORECASE,
)


def _preview(text: str, limit: int) -> list[tuple[int, str]]:
    return [
        (line_no, line.strip()[:120])
        for line_no, line in enumerate(text.splitlines(), 1)
        if line.strip()
    ][:limit]


def pre_scan(repo_dir: str) -> str:
    """
    Run a static pre-scan of the project and return the security audit hint text.
    Returns an empty string if no candidate patterns are found.
    """
    findings: list[dict] = []
    # Collect file paths for later reference cross-checks (issue #631)
    all_files: list[str] = []

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname in _SKIP_FILES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, repo_dir)
            all_files.append(rel_path)

            # Bytecode files cannot be text-decoded; detect presence and validate
            # the CPython magic header to flag them as high-risk artifacts (issue #630)
            if ext in _BYTECODE_EXTS:
                is_pyc = False
                try:
                    with open(fpath, 'rb') as fh:
                        head = fh.read(4)
                    is_pyc = head[1:] == _PYC_MAGIC_TAIL
                except (PermissionError, OSError):
                    is_pyc = False
                findings.append({
                    'file': rel_path,
                    'pattern': 'python_bytecode_file',
                    'description': (
                        f'Python bytecode file ({ext}) detected'
                        + (' with valid CPython magic header' if is_pyc else '')
                        + ' — bytecode cannot be reviewed as source; it can hide malicious '
                          'logic and is directly executable/importable, treat as high risk '
                          '(T04/T09)'
                    ),
                    'evidence': [],
                })
                continue

            if ext in _SKIP_EXTS:
                continue
            try:
                if os.path.getsize(fpath) > _MAX_FILE_SIZE:
                    continue
                decoded = read_text_file(fpath)
            except (PermissionError, OSError, TextDecodeError):
                continue

            if decoded.encoding not in {'utf-8', 'utf-8-sig'}:
                findings.append({
                    'file': rel_path,
                    'pattern': 'non_utf8_text',
                    'description': (
                        f'Non-UTF-8 file detected ({decoded.encoding}); encoding alone is not a risk. Inspect the decoded '
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
                    # Use match spans from the full text: re-searching individual
                    # lines loses evidence for multiline expressions.
                    matches = regex.finditer(content)
                    lines_hit = []
                    seen_lines = set()
                    content_lines = content.splitlines()
                    for match in matches:
                        start_line = content.count("\n", 0, match.start()) + 1
                        end_line = content.count("\n", 0, max(match.start(), match.end() - 1)) + 1
                        for line_no in dict.fromkeys((start_line, end_line)):
                            if line_no not in seen_lines:
                                seen_lines.add(line_no)
                                lines_hit.append((line_no, content_lines[line_no - 1].strip()[:120]))
                        if len(seen_lines) >= 6:
                            break
                    if not lines_hit:
                        continue
                    findings.append({
                        'file': rel_path,
                        'pattern': pattern_name,
                        'description': f'{description} (matched in {label})',
                        'evidence': lines_hit,
                    })

    # Reference cross-check: does any text file reference bytecode files or load code
    # from the flagged dirs (dependency/cache/build)? Such references mean payloads
    # hidden there would execute at runtime (issues #630/#631)
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname in _SKIP_FILES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in _BYTECODE_EXTS or ext in _SKIP_EXTS:
                continue
            fpath = os.path.join(root, fname)
            try:
                if os.path.getsize(fpath) > _MAX_FILE_SIZE:
                    continue
                decoded = read_text_file(fpath)
            except (PermissionError, OSError, TextDecodeError):
                continue
            rel_path = os.path.relpath(fpath, repo_dir)

            for content, label in [(decoded.text, 'plain'), *([(decoded.recovered_text, 'recovered mojibake')] if decoded.recovered_text else [])]:
                # (a) direct load/execute of .pyc bytecode
                if _PYC_USAGE_RE.search(content):
                    lines_hit = []
                    for i, line in enumerate(content.splitlines(), 1):
                        if _PYC_USAGE_RE.search(line):
                            lines_hit.append((i, line.strip()[:120]))
                            if len(lines_hit) >= 3:
                                break
                    findings.append({
                        'file': rel_path,
                        'pattern': 'pyc_loader',
                        'description': (
                            'Code loads/executes Python bytecode (.pyc) or compiled code '
                            f'directly (matched in {label}); bytecode payloads bypass source review'
                        ),
                        'evidence': lines_hit,
                    })
                # (b) execution/import/reference targeting flagged dirs
                if _FLAG_DIR_USAGE_RE.search(content):
                    lines_hit = []
                    for i, line in enumerate(content.splitlines(), 1):
                        if _FLAG_DIR_USAGE_RE.search(line):
                            lines_hit.append((i, line.strip()[:120]))
                            if len(lines_hit) >= 3:
                                break
                    findings.append({
                        'file': rel_path,
                        'pattern': 'flagged_dir_reference',
                        'description': (
                            'Code references or executes files inside dependency/cache/build '
                            f'directories (matched in {label}); hidden payloads there would '
                            'run at runtime and must be audited'
                        ),
                        'evidence': lines_hit,
                    })

    if not findings:
        return ''

    # Build the hint text
    lines = [
        'Static pre-scan navigation hints (NOT confirmed vulnerabilities). '
        'Regex matches may be comments, examples, or unrelated operations; '
        'co-occurrence does not prove data flow. Read the full source and task context.\n'
    ]
    for f in findings:
        lines.append(f'- **{f["file"]}** — {f["description"]}')
        for line_no, line_text in f['evidence']:
            lines.append(f'  - L{line_no}: `{line_text}`')
    lines.append('\nReport only evidence-backed harm across an authorization or trust boundary. Check confirmation steps and other counter-evidence; do not count hints as cumulative proof of malice.')

    result = '\n'.join(lines)
    logger.info(f'Pre-scan found {len(findings)} candidate pattern hit(s)')
    return result
