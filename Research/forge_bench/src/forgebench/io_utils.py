from __future__ import print_function

import datetime
import hashlib
import json
import os
import platform
import sys


def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def write_text(path, text):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def append_jsonl(path, payload):
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def environment_snapshot():
    return {
        "created_at": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": os.getcwd(),
    }


def hash_manifest(root):
    entries = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        files.sort()
        for name in files:
            if name == "checksums.json":
                continue
            path = os.path.join(base, name)
            entries.append({
                "path": os.path.relpath(path, root),
                "sha256": sha256_file(path),
                "bytes": os.path.getsize(path),
            })
    return entries
