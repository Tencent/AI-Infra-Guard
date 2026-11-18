"""A reply that only repeats closing tags after a finished call must be cut.

After a finished tool call some models keep writing
``</invoke></function></result></tool_call>`` until the server cuts the stream.
Such a reply is hundreds of thousands of characters, takes minutes to receive and
is kept in the conversation history. ``LLM.chat_stream`` stops reading once the
tail of the reply is nothing but closing tags and drops the run, keeping the call
the model actually wrote.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_scan.utils.llm import LLM
from mcp_scan.utils.parse import parse_tool_invocations
from mcp_scan.utils.tool_format_fix import has_runaway_tail, strip_runaway_tail

SH = "<function=execute_shell>\n<parameter=command>ls</parameter>\n</function>"
FIN = "<function=finish>\n<parameter=content>done</parameter>\n</function>"
JUNK = (
    "</invoke>\n</parameter>\n</function>\n</invoke>\n</result>\n"
    "</function>\n</invoke>\n</tool_call>\n</result>\n"
)


@pytest.mark.parametrize(
    ("raw", "tool", "args"),
    [
        # junk right after the real call
        ("Checking. " + SH + "\n" + JUNK * 30, "execute_shell", {"command": "ls"}),
        ("Checking. " + SH + JUNK * 30, "execute_shell", {"command": "ls"}),
        # the real call is not closed: the first </function> inside the run is kept
        (
            "<function=read_file>\n<parameter=file_path>/a</parameter>\n" + JUNK * 30,
            "read_file",
            {"file_path": "/a"},
        ),
        # the received text may stop anywhere inside a tag
        (SH + "\n" + JUNK * 30 + "</res", "execute_shell", {"command": "ls"}),
        (SH + "\n" + JUNK * 30 + "<", "execute_shell", {"command": "ls"}),
        (SH + "\n" + JUNK * 30 + "</", "execute_shell", {"command": "ls"}),
        (SH + "\n" + JUNK * 30 + "</result ", "execute_shell", {"command": "ls"}),
        (
            "<function=finish>\n<parameter=content>"
            + "report." * 300
            + "</parameter>\n</function>\n"
            + JUNK * 30,
            "finish",
            {"content": "report." * 300},
        ),
    ],
)
def test_runaway_closing_tags_are_cut_and_the_call_survives(raw, tool, args):
    assert has_runaway_tail(raw)

    cut = strip_runaway_tail(raw)

    assert len(cut) < len(raw) - 2000
    assert cut.rstrip().endswith("</function>")
    call = parse_tool_invocations(cut)
    assert call is not None and call["toolName"] == tool, cut
    for key, value in args.items():
        assert call["args"].get(key) == value, cut


@pytest.mark.parametrize("pad", range(14))
def test_runaway_tail_is_found_wherever_the_window_starts(pad):
    raw = "x" * pad + SH + "\n" + JUNK * 30 + "</res"

    assert has_runaway_tail(raw)
    assert parse_tool_invocations(strip_runaway_tail(raw))["toolName"] == "execute_shell"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        SH + JUNK,  # too short to tell
        SH + "\n" + "Some prose. " * 700 + JUNK * 3,  # a few closing tags after prose
        "<tr><td>cell</td></tr>\n" * 200,  # closing tags mixed with text
        "<div>" + "<p>paragraph</p>\n" * 300 + "</div>",
        " \n" * 2000,  # whitespace only
        FIN + "\n" + "</function>\n" * 5,
    ],
)
def test_ordinary_text_is_not_a_runaway_tail(raw):
    assert not has_runaway_tail(raw)
    assert strip_runaway_tail(raw) == raw


class _Stream:
    """One finished call, then closing tags without end."""

    def __init__(self, junk_chunks=20000):
        self.sent = 0
        self.closed = False
        self._junk_chunks = junk_chunks

    @staticmethod
    def _chunk(text):
        return SimpleNamespace(
            usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
        )

    def __iter__(self):
        yield self._chunk("Checking. " + SH + "\n")
        for _ in range(self._junk_chunks):
            self.sent += 1
            yield self._chunk(JUNK)

    def close(self):
        self.closed = True


def _llm(stream):
    llm = object.__new__(LLM)
    llm.model = "test-model"
    llm.stream_timeout = 300
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=Mock(return_value=stream)))
    )
    return llm


def test_chat_stream_stops_reading_a_runaway_reply():
    stream = _Stream()

    reply, _usage = _llm(stream).chat_stream([{"role": "user", "content": "test"}])

    assert stream.closed
    assert stream.sent < 200  # stopped soon after the run began, not after 20000 chunks
    assert reply.endswith("</function>")
    assert parse_tool_invocations(reply)["toolName"] == "execute_shell"


def test_chat_stream_keeps_a_normal_reply_whole():
    class Normal(_Stream):
        def __iter__(self):
            yield self._chunk("Checking. ")
            yield self._chunk(SH)

    stream = Normal()

    reply, _usage = _llm(stream).chat_stream([{"role": "user", "content": "test"}])

    assert reply == "Checking. " + SH
    assert not stream.closed
