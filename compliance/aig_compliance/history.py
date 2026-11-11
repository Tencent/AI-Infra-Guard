"""Keep past runs in a local SQLite database, without API keys."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_NAME = "aig-compliance.db"
MAX_ITEMS = 100
PREVIEW = 2000
_ID = re.compile(r"^[0-9a-z-]{8,48}$")
_CHECK = re.compile(r"^[A-Za-z][A-Za-z0-9.]{0,7}$")


def _path(directory: Path) -> Path:
    return Path(directory) / DB_NAME


@contextmanager
def _connect(directory: Path):
    conn = sqlite3.connect(_path(directory), timeout=10)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                verdict TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                run_id TEXT NOT NULL,
                n INTEGER NOT NULL,
                dataset TEXT NOT NULL,
                result TEXT NOT NULL,
                mark TEXT NOT NULL,
                bypass INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                reply TEXT NOT NULL DEFAULT ''
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cases)")}
        if "reply" not in columns:
            conn.execute("ALTER TABLE cases ADD COLUMN reply TEXT NOT NULL DEFAULT ''")
        if "checks" not in columns:
            conn.execute("ALTER TABLE cases ADD COLUMN checks TEXT NOT NULL DEFAULT '[]'")
        if "turns" not in columns:
            conn.execute("ALTER TABLE cases ADD COLUMN turns INTEGER NOT NULL DEFAULT 1")
        conn.execute("CREATE INDEX IF NOT EXISTS cases_run ON cases (run_id, n)")
        yield conn
        conn.commit()
    finally:
        conn.close()


def list_runs(directory: Path) -> list[dict]:
    if not _path(directory).is_file():
        return []
    with _connect(directory) as conn:
        rows = conn.execute(
            "SELECT id, name, verdict, created_at FROM runs ORDER BY rowid DESC LIMIT ?",
            (MAX_ITEMS,),
        ).fetchall()
    return [{"id": item_id, "name": name, "verdict": verdict, "time": created} for item_id, name, verdict, created in rows]


def _stored_checks(value: object) -> str:
    rows = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("id") or "").strip()[:8]
        if not _CHECK.fullmatch(name):
            continue
        rows.append({"id": name, "hit": bool(item.get("hit")), "exempt": bool(item.get("exempt"))})
        if len(rows) >= 12:
            break
    return json.dumps(rows, ensure_ascii=False)


def _clean_case(item: dict) -> tuple | None:
    if not isinstance(item, dict):
        return None
    result = item.get("result")
    if result not in {"通过", "失败", "未完成"}:
        return None
    allowed = {"拒", "答", "未返回", "未完成"}
    mark = item.get("mark") if item.get("mark") in allowed else ""
    prompt = str(item.get("prompt") or "").replace("\x00", "")
    reply = re.sub(r"sk-[A-Za-z0-9_\-]{6,}", "sk-****", str(item.get("reply") or "").replace("\x00", ""))
    if len(prompt) > 30000:
        prompt = prompt[:30000] + "…"
    if len(reply) > 30000:
        reply = reply[:30000] + "…"
    try:
        number = int(item.get("n") or 0)
    except (TypeError, ValueError):
        number = 0
    try:
        turns = int(item.get("turns") or 1)
    except (TypeError, ValueError):
        turns = 1
    return (
        number,
        str(item.get("set") or "")[:80],
        result,
        mark,
        1 if item.get("bypass") else 0,
        prompt,
        reply,
        _stored_checks(item.get("checks")),
        min(8, max(1, turns)),
    )


def save_run(directory: Path, name: str, verdict: str, when: str, payload: dict, cases: list | None = None) -> dict:
    compact = "".join(ch for ch in when if ch.isdigit()) or "0"
    item_id = f"{compact}-{uuid.uuid4().hex[:6]}"
    stored = dict(payload)
    stored.pop("cases", None)
    blob = json.dumps(stored, ensure_ascii=False)
    rows = []
    for item in cases or []:
        cleaned = _clean_case(item)
        if cleaned is not None:
            rows.append((item_id, *cleaned))
    with _connect(directory) as conn:
        conn.execute(
            "INSERT INTO runs (id, name, verdict, created_at, payload) VALUES (?, ?, ?, ?, ?)",
            (item_id, name, verdict, when, blob),
        )
        if rows:
            conn.executemany(
                "INSERT INTO cases (run_id, n, dataset, result, mark, bypass, prompt, reply, checks, turns) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        conn.execute(
            """
            DELETE FROM runs
            WHERE id NOT IN (SELECT id FROM runs ORDER BY rowid DESC LIMIT ?)
            """,
            (MAX_ITEMS,),
        )
        conn.execute("DELETE FROM cases WHERE run_id NOT IN (SELECT id FROM runs)")
    return {"id": item_id, "name": name, "verdict": verdict, "time": when}


def read_run(directory: Path, item_id: str) -> dict | None:
    if not _ID.fullmatch(item_id or ""):
        return None
    if not _path(directory).is_file():
        return None
    with _connect(directory) as conn:
        row = conn.execute("SELECT payload FROM runs WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _load_checks(raw: object) -> list[dict]:
    try:
        rows = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(rows, list):
        return []
    return [
        {"id": item.get("id"), "hit": bool(item.get("hit")), "exempt": bool(item.get("exempt"))}
        for item in rows
        if isinstance(item, dict) and item.get("id")
    ]


def case_page(
    directory: Path,
    item_id: str,
    result: str = "",
    offset: int = 0,
    limit: int = 40,
    dataset: str = "",
    turns: str = "",
    check: str = "",
) -> dict | None:
    if not _ID.fullmatch(item_id or "") or not _path(directory).is_file():
        return None
    choice = result if result in {"通过", "失败", "未完成"} else ""
    start = max(0, int(offset))
    size = min(80, max(1, int(limit)))
    where = ["run_id = ?"]
    params: list = [item_id]
    if choice:
        where.append("result = ?")
        params.append(choice)
    name = str(dataset or "").strip()[:80]
    if name:
        where.append("dataset = ?")
        params.append(name)
    if turns == "single":
        where.append("turns <= 1")
    elif turns == "multi":
        where.append("turns > 1")
    token = str(check or "").strip()
    if _CHECK.fullmatch(token):
        where.append(
            """
            EXISTS (
                SELECT 1 FROM json_each(cases.checks)
                WHERE json_extract(json_each.value, '$.id') = ?
                  AND json_extract(json_each.value, '$.hit') = 1
                  AND json_extract(json_each.value, '$.exempt') = 0
            )
            """
        )
        params.append(token)
    clause = " AND ".join(where)
    with _connect(directory) as conn:
        found = conn.execute("SELECT 1 FROM runs WHERE id = ?", (item_id,)).fetchone()
        if found is None:
            return None
        passed = conn.execute("SELECT COUNT(*) FROM cases WHERE run_id = ? AND result = '通过'", (item_id,)).fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM cases WHERE run_id = ? AND result = '失败'", (item_id,)).fetchone()[0]
        unfinished = conn.execute("SELECT COUNT(*) FROM cases WHERE run_id = ? AND result = '未完成'", (item_id,)).fetchone()[0]
        matched = conn.execute(f"SELECT COUNT(*) FROM cases WHERE {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT n, dataset, result, mark, bypass, turns, checks,
                   substr(prompt, 1, ?), substr(reply, 1, ?), length(prompt), length(reply)
            FROM cases WHERE {clause} ORDER BY n LIMIT ? OFFSET ?
            """,
            (PREVIEW, PREVIEW, *params, size, start),
        ).fetchall()
    return {
        "pass": passed,
        "fail": failed,
        "unfinished": unfinished,
        "matched": matched,
        "offset": start,
        "limit": size,
        "items": [
            {
                "n": n,
                "set": name,
                "result": label,
                "mark": mark,
                "bypass": bool(flag),
                "turns": turns_n or 1,
                "checks": _load_checks(checks),
                "preview": preview or "",
                "answer": answer or "",
                "prompt_more": int(prompt_len or 0) > PREVIEW,
                "reply_more": int(reply_len or 0) > PREVIEW,
            }
            for n, name, label, mark, flag, turns_n, checks, preview, answer, prompt_len, reply_len in rows
        ],
    }


def case_rows(directory: Path, item_id: str) -> list[tuple] | None:
    if not _ID.fullmatch(item_id or "") or not _path(directory).is_file():
        return None
    with _connect(directory) as conn:
        found = conn.execute("SELECT 1 FROM runs WHERE id = ?", (item_id,)).fetchone()
        if found is None:
            return None
        return conn.execute(
            "SELECT n, dataset, result, mark, bypass, prompt, reply, checks FROM cases WHERE run_id = ? ORDER BY n",
            (item_id,),
        ).fetchall()
