#!/usr/bin/env python3
"""
Batch add Apache 2.0 license header to .go and .py source files.
Skips files that already contain the license header.
"""

import os
import sys

GO_HEADER = """\
// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

"""

PY_HEADER = """\
# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""

SKIP_MARKER = "Copyright (c) 2024-2026 Tencent Zhuque Lab"

SKIP_DIRS = {".git", "vendor", "node_modules", "__pycache__", ".mypy_cache"}

def should_skip_dir(path):
    parts = path.replace("\\", "/").split("/")
    return any(p in SKIP_DIRS for p in parts)

def process_file(filepath, header, dry_run=False):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if SKIP_MARKER in content:
        return "skip"

    # For .py files: preserve shebang line if present
    if filepath.endswith(".py") and content.startswith("#!"):
        shebang_end = content.find("\n") + 1
        new_content = content[:shebang_end] + header + content[shebang_end:]
    else:
        new_content = header + content

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
    return "added"

def main():
    dry_run = "--dry-run" in sys.argv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    added = []
    skipped = []
    errors = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel_dir = os.path.relpath(dirpath, root)

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root)

            if filename.endswith(".go"):
                header = GO_HEADER
            elif filename.endswith(".py"):
                header = PY_HEADER
            else:
                continue

            try:
                result = process_file(filepath, header, dry_run=dry_run)
                if result == "added":
                    added.append(rel_path)
                    print(f"  [added]  {rel_path}")
                else:
                    skipped.append(rel_path)
            except Exception as e:
                errors.append((rel_path, str(e)))
                print(f"  [error]  {rel_path}: {e}", file=sys.stderr)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  Added  : {len(added)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Errors : {len(errors)}")

if __name__ == "__main__":
    main()
