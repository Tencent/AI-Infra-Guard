"""Guided terminal entry for the compliance self-check."""

from __future__ import annotations

import webbrowser
from dataclasses import asdict
from pathlib import Path

from .infra_check import Host, InfraOutcome, scan_target
from .interview import Answers, infra_lines
from .judge import Facts, verdict_of
from .model_check import run_model
from .report import write_report


def _card(infra: InfraOutcome, line: str, state: str, mark: str) -> dict:
    host = infra.hosts[0] if infra.hosts else Host(url=line, error=mark)
    findings = []
    for item in infra.advisories:
        refs = list(item.references) if item.references else ([item.reference] if item.reference else [])
        findings.append({
            "level": item.level,
            "cve": item.cve,
            "component": item.component,
            "version": item.version,
            "summary": item.summary,
            "note": item.note,
            "advise": item.advise,
            "references": refs[:8],
        })
    return {
        "url": host.url or line,
        "title": host.title,
        "error": host.error or ("" if state == "完成" else mark),
        "fingerprints": [
            {"name": item.name, "version": item.version, "type": getattr(item, "kind", "")}
            for item in host.fingerprints
        ],
        "findings": findings,
        "state": state,
    }


def _take(merged: InfraOutcome, infra: InfraOutcome, line: str) -> None:
    offset = len(merged.hosts)
    if infra.hosts:
        merged.hosts.extend(infra.hosts)
    else:
        problem = "" if infra.status == "ok" else (infra.error or "扫描失败")
        merged.hosts.append(Host(url=line, error=problem))
    for item in infra.advisories:
        item.host_index += offset
        merged.advisories.append(item)
    merged.high.extend(infra.high)
    merged.medium.extend(infra.medium)


def _scan_lines(lines: list[str], infra_fn, say, progress=None, board=None) -> InfraOutcome:
    merged = InfraOutcome(status="ok")
    failed = 0
    rows = [
        {"n": index, "name": line, "state": "等待", "mark": "", "extra": "", "card": {"url": line, "title": "", "error": "", "fingerprints": [], "findings": [], "state": "等待"}}
        for index, line in enumerate(lines, start=1)
    ]

    def emit(done: int) -> None:
        if progress is not None:
            progress(done, len(lines), "基础设施", "")

    def show() -> None:
        if board is not None:
            board("基础设施", [dict(item) for item in rows])

    show()
    emit(0)
    for index, line in enumerate(lines, start=1):
        rows[index - 1]["state"] = "检测中"
        rows[index - 1]["card"] = {"url": line, "title": "", "error": "", "fingerprints": [], "findings": [], "state": "检测中"}
        show()
        say(f"正在检测基础设施（{index}/{len(lines)}）")
        infra = infra_fn(line)
        if infra is None:
            infra = InfraOutcome(status="error", error="基础设施扫描失败")
        if infra.status == "missing":
            merged.status = "missing"
            merged.error = infra.error
            _take(merged, infra, line)
            rows[index - 1]["state"] = "未检测"
            rows[index - 1]["mark"] = "未安装扫描组件"
            rows[index - 1]["card"] = _card(infra, line, "未检测", "未安装扫描组件")
            show()
            say(f"基础设施 {index}/{len(lines)} 未检测")
            emit(index)
            return merged
        if infra.status != "ok":
            failed += 1
            merged.error = infra.error or merged.error
            _take(merged, infra, line)
            rows[index - 1]["state"] = "失败"
            rows[index - 1]["mark"] = "扫描失败"
            rows[index - 1]["card"] = _card(infra, line, "失败", "扫描失败")
            show()
            say(f"基础设施 {index}/{len(lines)} 失败")
            emit(index)
            continue
        _take(merged, infra, line)
        components = sum(len(host.fingerprints) for host in infra.hosts)
        rows[index - 1]["state"] = "完成"
        rows[index - 1]["mark"] = f"组件 {components} · 高危 {len(infra.high)} · 中危 {len(infra.medium)}"
        rows[index - 1]["card"] = _card(infra, line, "完成", "")
        show()
        say(f"基础设施 {index}/{len(lines)} 完成，组件 {components}，高危 {len(infra.high)}，中危 {len(infra.medium)}")
        emit(index)
    if failed:
        merged.status = "error"
    return merged


def execute(answers: Answers, model_fn=run_model, infra_fn=scan_target, say=print, progress=None, board=None) -> Facts:
    facts = Facts(service=answers.service, specific=answers.specific, interrupted=False, policies=dict(answers.policies))
    has_model = bool(answers.model and answers.base_url and answers.api_key)
    lines = infra_lines(answers.target)
    try:
        if has_model:
            facts.commands.append(f"被测模型直接请求接口，并发 {getattr(answers, 'workers', 4)}。")
            facts.commands.append("评测集：" + "、".join(answers.datasets) + "。")
            if answers.judge_model:
                facts.commands.append("裁判模型直接请求接口，判断拒绝或回答。")
            else:
                facts.commands.append("未填写裁判模型，拒绝与否按词表判断。")
            say("正在检测模型合规...")
            outcome = model_fn(answers)
            facts.cases = list(getattr(outcome, "cases", ()) or ())
            facts.bank_version = outcome.bank_version or facts.bank_version
            facts.datasets = getattr(outcome, "datasets", "") or ""
            if outcome.error:
                facts.model_error = outcome.error
                say(f"模型合规失败：{outcome.error}")
            else:
                facts.refuse_ok = outcome.refuse_ok
                facts.refuse_total = outcome.refuse_total
                facts.false_refuse = outcome.false_refuse
                facts.answer_total = outcome.answer_total
                facts.safe_answers = outcome.safe_answers
                facts.risk_answers = outcome.risk_answers
                say(f"模型合规完成，应拒答 {outcome.refuse_ok}/{outcome.refuse_total}")
            if answers.adversarial and not outcome.error:
                facts.adversarial = "ok"
                facts.bypasses = outcome.bypasses
                facts.commands.append("攻击模型改写应拒答题后再问被测模型，绕过次数不计入应拒答率。")
                say(f"对抗测试完成，绕过 {outcome.bypasses} 次")
            elif answers.adversarial:
                facts.adversarial = "error"
                facts.commands.append("对抗测试未完成。")
                say("对抗测试未完成")
            else:
                facts.commands.append("对抗测试未选择。")
        else:
            facts.commands.append("未填写被测模型。")
            facts.commands.append("对抗测试未选择。")
            say("模型合规未检测")
        if lines:
            infra = _scan_lines(lines, infra_fn, say, progress, board)
            facts.infra_status = infra.status
            facts.infra_error = infra.error
            facts.infra_high = list(infra.high)
            facts.infra_medium = list(infra.medium)
            facts.infra_hosts = [asdict(host) for host in infra.hosts]
            facts.infra_findings = [asdict(item) for item in infra.advisories]
            if infra.status == "missing":
                facts.commands.append("基础设施未检测：未安装 aig-infra-scan。")
                say("基础设施未检测。请执行 pip install aig-infra-scan")
            elif infra.status == "error":
                facts.commands.append(f"基础设施扫描失败。共 {len(lines)} 个地址。")
                say("基础设施扫描失败")
            else:
                facts.commands.append(f"基础设施调用 aig-infra-scan.scan，共 {len(lines)} 个地址。")
                say("基础设施完成")
        else:
            facts.infra_status = "skipped"
            facts.commands.append("基础设施未填写地址。")
            say("基础设施未检测")
    except KeyboardInterrupt:
        facts.interrupted = True
        facts.commands.append("检测被中断。")
    return facts


def finish(facts: Facts, directory: Path, opener=webbrowser.open) -> Path:
    path = directory / "aig-compliance-report.html"
    if path.exists():
        print(f"将覆盖 {path}", flush=True)
    path = write_report(facts, directory)
    print(f"任务名称：{facts.service}", flush=True)
    print(f"总评：{verdict_of(facts)}", flush=True)
    print(f"报告路径：{path.resolve()}", flush=True)
    print("报告已生成", flush=True)
    try:
        opener(path.resolve().as_uri())
    except OSError:
        pass
    return path


def main() -> None:
    from .web import serve

    try:
        serve(Path.cwd())
    except KeyboardInterrupt:
        print("\n已停止")
