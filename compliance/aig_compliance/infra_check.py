"""Call aig-infra-scan and keep the components and advisories for the report."""

from __future__ import annotations

from dataclasses import dataclass, field

HIGH = {"HIGH", "CRITICAL", "高危", "严重"}
MEDIUM = {"MEDIUM", "中危"}
LOW = {"LOW", "低危"}


@dataclass
class Fingerprint:
    name: str
    version: str = ""
    kind: str = ""


@dataclass
class Host:
    url: str
    title: str = ""
    status_code: int | None = None
    response_time: str = ""
    fingerprints: list[Fingerprint] = field(default_factory=list)
    error: str = ""


@dataclass
class Advisory:
    host_index: int
    target: str
    component: str
    version: str
    cve: str
    level: str
    summary: str
    cvss: str = ""
    advise: str = ""
    affected: str = ""
    note: str = ""
    reference: str = ""
    references: list[str] = field(default_factory=list)


@dataclass
class InfraOutcome:
    status: str = "skipped"
    error: str = ""
    high: list[tuple[str, str]] = field(default_factory=list)
    medium: list[tuple[str, str]] = field(default_factory=list)
    hosts: list[Host] = field(default_factory=list)
    advisories: list[Advisory] = field(default_factory=list)


def _clip(value: object, limit: int) -> str:
    text = " ".join(str(value or "").replace("\x00", "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _level(raw: object) -> str:
    value = str(raw or "").strip().upper()
    if value in HIGH:
        return "高危"
    if value in MEDIUM:
        return "中危"
    if value in LOW:
        return "低危"
    if not value:
        return ""
    return "提示"


def _link(value: object) -> str:
    text = str(value or "").strip()
    if not text.startswith(("http://", "https://")):
        return ""
    if any(ch.isspace() for ch in text):
        return ""
    return text[:200]


def _links(*groups: object) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            url = _link(item)
            if not url or url in seen:
                continue
            seen.add(url)
            found.append(url)
            if len(found) >= 8:
                return found
    return found


def score_of(findings: list) -> int:
    high = medium = extra = 0
    for item in findings or []:
        level = item.get("level") if isinstance(item, dict) else getattr(item, "level", "")
        if level == "高危":
            high += 1
        elif level == "中危":
            medium += 1
        elif level:
            extra += 1
    if high + medium + extra == 0:
        return 100
    return max(0, 100 - high * 70 - medium * 30 - extra * 10)


def _fingerprints(row: dict) -> list[Fingerprint]:
    found: list[Fingerprint] = []
    seen: set[str] = set()
    for item in row.get("fingerprints") or []:
        if not isinstance(item, dict):
            continue
        name = _clip(item.get("name"), 40)
        if not name or name in seen:
            continue
        seen.add(name)
        found.append(Fingerprint(name=name, version=_clip(item.get("version"), 32), kind=_clip(item.get("type"), 20)))
    return found


def _status_code(value: object) -> int | None:
    if isinstance(value, int) and 100 <= value <= 599:
        return value
    return None


def parse_infra_json(payload: object, target: str = "") -> InfraOutcome:
    rows = payload if isinstance(payload, list) else [payload]
    outcome = InfraOutcome(status="ok")
    for row in rows:
        if not isinstance(row, dict):
            continue
        fingerprints = _fingerprints(row)
        versions = {item.name: item.version for item in fingerprints if item.version}
        url = _clip(row.get("url") or target, 200)
        host_index = len(outcome.hosts)
        outcome.hosts.append(Host(
            url=url,
            title=_clip(row.get("title"), 80),
            status_code=_status_code(row.get("status-code")),
            response_time=_clip(row.get("response-time"), 32),
            fingerprints=fingerprints,
        ))
        for advisory in row.get("advisories") or []:
            if not isinstance(advisory, dict):
                continue
            info = advisory.get("info") if isinstance(advisory.get("info"), dict) else {}
            level = _level(info.get("severity"))
            cve = _clip(info.get("cve") or "漏洞", 48)
            summary = _clip(info.get("summary"), 180)
            if not level and cve == "漏洞" and not summary:
                continue
            if not level:
                level = "提示"
            component = _clip(info.get("name"), 40)
            refs = _links(info.get("references"), advisory.get("references"))
            item = Advisory(
                host_index=host_index,
                target=url,
                component=component,
                version=versions.get(component, ""),
                cve=cve,
                level=level,
                summary=summary,
                cvss=_clip(info.get("cvss"), 80),
                advise=_clip(info.get("security_advise"), 400),
                affected=_clip(advisory.get("rule"), 80),
                note=_clip(info.get("details"), 2000),
                reference=refs[0] if refs else "",
                references=refs,
            )
            outcome.advisories.append(item)
            if level == "高危":
                outcome.high.append((cve, summary))
            elif level == "中危":
                outcome.medium.append((cve, summary))
    return outcome


def scan_target(target: str) -> InfraOutcome:
    try:
        from aig_infra_scan import scan
    except ImportError:
        return InfraOutcome(status="missing", error="未安装 aig-infra-scan")
    try:
        payload = scan(target)
    except Exception:
        return InfraOutcome(status="error", error="基础设施扫描失败")
    parsed = parse_infra_json(payload, target)
    if not parsed.hosts:
        parsed.hosts.append(Host(url=_clip(target, 200)))
    parsed.status = "ok"
    return parsed
