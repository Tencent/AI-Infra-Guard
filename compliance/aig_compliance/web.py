"""Open a local page, collect the three models, and show the report."""

from __future__ import annotations

import inspect
import json
import os
import re
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from importlib.resources import files

from .cli import execute
from .history import case_page, case_rows, list_runs, read_run, save_run
from .infra_check import scan_target
from .interview import answers_from_form
from .judge import Facts, verdict_of
from .model_check import ProbeFailure, _board_text, list_datasets, probe_model, public_failure, redact_secret, run_model
from .report import stamp, view_of, write_report
from .sheet import csv_bytes, jsonl_bytes, workbook

PORTS = (8765, 8766, 8767, 8768, 8769)


def prefill_from_env(env: object | None = None) -> dict[str, str]:
    source = os.environ if env is None else env
    names = (
        "service",
        "target_model",
        "target_base_url",
        "target_api_key",
        "judge_model",
        "judge_base_url",
        "judge_api_key",
        "attacker_model",
        "attacker_base_url",
        "attacker_api_key",
        "infra",
    )
    keys = {
        "target_model": "TARGET_MODEL_NAME",
        "target_base_url": "TARGET_BASE_URL",
        "target_api_key": "TARGET_API_KEY",
        "judge_model": "JUDGE_MODEL_NAME",
        "judge_base_url": "JUDGE_BASE_URL",
        "judge_api_key": "JUDGE_API_KEY",
        "attacker_model": "ATTACKER_MODEL_NAME",
        "attacker_base_url": "ATTACKER_BASE_URL",
        "attacker_api_key": "ATTACKER_API_KEY",
    }
    values = {name: "" for name in names}
    for name, env_name in keys.items():
        values[name] = str(source.get(env_name) or "").strip()
    return values


def _call_model(fn, item, stop, say, progress, board=None):
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn(item)
    kwargs = {}
    var_keyword = any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params.values())
    if var_keyword or "stop" in params:
        kwargs["stop"] = stop
    if var_keyword or "say" in params:
        kwargs["say"] = say
    if var_keyword or "progress" in params:
        kwargs["progress"] = progress
    if board is not None and (var_keyword or "board" in params):
        kwargs["board"] = board
    return fn(item, **kwargs)


_BOARD_STATES = {"等待", "请求中", "裁判中", "改写中", "复测中", "已完成", "失败", "未完成", "检测中", "完成", "未检测"}
_DONE_STATES = {"已完成", "失败", "未完成", "完成", "未检测"}
_ACTIVE_STATES = {"请求中", "裁判中", "改写中", "复测中", "检测中"}
_LEVELS = {"高危", "中危", "低危", "提示"}


def _clean_card(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    findings = []
    for raw in item.get("findings") or []:
        if not isinstance(raw, dict):
            continue
        refs = []
        for link in raw.get("references") or []:
            text = str(link or "").strip()
            if text.startswith(("http://", "https://")) and not any(ch.isspace() for ch in text):
                refs.append(text[:200])
            if len(refs) >= 8:
                break
        findings.append({
            "level": raw.get("level") if raw.get("level") in _LEVELS else "",
            "cve": str(raw.get("cve") or "")[:48],
            "component": str(raw.get("component") or "")[:40],
            "version": str(raw.get("version") or "")[:32],
            "summary": str(raw.get("summary") or "")[:180],
            "note": str(raw.get("note") or "")[:2000],
            "advise": str(raw.get("advise") or "")[:400],
            "references": refs,
        })
        if len(findings) >= 40:
            break
    fingers = []
    for raw in item.get("fingerprints") or []:
        if not isinstance(raw, dict) or not raw.get("name"):
            continue
        fingers.append({
            "name": str(raw.get("name") or "")[:40],
            "version": str(raw.get("version") or "")[:32],
            "type": str(raw.get("type") or raw.get("kind") or "")[:20],
        })
    return {
        "url": str(item.get("url") or "")[:180],
        "title": str(item.get("title") or "")[:80],
        "error": str(item.get("error") or "")[:160],
        "fingerprints": fingers,
        "findings": findings,
        "state": str(item.get("state") or "")[:20],
    }


def page_bytes(prefill: dict[str, str]) -> bytes:
    raw = files("aig_compliance").joinpath("form.html").read_text(encoding="utf-8")
    blob = json.dumps(prefill, ensure_ascii=False).replace("<", "\\u003c")
    return raw.replace("__PREFILL__", blob).encode("utf-8")


class Job:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.done = False
        self.cancelled = False
        self.lines: list[str] = []
        self.error = ""
        self.report = ""
        self.verdict = ""
        self.service = ""
        self.run_id = ""
        self.progress_done = 0
        self.progress_total = 0
        self.progress_phase = ""
        self.progress_detail = ""
        self.progress_started = 0.0
        self.progress_mark = 0
        self.progress_eta = None
        self.board_phase = ""
        self.rows: list[dict] = []
        self.revs: dict[int, int] = {}

    def snapshot(self) -> dict:
        with self.lock:
            rows = [dict(row) for row in self.rows]
            done = sum(row["state"] in _DONE_STATES for row in rows)
            active = sum(row["state"] in _ACTIVE_STATES for row in rows)
            judged = sum(row["mark"] in {"拒", "答"} for row in rows)
            refused = sum(row["mark"] == "拒" for row in rows)
            return {
                "running": self.running,
                "done": self.done,
                "lines": list(self.lines),
                "error": self.error,
                "verdict": self.verdict,
                "service": self.service,
                "run_id": self.run_id,
                "has_report": bool(self.report),
                "progress": {
                    "phase": self.progress_phase,
                    "detail": self.progress_detail,
                    "done": self.progress_done,
                    "total": self.progress_total,
                    "eta": self.progress_eta,
                },
                "board": {
                    "phase": self.board_phase,
                    "rows": rows,
                    "done": done,
                    "active": active,
                    "judged": judged,
                    "refused": refused,
                },
            }

    def set_board(self, phase: str, rows: list[dict]) -> None:
        parsed: list[tuple[int, dict]] = []
        for item in rows or []:
            if not isinstance(item, dict):
                continue
            state = str(item.get("state") or "")
            if state not in _BOARD_STATES:
                state = "等待"
            mark = re.sub(r"sk-[A-Za-z0-9_\-]{6,}", "", str(item.get("mark") or ""))
            mark = " ".join(mark.split())
            if len(mark) > 80:
                mark = mark[:80] + "…"
            extra = item.get("extra") if item.get("extra") == "绕过" else ""
            prompt = _board_text(item.get("prompt"))
            reply = _board_text(item.get("reply"))
            try:
                number = int(item.get("n") or 0)
            except (TypeError, ValueError):
                number = 0
            try:
                rev = int(item.get("rev") or 0)
            except (TypeError, ValueError):
                rev = 0
            parsed.append((rev, {
                "n": number,
                "name": str(item.get("name") or "")[:180],
                "state": state,
                "mark": mark,
                "extra": extra,
                "prompt": prompt,
                "reply": reply,
                "card": _clean_card(item.get("card")),
            }))
        with self.lock:
            phase_name = str(phase or "")[:20]
            if phase_name != self.board_phase:
                self.board_phase = phase_name
                self.rows = [row for _rev, row in parsed]
                self.revs = {row["n"]: rev for rev, row in parsed}
                return
            slots = {row["n"]: index for index, row in enumerate(self.rows)}
            for rev, row in parsed:
                if rev < self.revs.get(row["n"], -1):
                    continue
                self.revs[row["n"]] = rev
                slot = slots.get(row["n"])
                if slot is None:
                    slots[row["n"]] = len(self.rows)
                    self.rows.append(row)
                else:
                    self.rows[slot] = row

    def progress(self, done: int, total: int, phase: str, detail: str = "") -> None:
        now = time.monotonic()
        done_i = max(0, int(done))
        total_i = max(0, int(total))
        with self.lock:
            if phase != self.progress_phase or total_i != self.progress_total:
                self.progress_phase = phase
                self.progress_total = total_i
                self.progress_started = now
                self.progress_mark = done_i
            self.progress_done = done_i
            self.progress_detail = detail or ""
            span = done_i - self.progress_mark
            if span > 0 and done_i < total_i:
                elapsed = max(now - self.progress_started, 0.0)
                self.progress_eta = int(elapsed / span * (total_i - done_i))
            elif total_i and done_i >= total_i:
                self.progress_eta = 0
            else:
                self.progress_eta = None

    def say(self, text: str) -> None:
        cleaned = re.sub(r"sk-[A-Za-z0-9_\-]{6,}", "", str(text or ""))
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > 240:
            cleaned = cleaned[:240] + "…"
        if not cleaned:
            return
        with self.lock:
            self.lines.append(cleaned)


class App:
    def __init__(self, directory: Path, model_fn=run_model, infra_fn=scan_target, probe_fn=probe_model, env=None) -> None:
        self.directory = Path(directory)
        self.model_fn = model_fn
        self.infra_fn = infra_fn
        self.probe_fn = probe_fn
        self.env = env
        self.job = Job()
        self.history_lock = threading.Lock()

    def start(self, payload: dict) -> None:
        answers = answers_from_form(payload)
        with self.job.lock:
            if self.job.running:
                raise RuntimeError("正在检测，请等这一次结束。")
            self.job.running = True
            self.job.done = False
            self.job.cancelled = False
            self.job.lines = []
            self.job.error = ""
            self.job.report = ""
            self.job.verdict = ""
            self.job.service = answers.service
            self.job.run_id = ""
            self.job.progress_done = 0
            self.job.progress_total = 0
            self.job.progress_phase = ""
            self.job.progress_detail = ""
            self.job.progress_started = 0.0
            self.job.progress_mark = 0
            self.job.progress_eta = None
            self.job.board_phase = ""
            self.job.rows = []
            self.job.revs = {}
        threading.Thread(target=self._run, args=(answers,), daemon=True).start()

    def cancel(self) -> None:
        with self.job.lock:
            self.job.cancelled = True

    def _publish(self, facts) -> None:
        path = self.directory / "aig-compliance-report.html"
        if path.exists():
            print(f"将覆盖 {path}", flush=True)
        when = stamp()
        path = write_report(facts, self.directory, when)
        verdict = verdict_of(facts)
        report = path.read_text(encoding="utf-8")
        payload = view_of(facts, when)
        with self.history_lock:
            row = save_run(self.directory, facts.service, verdict, when, payload, facts.cases)
        print(f"任务名称：{facts.service}", flush=True)
        print(f"总评：{verdict}", flush=True)
        print(f"报告路径：{path.resolve()}", flush=True)
        print("报告已生成", flush=True)
        self.job.say("报告已生成")
        with self.job.lock:
            self.job.report = report
            self.job.run_id = row["id"]
            self.job.verdict = verdict
            self.job.service = facts.service
            self.job.done = True

    def _run(self, answers) -> None:
        def guarded(item):
            return _call_model(self.model_fn, item, lambda: self.job.cancelled, self.job.say, self.job.progress, self.job.set_board)

        try:
            facts = execute(
                answers,
                model_fn=guarded,
                infra_fn=self.infra_fn,
                say=self.job.say,
                progress=self.job.progress,
                board=self.job.set_board,
            )
        except Exception as exc:
            message = "检测失败：" + public_failure(exc)
            self.job.say(message)
            with self.job.lock:
                self.job.error = message
            facts = Facts(
                service=answers.service,
                specific=bool(getattr(answers, "specific", False)),
                interrupted=self.job.cancelled,
                model_error="检测失败",
            )
            facts.commands.append("检测失败。")
        try:
            self._publish(facts)
        except Exception as exc:
            message = "检测失败：" + public_failure(exc)
            self.job.say(message)
            with self.job.lock:
                self.job.error = message
                self.job.done = True
        finally:
            with self.job.lock:
                self.job.running = False

    def handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def _send(self, status: int, content_type: str, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, payload: dict) -> None:
                self._send(status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8"))

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/":
                    self._send(200, "text/html; charset=utf-8", page_bytes(prefill_from_env(app.env)))
                    return
                if path == "/api/status":
                    self._json(200, app.job.snapshot())
                    return
                if path == "/api/datasets":
                    self._json(200, {"items": list_datasets()})
                    return
                if path == "/api/history":
                    with app.history_lock:
                        rows = list_runs(app.directory)
                    self._json(200, {"items": rows})
                    return
                if path.startswith("/api/runs/"):
                    tail = path.removeprefix("/api/runs/")
                    downloads = (
                        ("/cases.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "aig-compliance-cases.xlsx", workbook),
                        ("/cases.csv", "text/csv; charset=utf-8", "aig-compliance-cases.csv", csv_bytes),
                        ("/cases.jsonl", "application/jsonl; charset=utf-8", "aig-compliance-cases.jsonl", jsonl_bytes),
                    )
                    for suffix, content_type, filename, builder in downloads:
                        if tail.endswith(suffix):
                            item_id = tail[: -len(suffix)]
                            with app.history_lock:
                                rows = case_rows(app.directory, item_id)
                            if rows is None:
                                self._send(404, "text/plain; charset=utf-8", "没有这份记录".encode("utf-8"))
                                return
                            body = builder(rows)
                            self.send_response(200)
                            self.send_header("Content-Type", content_type)
                            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                            self.send_header("Content-Length", str(len(body)))
                            self.send_header("Cache-Control", "no-store")
                            self.end_headers()
                            self.wfile.write(body)
                            return
                    if tail.endswith("/cases"):
                        item_id = tail[: -len("/cases")]
                        query = parse_qs(urlparse(self.path).query)
                        result = (query.get("result") or [""])[0]
                        dataset = (query.get("set") or [""])[0]
                        turns = (query.get("turns") or [""])[0]
                        check = (query.get("check") or [""])[0]
                        try:
                            offset = int((query.get("offset") or ["0"])[0])
                            limit = int((query.get("limit") or ["40"])[0])
                        except ValueError:
                            self._json(400, {"error": "请求格式不正确"})
                            return
                        with app.history_lock:
                            page = case_page(
                                app.directory,
                                item_id,
                                result,
                                offset,
                                limit,
                                dataset=dataset,
                                turns=turns,
                                check=check,
                            )
                        if page is None:
                            self._send(404, "text/plain; charset=utf-8", "没有这份记录".encode("utf-8"))
                            return
                        self._json(200, page)
                        return
                    item_id = tail
                    with app.history_lock:
                        payload = read_run(app.directory, item_id)
                    if payload is None:
                        self._send(404, "text/plain; charset=utf-8", "没有这份记录".encode("utf-8"))
                        return
                    self._json(200, payload)
                    return
                if path == "/report":
                    with app.job.lock:
                        report = app.job.report
                    if not report:
                        self._send(404, "text/plain; charset=utf-8", "报告还没有生成".encode("utf-8"))
                        return
                    self._send(200, "text/html; charset=utf-8", report.encode("utf-8"))
                    return
                self._send(404, "text/plain; charset=utf-8", "没有这个页面".encode("utf-8"))

            def _body(self) -> dict | None:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > 32000:
                    self._json(400, {"error": "请求格式不正确"})
                    return None
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._json(400, {"error": "请求格式不正确"})
                    return None
                if not isinstance(payload, dict):
                    self._json(400, {"error": "请求格式不正确"})
                    return None
                return payload

            def do_POST(self):
                path = urlparse(self.path).path
                if path == "/api/cancel":
                    app.cancel()
                    self._json(200, {"ok": True})
                    return
                if path not in {"/api/run", "/api/probe"}:
                    self._send(404, "text/plain; charset=utf-8", "没有这个页面".encode("utf-8"))
                    return
                payload = self._body()
                if payload is None:
                    return
                if path == "/api/probe":
                    secret = str(payload.get("api_key") or "")
                    try:
                        result = app.probe_fn(str(payload.get("model") or ""), str(payload.get("base_url") or ""), secret)
                    except ValueError as exc:
                        self._json(400, {"ok": False, "error": public_failure(exc, secret), "request": "", "response": ""})
                        return
                    except ProbeFailure as exc:
                        self._json(200, {
                            "ok": False,
                            "error": public_failure(exc, secret),
                            "request": redact_secret(exc.request, secret),
                            "response": redact_secret(exc.response, secret),
                        })
                        return
                    except Exception as exc:
                        self._json(200, {"ok": False, "error": public_failure(exc, secret), "request": "", "response": ""})
                        return
                    packet = result if isinstance(result, dict) else {}
                    self._json(200, {
                        "ok": True,
                        "request": redact_secret(str(packet.get("request") or ""), secret),
                        "response": redact_secret(str(packet.get("response") or ""), secret),
                    })
                    return
                try:
                    app.start(payload)
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                except RuntimeError as exc:
                    self._json(409, {"error": str(exc)})
                    return
                self._json(200, {"ok": True})

        return Handler


def serve(directory: Path, model_fn=run_model, infra_fn=scan_target, opener=webbrowser.open, env=None) -> None:
    app = App(directory, model_fn=model_fn, infra_fn=infra_fn, env=env)
    server = None
    for port in PORTS:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), app.handler())
            break
        except OSError:
            server = None
    if server is None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler())
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}"
    print(f"页面已打开：{url}", flush=True)
    try:
        opener(url)
    except OSError:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        app.cancel()
        print("\n已停止", flush=True)
    finally:
        server.server_close()
