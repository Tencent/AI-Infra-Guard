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


def strip_surrogates(obj):
    """Recursively replace lone surrogate characters (``\\udc00``-``\\udfff``) in strings.

    Python's ``os.walk()``/``os.listdir()`` decode file and directory names that
    contain non-UTF-8 bytes using the ``surrogateescape`` error handler, which
    produces lone surrogates in the resulting ``str``. Those strings cannot be
    encoded back to UTF-8, so serializing them (``model_dump_json()``,
    ``json.dumps``, the LLM request body, ...) raises ``UnicodeEncodeError`` and
    aborts the whole scan. Replacing the surrogates with ``?`` keeps the scan
    running even when a scanned project contains badly-encoded filenames.
    """
    if isinstance(obj, str):
        return obj.encode("utf-8", "replace").decode("utf-8")
    if isinstance(obj, dict):
        return {k: strip_surrogates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_surrogates(i) for i in obj]
    return obj

