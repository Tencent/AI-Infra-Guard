"""Orchestration: collect recognizer hits, resolve overlaps, build findings."""
import bisect
import os

from .recognizers import get_recognizers
from .report.models import CONFIDENCE_ORDER, Finding
from .utils.text_loader import read_text_file


def _line_starts(text):
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_col(line_starts, offset):
    idx = bisect.bisect_right(line_starts, offset) - 1
    if idx < 0:
        idx = 0
    return idx + 1, offset - line_starts[idx] + 1


def _mask(value, type_):
    if type_ == "email":
        local, _, domain = value.partition("@")
        return "{}***@{}***".format(local[:1], domain[:1])
    n = len(value)
    if n <= 3:
        return "*" * n
    if n <= 6:
        return value[:1] + "*" * (n - 2) + value[-1:]
    return value[:3] + "*" * (n - 6) + value[-3:]


def _resolve(raw_hits):
    """Greedy non-overlapping selection with a total, deterministic order."""
    ordered = sorted(
        raw_hits,
        key=lambda item: (item[0], item[2].start, -(item[2].end - item[2].start), item[1]),
    )
    accepted = []
    occupied = []
    for _, _, h in ordered:
        if any(not (h.end <= s or h.start >= e) for s, e in occupied):
            continue
        occupied.append((h.start, h.end))
        accepted.append(h)
    return accepted


def scan_text(text, source="<text>", min_confidence="medium", enabled=None, mask=True):
    threshold = CONFIDENCE_ORDER.get(min_confidence, 1)
    line_starts = _line_starts(text)
    raw_hits = []
    for type_, priority, fn in get_recognizers(enabled):
        for h in fn(text):
            if "\n" in h.value:
                continue
            # Drop sub-threshold hits BEFORE overlap resolution so a low-confidence
            # hit cannot occupy a span and suppress a high-confidence one.
            if CONFIDENCE_ORDER.get(h.confidence, 0) < threshold:
                continue
            raw_hits.append((priority, type_, h))

    findings = []
    for h in _resolve(raw_hits):
        line, column = _line_col(line_starts, h.start)
        masked = _mask(h.value, h.type) if mask else h.value
        findings.append(
            Finding(
                type=h.type,
                start=h.start,
                end=h.end,
                line=line,
                column=column,
                confidence=h.confidence,
                masked_sample=masked,
                source=source,
                raw=None if mask else h.value,
            )
        )
    findings.sort(key=lambda f: (f.source, f.start, f.end, f.type))
    return findings


def scan_path(path, min_confidence="medium", enabled=None, mask=True, exclude=None):
    if os.path.isfile(path):
        files = [path]
        base = os.path.dirname(path) or "."
    elif os.path.isdir(path):
        base = path
        files = []
        for root, dirs, names in os.walk(path):
            dirs.sort()
            for name in sorted(names):
                files.append(os.path.join(root, name))
    else:
        raise FileNotFoundError(path)

    exclude_abs = os.path.abspath(exclude) if exclude else None
    summary = {"files_total": 0, "scanned_ok": 0, "filtered": 0, "failed": 0}
    findings = []
    for fp in files:
        if exclude_abs is not None and os.path.abspath(fp) == exclude_abs:
            continue  # don't scan our own output file (keeps runs deterministic)
        summary["files_total"] += 1
        text, status = read_text_file(fp)
        if status == "filtered":
            summary["filtered"] += 1
            continue
        if status == "failed":
            summary["failed"] += 1
            continue
        summary["scanned_ok"] += 1
        rel = os.path.relpath(fp, base).replace(os.sep, "/")
        findings.extend(
            scan_text(text, source=rel, min_confidence=min_confidence, enabled=enabled, mask=mask)
        )
    findings.sort(key=lambda f: (f.source, f.start, f.end, f.type))
    return findings, summary
