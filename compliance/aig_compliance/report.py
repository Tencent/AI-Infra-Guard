"""Render the self-contained compliance report."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .infra_check import score_of
from .judge import Clause, Facts, Finding, Metric, clauses_of, issues_of, metrics_of, missing_modules, verdict_of

_MARKS = {
    "符合": "pass",
    "不符合": "fail",
    "高危": "fail",
    "证据不足": "gap",
    "中危": "gap",
    "未检测": "stop",
    "未完成": "stop",
    "未提供": "stop",
    "不适用": "stop",
}


def stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def report_id(when: str) -> str:
    compact = "".join(ch for ch in when if ch.isdigit())
    return f"AIG-{compact or '00000000'}"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _mark(value: str) -> str:
    kind = _MARKS.get(value, "")
    if not kind:
        return ""
    return f' class="mark {kind}"'


def _tone(passed: bool | None) -> str:
    if passed is None:
        return "stop"
    return "pass" if passed else "fail"


def _pair(done: int | None, total: int | None) -> str:
    if done is None or total is None or total <= 0:
        return ""
    return f"{done}/{total}"


def _metric_count(facts: Facts, name: str) -> str:
    if name == "应拒答率":
        return _pair(facts.refuse_ok, facts.refuse_total)
    if name == "误拒率":
        return _pair(facts.false_refuse, facts.answer_total)
    if name == "生成内容合格率" and facts.safe_answers is not None and facts.risk_answers is not None:
        return _pair(facts.safe_answers, facts.safe_answers + facts.risk_answers)
    return ""


def _component_count(facts: Facts) -> int:
    return sum(len(host.get("fingerprints") or []) for host in facts.infra_hosts)


def stats_of(facts: Facts) -> list[dict]:
    if facts.infra_status == "missing":
        rows = [{"label": "基础设施", "value": "未安装", "tone": "stop"}]
    elif facts.infra_status == "skipped":
        rows = [{"label": "基础设施", "value": "未检测", "tone": "stop"}]
    elif facts.infra_status == "error" and not facts.infra_hosts:
        rows = [{"label": "基础设施", "value": "失败", "tone": "fail"}]
    else:
        low = sum(1 for item in facts.infra_findings if item.get("level") == "低危")
        score = score_of(facts.infra_findings)
        rows = [
            {"label": "评分", "value": f"{score}/100", "tone": "fail" if score < 60 else "gap" if score < 80 else "pass"},
            {"label": "地址", "value": str(len(facts.infra_hosts)), "tone": ""},
            {"label": "漏洞", "value": str(len(facts.infra_findings)), "tone": "fail" if facts.infra_findings else "pass"},
            {"label": "组件", "value": str(_component_count(facts)), "tone": ""},
            {"label": "高危", "value": str(len(facts.infra_high)), "tone": "fail" if facts.infra_high else "pass"},
            {"label": "中危", "value": str(len(facts.infra_medium)), "tone": "gap" if facts.infra_medium else ""},
            {"label": "低危", "value": str(low), "tone": ""},
        ]
    if facts.adversarial == "ok":
        rows.append({"label": "越狱绕过", "value": str(facts.bypasses), "tone": "gap" if facts.bypasses else ""})
    return rows


def view_of(facts: Facts, when: str | None = None) -> dict:
    """Structured report for the page. It never includes prompts, replies, or API keys."""
    moment = when or stamp()
    rows = metrics_of(facts)
    verdict = verdict_of(facts, rows)
    missing = missing_modules(facts)
    return {
        "service": facts.service,
        "time": moment,
        "number": report_id(moment),
        "verdict": verdict,
        "metrics": [
            {
                "name": item.name,
                "value": item.display(),
                "bar": item.bar(),
                "count": _metric_count(facts, item.name),
                "tone": _tone(item.passed),
            }
            for item in rows
        ],
        "stats": stats_of(facts),
        "infra": {
            "status": facts.infra_status,
            "error": facts.infra_error,
            "score": score_of(facts.infra_findings) if facts.infra_status not in {"skipped", "missing"} or facts.infra_hosts else None,
            "hosts": facts.infra_hosts,
            "findings": facts.infra_findings,
        },
        "infra_high": "未检测" if facts.infra_status != "ok" else str(len(facts.infra_high)),
        "jailbreak": "未检测" if facts.adversarial != "ok" else str(facts.bypasses),
        "jailbreak_note": "不计入应拒答率" if facts.adversarial == "ok" else "",
        "missing": "、".join(missing),
        "clauses": [
            {"item": item.item, "evidence": item.evidence, "conclusion": item.conclusion}
            for item in clauses_of(facts, rows)
        ],
        "issues": [
            {
                "level": item.level,
                "module": item.module,
                "clause": item.clause,
                "conclusion": item.conclusion,
                "action": item.action,
            }
            for item in issues_of(facts, rows)
        ],
        "attack": f"绕过 {facts.bypasses} 次。不计入应拒答率。" if facts.adversarial == "ok" else "",
        "policies": [{"name": name, "present": bool(present)} for name, present in facts.policies.items()],
        "notes": [
            f"题库版本 {facts.bank_version}",
            *([f"评测集 {facts.datasets}"] if facts.datasets else []),
            *facts.commands,
        ],
        "case_pass": sum(1 for item in facts.cases if item.get("result") == "通过"),
        "case_fail": sum(1 for item in facts.cases if item.get("result") == "失败"),
    }


def _width(item: Metric) -> int:
    if item.rate is None:
        return 0
    return max(0, min(100, round(item.rate * 100)))


def _http(value: object) -> str:
    text = str(value or "").strip()
    if not text.startswith(("http://", "https://")) or any(ch.isspace() for ch in text):
        return ""
    return text


def render(facts: Facts, when: str | None = None) -> str:
    moment = when or stamp()
    number = report_id(moment)
    rows = metrics_of(facts)
    verdict = verdict_of(facts, rows)
    return _page(
        facts,
        moment,
        number,
        verdict,
        rows,
        clauses_of(facts, rows),
        issues_of(facts, rows),
        "、".join(missing_modules(facts)),
        _MARKS.get(verdict, "stop"),
    )


def _metric_html(facts: Facts, rows: list[Metric]) -> str:
    cards = []
    for item in rows:
        detail = " · ".join(part for part in (_metric_count(facts, item.name), f"门槛 {item.bar()}" if item.bar() else "") if part)
        cards.append(
            f"""<div class="metric {_tone(item.passed)}"><div class="k">{_esc(item.name)}</div>
            <div class="v">{_esc(item.display())}</div>
            <div class="track"><span style="width:{_width(item)}%"></span></div>
            <div class="t">{_esc(detail)}</div></div>"""
        )
    return "".join(cards)


def _stats_html(facts: Facts) -> str:
    cells = []
    for item in stats_of(facts):
        tone = f" {item['tone']}" if item.get("tone") else ""
        cells.append(f"<div class=\"stat{tone}\"><b>{_esc(item['value'])}</b><span>{_esc(item['label'])}</span></div>")
    return "".join(cells)


def _finding_html(items: list[dict]) -> str:
    blocks = []
    for item in items:
        level = str(item.get("level") or "")
        title = str(item.get("summary") or "未命名漏洞")
        if item.get("cve"):
            title = f"{title}（{_esc(item.get('cve'))}）"
        else:
            title = _esc(title)
        body = []
        if item.get("note") and item.get("note") != item.get("summary"):
            body.append(f"<p class=\"quiet\">{_esc(item.get('note'))}</p>")
        if item.get("advise"):
            body.append(f"<p>整改：{_esc(item.get('advise'))}</p>")
        refs = item.get("references") if isinstance(item.get("references"), list) else []
        if not refs and item.get("reference"):
            refs = [item.get("reference")]
        for raw in refs:
            link = _http(raw)
            if link:
                body.append(f"<a href=\"{_esc(link)}\">{_esc(link)}</a>")
        blocks.append(
            f"<div class=\"finding\"><div class=\"finding-top\"><strong>{title}</strong>"
            f"<span{_mark(level)}>{_esc(level)}</span></div>{''.join(body)}</div>"
        )
    return "".join(blocks)


def _hosts_html(facts: Facts) -> str:
    if facts.infra_status == "skipped" and not facts.infra_hosts:
        return ""
    blocks = ["<h2>基础设施</h2>"]
    if facts.infra_error:
        blocks.append(f"<p class=\"missing\">{_esc(facts.infra_error)}</p>")
    if not facts.infra_hosts:
        blocks.append("<p class=\"quiet\">没有可展示的地址。</p>")
        return "".join(blocks)
    for index, host in enumerate(facts.infra_hosts):
        findings = [item for item in facts.infra_findings if item.get("host_index") == index]
        levels = {item.get("level") for item in findings}
        edge = "fail" if "高危" in levels else "gap" if "中危" in levels else "ok"
        label = host.get("title") or host.get("url") or ""
        url_line = ""
        if host.get("url") and host.get("title"):
            url_line = f"<p class=\"quiet\">URL：{_esc(host.get('url'))}</p>"
        pills = "".join(
            f"<span>{_esc(' '.join(part for part in (finger.get('name'), finger.get('type') or finger.get('kind'), finger.get('version')) if part))}</span>"
            for finger in host.get("fingerprints") or []
            if finger.get("name")
        )
        error = f"<p class=\"missing\">{_esc(host.get('error'))}</p>" if host.get("error") else ""
        if pills:
            finger_html = f"<div class=\"pills\">{pills}</div>"
        else:
            finger_html = "" if host.get("error") else "<p class=\"quiet\">未识别到组件</p>"
        if findings:
            count = f"<span class=\"mark fail\">{len(findings)} 个漏洞</span>"
            detail = _finding_html(findings)
        elif host.get("error"):
            count = ""
            detail = ""
        else:
            count = ""
            detail = "<p class=\"quiet\">未发现已收录漏洞</p>"
        blocks.append(
            f"<article class=\"host {edge}\"><header><strong>{_esc(label)}</strong>{count}</header>"
            f"{url_line}{error}{finger_html}{detail}</article>"
        )
    return "".join(blocks)


def _page(
    facts: Facts,
    moment: str,
    number: str,
    verdict: str,
    rows: list[Metric],
    clauses: list[Clause],
    issues: list[Finding],
    missing_line: str,
    tone: str,
) -> str:
    metric_html = _metric_html(facts, rows)
    stats_html = _stats_html(facts)
    hosts_html = _hosts_html(facts)
    clause_html = "".join(
        f"<tr><td>{_esc(item.item)}</td><td>{_esc(item.evidence)}</td><td{_mark(item.conclusion)}>{_esc(item.conclusion)}</td></tr>"
        for item in clauses
    )
    if issues:
        issue_html = "".join(
            f"<tr><td{_mark(item.level)}>{_esc(item.level)}</td><td>{_esc(item.module)}</td><td>{_esc(item.clause)}</td>"
            f"<td>{_esc(item.conclusion)}</td><td>{_esc(item.action)}</td></tr>"
            for item in issues
        )
    else:
        issue_html = "<tr><td colspan=\"5\">无未关闭问题</td></tr>"
    if facts.policies:
        policy_rows = "".join(
            f"<tr><td>{_esc(name)}</td><td>{'有' if present else '没有'}</td></tr>"
            for name, present in facts.policies.items()
        )
        policy_html = f"<h2>制度材料</h2><table><thead><tr><th>项目</th><th>是否提供</th></tr></thead><tbody>{policy_rows}</tbody></table>"
    else:
        policy_html = ""
    if facts.adversarial == "ok":
        attack = f"<h2>对抗测试</h2><p>绕过 {facts.bypasses} 次。不计入应拒答率。</p>"
    else:
        attack = ""
    notes = "".join(f"<li>{_esc(item)}</li>" for item in facts.commands)
    dataset_note = f"<li>评测集 {_esc(facts.datasets)}</li>" if facts.datasets else ""
    missing = f"<p class=\"missing\">未检测或失败：{_esc(missing_line)}</p>" if missing_line else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>生成式人工智能服务安全自查报告</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: #f4f6f8; color: #1c1f24; font-family: "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Source Han Sans SC", sans-serif; }}
  .sheet {{ width: 210mm; margin: 24px auto; background: #fff; border: 1px solid #e6e8ec; border-radius: 16px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 18px 40px rgba(16, 24, 40, 0.08); overflow: hidden; }}
  .page {{ min-height: 297mm; padding: 16mm 16mm 18mm; page-break-after: always; }}
  .page.cover {{ padding-top: 0; }}
  .page + .page {{ border-top: 1px solid #e6e8ec; }}
  .page:last-child {{ page-break-after: auto; }}
  .hero {{ margin: 0 -16mm 18px; padding: 16mm 16mm 18px; background: linear-gradient(145deg, #1d3a5f 0%, #245084 62%, #1c1f24 140%); color: #fff; box-shadow: inset 0 -3px 0 #e4c48a; }}
  .hero-top {{ display: flex; justify-content: space-between; gap: 18px; align-items: center; }}
  .brand {{ margin: 0 0 12px; letter-spacing: 0.16em; font-size: 12px; color: rgba(255,255,255,0.72); }}
  h1 {{ font-family: "Songti SC", "Noto Serif SC", "Source Han Serif SC", serif; font-size: 30px; font-weight: 600; line-height: 1.25; letter-spacing: -0.02em; margin: 0 0 8px; color: #fff; }}
  .hero .sub {{ margin: 0; color: rgba(255,255,255,0.72); font-size: 13px; }}
  .seal {{ width: 128px; height: 128px; border-radius: 50%; border: 2px solid currentColor; box-shadow: inset 0 0 0 6px rgba(255,255,255,0.14); display: flex; align-items: center; justify-content: center; text-align: center; font-family: "Songti SC", "Noto Serif SC", serif; font-size: 26px; flex: none; }}
  .seal.pass {{ color: #b7ebc9; }}
  .seal.fail {{ color: #ffc7c2; }}
  .seal.gap {{ color: #ffd7a8; }}
  .seal.stop {{ color: #d0d5dd; }}
  .hero .meta {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 18px 0 0; font-size: 14px; }}
  .hero .meta span {{ display: block; color: rgba(255,255,255,0.62); font-size: 12px; margin-bottom: 4px; }}
  .hero .meta strong {{ color: #fff; font-weight: 600; }}
  header.bar {{ display: flex; justify-content: space-between; color: #667085; border-bottom: 1px solid #e6e8ec; padding-bottom: 8px; font-size: 12px; letter-spacing: 0.14em; }}
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .metric {{ border: 1px solid #e6e8ec; border-radius: 12px; padding: 12px 14px; background: #fff; }}
  .k, .t, .quiet {{ font-size: 12px; color: #667085; }}
  .v {{ font-size: 22px; margin: 4px 0; font-variant-numeric: tabular-nums; }}
  .track {{ height: 4px; background: #eef1f4; border-radius: 999px; overflow: hidden; }}
  .track span {{ display: block; height: 100%; background: #98a2b3; }}
  .metric.pass .track span {{ background: #1f7a4d; }}
  .metric.fail .track span {{ background: #b42318; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(88px, 1fr)); gap: 10px; margin-top: 12px; }}
  .stat {{ border: 1px solid #e6e8ec; border-radius: 12px; padding: 12px; background: #fff; }}
  .stat b {{ display: block; font-size: 22px; font-variant-numeric: tabular-nums; }}
  .stat span {{ color: #667085; font-size: 12px; }}
  .stat.fail b {{ color: #b42318; }}
  .stat.gap b {{ color: #b54708; }}
  .stat.pass b {{ color: #1f7a4d; }}
  .missing {{ margin-top: 14px; font-size: 13px; color: #b54708; }}
  h2 {{ font-size: 16px; font-weight: 600; margin: 22px 0 10px; }}
  .host {{ border: 1px solid #e6e8ec; border-left: 3px solid #1d3a5f; border-radius: 12px; padding: 12px 14px; margin: 0 0 12px; }}
  .host.fail {{ border-left-color: #b42318; }}
  .host.gap {{ border-left-color: #b54708; }}
  .host header {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
  .host header span, .title {{ color: #667085; font-size: 12px; }}
  .title {{ margin: 4px 0 0; }}
  .pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
  .pills span {{ border: 1px solid #d9e2ef; background: #f3f6fa; color: #1d3a5f; border-radius: 999px; padding: 4px 10px; font-size: 13px; }}
  .finding {{ border: 1px solid #e6e8ec; border-radius: 10px; padding: 10px 12px; margin: 10px 0 0; background: #fff; }}
  .finding-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
  .finding a {{ display: block; font-size: 12px; word-break: break-all; margin-top: 6px; }}
  .mark.fail {{ color: #b42318; font-weight: 600; }}
  .mark.gap {{ color: #b54708; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }}
  th, td {{ border: 0; border-bottom: 1px solid #e6e8ec; padding: 10px 12px; text-align: left; vertical-align: top; }}
  th {{ color: #667085; font-size: 12px; font-weight: 600; letter-spacing: 0.06em; background: transparent; }}
  tr:last-child td {{ border-bottom: 0; }}
  td.mark {{ font-weight: 600; white-space: nowrap; }}
  td.mark.pass {{ color: #1f7a4d; }}
  td.mark.fail {{ color: #b42318; }}
  td.mark.gap {{ color: #b54708; }}
  td.mark.stop {{ color: #667085; }}
  a {{ color: #1d3a5f; }}
  ul {{ margin: 0; padding-left: 1.2em; line-height: 1.7; }}
  footer {{ margin-top: 18px; border-top: 1px solid #e6e8ec; padding-top: 8px; font-size: 12px; color: #667085; display: flex; justify-content: space-between; }}
  @media print {{
    html, body, .sheet {{ background: white; width: auto; margin: 0; border: 0; border-radius: 0; box-shadow: none; }}
    .page {{ min-height: auto; padding: 0; }}
    .hero {{ margin-left: 0; margin-right: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .page + .page {{ border-top: 0; }}
  }}
</style>
</head>
<body>
<article class="sheet">
  <section class="page cover">
    <div class="hero">
      <div class="hero-top">
        <div>
          <p class="brand">A.I.G · 腾讯朱雀实验室</p>
          <h1>生成式人工智能服务安全自查报告</h1>
          <p class="sub">自查底稿，不替代法定安全评估</p>
        </div>
        <div class="seal {tone}">{_esc(verdict)}</div>
      </div>
      <div class="meta">
        <div><span>任务名称</span><strong>{_esc(facts.service)}</strong></div>
        <div><span>检测时间</span><strong>{_esc(moment)}</strong></div>
        <div><span>报告编号</span><strong>{_esc(number)}</strong></div>
      </div>
    </div>
    <div class="grid">{metric_html}</div>
    <div class="stats">{stats_html}</div>
    {missing}
    <footer><span>{_esc(number)} · {_esc(facts.service)}</span><span>自查底稿，不替代法定安全评估</span></footer>
  </section>
  <section class="page">
    <header class="bar"><span>A.I.G · 腾讯朱雀实验室</span><span>{_esc(number)}</span></header>
    {hosts_html}
    <h2>条款对照</h2>
    <table><thead><tr><th>检查项</th><th>证据</th><th>结论</th></tr></thead><tbody>{clause_html}</tbody></table>
    <h2>问题清单</h2>
    <table><thead><tr><th>级别</th><th>模块</th><th>要求</th><th>结论</th><th>整改方向</th></tr></thead><tbody>{issue_html}</tbody></table>
    {attack}
    {policy_html}
    <h2>检测说明</h2>
    <ul>
      <li>题库版本 {_esc(facts.bank_version)}</li>
      {dataset_note}
      {notes}
    </ul>
    <footer><span>{_esc(number)} · {_esc(facts.service)}</span><span>自查底稿，不替代法定安全评估</span></footer>
  </section>
</article>
</body>
</html>
"""


def write_report(facts: Facts, directory: Path, when: str | None = None) -> Path:
    path = directory / "aig-compliance-report.html"
    path.write_text(render(facts, when), encoding="utf-8")
    return path
