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


def _clean_case(item: dict) -> tuple | None:
    if not isinstance(item, dict):
        return None
    result = item.get("result")
    if result not in {"通过", "失败"}:
        return None
    mark = item.get("mark") if item.get("mark") in {"拒", "答", "未返回"} else ""
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
    return (
        number,
        str(item.get("set") or "")[:80],
        result,
        mark,
        1 if item.get("bypass") else 0,
        prompt,
        reply,
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
                "INSERT INTO cases (run_id, n, dataset, result, mark, bypass, prompt, reply) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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


def case_page(directory: Path, item_id: str, result: str = "", offset: int = 0, limit: int = 40) -> dict | None:
    if not _ID.fullmatch(item_id or "") or not _path(directory).is_file():
        return None
    choice = result if result in {"通过", "失败"} else ""
    start = max(0, int(offset))
    size = min(80, max(1, int(limit)))
    with _connect(directory) as conn:
        found = conn.execute("SELECT 1 FROM runs WHERE id = ?", (item_id,)).fetchone()
        if found is None:
            return None
        passed = conn.execute("SELECT COUNT(*) FROM cases WHERE run_id = ? AND result = '通过'", (item_id,)).fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM cases WHERE run_id = ? AND result = '失败'", (item_id,)).fetchone()[0]
        if choice:
            matched = passed if choice == "通过" else failed
            rows = conn.execute(
                """
                SELECT n, dataset, result, mark, bypass,
                       substr(prompt, 1, ?), substr(reply, 1, ?), length(prompt), length(reply)
                FROM cases WHERE run_id = ? AND result = ? ORDER BY n LIMIT ? OFFSET ?
                """,
                (PREVIEW, PREVIEW, item_id, choice, size, start),
            ).fetchall()
        else:
            matched = passed + failed
            rows = conn.execute(
                """
                SELECT n, dataset, result, mark, bypass,
                       substr(prompt, 1, ?), substr(reply, 1, ?), length(prompt), length(reply)
                FROM cases WHERE run_id = ? ORDER BY n LIMIT ? OFFSET ?
                """,
                (PREVIEW, PREVIEW, item_id, size, start),
            ).fetchall()
    return {
        "pass": passed,
        "fail": failed,
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
                "preview": preview or "",
                "answer": answer or "",
                "prompt_more": int(prompt_len or 0) > PREVIEW,
                "reply_more": int(reply_len or 0) > PREVIEW,
            }
            for n, name, label, mark, flag, preview, answer, prompt_len, reply_len in rows
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
            "SELECT n, dataset, result, mark, bypass, prompt, reply FROM cases WHERE run_id = ? ORDER BY n",
            (item_id,),
        ).fetchall()
