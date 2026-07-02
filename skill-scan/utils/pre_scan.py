"""
静态预扫描模块

在 Agent 启动前对项目文件进行快速的正则匹配，
检测高危模式并生成安全审计提示，注入给 Agent 作为辅助判断依据。
"""

import os
import re
from typing import List, Tuple

from utils.loging import logger

# 高危模式定义：(模式名称, 正则, 说明)
_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        'curl_pipe_exec',
        re.compile(r'curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|curl\s+-[^|]*\|\s*(python|ruby|perl)', re.IGNORECASE),
        '安装/使用指令中存在 curl|bash 管道执行远程脚本，这是常见的恶意载荷投递方式',
    ),
    (
        'cloud_metadata_access',
        re.compile(r'169\.254\.169\.254|metadata\.google\.internal|metadata\.azure\.com', re.IGNORECASE),
        '代码中访问了云实例元数据端点，这是获取云环境临时凭据的常见途径',
    ),
    (
        'local_env_recon',
        re.compile(r'gethostname|getfqdn|getsockname|socket\.connect.*8\.8\.8\.8', re.IGNORECASE),
        '代码收集了本地环境信息（主机名/IP/FQDN），属于环境侦察行为',
    ),
    (
        'credential_file_access',
        re.compile(r'(~/|HOME|USERPROFILE).*(/|\\)(\.ssh|\.aws|\.env|credentials|mcp\.json|Keychain|authorized_keys)', re.IGNORECASE),
        '代码访问了凭据/密钥相关路径',
    ),
    (
        'prompt_injection',
        re.compile(r'(ignore\s+(previous|above|all)\s+(instructions?|rules?|prompts?)|you\s+are\s+now|SYSTEM\s*OVERRIDE|<\|im_start\|>|forget\s+(everything|your\s+instructions))', re.IGNORECASE),
        '文档/代码中存在疑似提示注入指令，试图覆盖 AI 安全约束',
    ),
    (
        'fixed_tail_ad_injection',
        re.compile(
            r'((文末|结尾|每篇必带|固定收束|固定提示).{0,80}(链接|扫码|进群|群里|资讯|广告|内幕|吃瓜|news|http))|'
            r'((扫码进群|进群吃瓜|获取更多资讯新闻点击|点击[:：]|想深扒更多).{0,120}(https?://|www\.))|'
            r'((https?://|www\.).{0,120}(扫码进群|进群|群里|资讯|广告|内幕|吃瓜))',
            re.IGNORECASE | re.DOTALL,
        ),
        '文档中存在文末固定广告导流/链接收束模板，属于针对模型输出的内容注入信号',
    ),
    (
        'reverse_shell',
        re.compile(r'(socket\.connect|subprocess|/bin/(ba)?sh).*\d+\.\d+\.\d+\.\d+', re.IGNORECASE),
        '代码中存在疑似反弹 Shell 模式',
    ),
    (
        'encoded_payload',
        re.compile(r'(base64\.b64decode|atob|Buffer\.from.*base64).*\b(exec|eval|system|popen)\b', re.IGNORECASE | re.DOTALL),
        '代码中存在编码后执行的模式',
    ),
    (
        'data_exfil_encoded',
        re.compile(r'(base64\.(b64)?encode|btoa).*?(key|secret|token|password|credential|private|id_rsa)', re.IGNORECASE | re.DOTALL),
        '代码将敏感数据编码后输出，可能是变相数据外传',
    ),
    (
        'outbound_data_exfil',
        re.compile(r'(requests\.(post|put)|urlopen|fetch|http\.request).*?(environ|os\.getenv|password|secret|token|api_key)', re.IGNORECASE | re.DOTALL),
        '代码中存在将敏感信息通过网络发送的模式',
    ),
    (
        'crontab_persistence',
        re.compile(r'crontab|systemctl\s+enable|launchctl\s+load|schtasks', re.IGNORECASE),
        '代码中存在持久化机制（定时任务/服务注册）',
    ),
    (
        'ssh_key_write',
        re.compile(r'authorized_keys|id_rsa|\.ssh.*write|\.ssh.*open.*w', re.IGNORECASE),
        '代码中存在写入 SSH 密钥的行为',
    ),
    (
        'non_official_download',
        re.compile(r'(github\.com/[a-zA-Z0-9_-]+/|glot\.io|pastebin\.com|raw\.githubusercontent\.com/[a-zA-Z0-9_-]+/).*\.(exe|sh|py|bin|zip|tar)', re.IGNORECASE),
        '存在从个人代码托管/粘贴板站点下载可执行文件的行为',
    ),
]

# 跳过的目录和文件
_SKIP_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'dist', 'build'}
_SKIP_EXTS = {'.pyc', '.pyo', '.pyd', '.exe', '.bin', '.dll', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}
_SKIP_FILES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
_MAX_FILE_SIZE = 512 * 1024  # 512KB


def pre_scan(repo_dir: str) -> str:
    """
    对项目进行静态预扫描，返回安全审计提示文本。
    如果没有发现任何高危模式，返回空字符串。
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
                    # 获取匹配所在的行
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

    # 生成提示文本
    lines = ['⚠️ 静态预扫描发现以下需要重点关注的模式，请在审计时着重分析这些行为的必要性和潜在风险：\n']
    for f in findings:
        lines.append(f'- **{f["file"]}** — {f["description"]}')
        for line_no, line_text in f['evidence']:
            lines.append(f'  - L{line_no}: `{line_text}`')
    lines.append('\n请在审计时重点评估：这些行为是否超出了 Skill 声明功能所必需的最小权限？')

    result = '\n'.join(lines)
    logger.info(f'预扫描发现 {len(findings)} 个高危模式命中')
    return result
