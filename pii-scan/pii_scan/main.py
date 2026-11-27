"""Command line interface and exit-code contract."""
import argparse
import json
import sys

from .recognizers import DEFAULT_TYPES
from .report.sarif_formatter import to_sarif
from .scanner import scan_path, scan_text


def build_parser():
    p = argparse.ArgumentParser(prog="aig-pii-scan", description="Deterministic PII scanner.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--path", help="file or directory to scan")
    g.add_argument("--text", help="literal text to scan")
    p.add_argument("--locale", default="cn,en", help="reserved for localized messages; does not change recognizers")
    p.add_argument("--format", choices=["json", "sarif"], default="json")
    p.add_argument("-o", "--output", help="write output to this file instead of stdout")
    p.add_argument("--min-confidence", choices=["low", "medium", "high"], default="medium")
    p.add_argument("--disable", default="", help="comma-separated recognizer types to disable")
    p.add_argument("--no-mask", action="store_true", help="emit raw values (not recommended)")
    return p


def _emit(doc, output):
    text = json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if output:
        try:
            with open(output, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        except OSError:
            sys.stderr.write("cannot write output: {}\n".format(output))
            return False
        return True
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)
    return True


def run(argv=None):
    args = build_parser().parse_args(argv)

    disabled = {d.strip() for d in args.disable.split(",") if d.strip()}
    unknown = disabled - set(DEFAULT_TYPES)
    if unknown:
        sys.stderr.write("unknown recognizer: {}\n".format(",".join(sorted(unknown))))
        return 2
    enabled = [t for t in DEFAULT_TYPES if t not in disabled]
    if not enabled:
        sys.stderr.write("no recognizers enabled (check --disable)\n")
        return 2
    active = sorted(enabled)
    mask = not args.no_mask

    if args.path:
        try:
            findings, summary = scan_path(
                args.path,
                min_confidence=args.min_confidence,
                enabled=enabled,
                mask=mask,
                exclude=args.output,
            )
        except FileNotFoundError:
            sys.stderr.write("path not found: {}\n".format(args.path))
            return 2
        if args.format == "sarif":
            doc = to_sarif(findings, summary=summary, active_recognizers=active)
        else:
            doc = {
                "findings": [f.to_dict() for f in findings],
                "summary": summary,
                "active_recognizers": active,
            }
        if not _emit(doc, args.output):
            return 2
        if summary["scanned_ok"] == 0:
            return 3
        return 1 if findings else 0

    summary = {"files_total": 1, "scanned_ok": 1, "filtered": 0, "failed": 0}
    findings = scan_text(
        args.text, source="<text>", min_confidence=args.min_confidence, enabled=enabled, mask=mask
    )
    if args.format == "sarif":
        doc = to_sarif(findings, summary=summary, active_recognizers=active)
    else:
        doc = {
            "findings": [f.to_dict() for f in findings],
            "summary": summary,
            "active_recognizers": active,
        }
    if not _emit(doc, args.output):
        return 2
    return 1 if findings else 0


def cli():
    sys.exit(run())
