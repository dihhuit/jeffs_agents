"""MDU-51: OpenCode v2 ``content``-part text/tool extraction.

Every fixture is a throwaway SQLite database built here under ``tmp_path``.
The developer's real session store is never opened.

v2 ``session_message.data`` rows carry a typed ``content`` array
(``text`` / ``reasoning`` / ``tool``).  These tests pin:

* text parts become the message text, reasoning parts never do (D-1),
* each finalized tool part becomes a synthetic ``role="tool"`` event (D-2/D-3),
* synthetic events cannot inflate metrics or cycle evidence (D-4),
* ``permission_thrash`` is not extractable on v2 and says so (D-5),
* ``info["v2_extraction"]`` plus the two opaqueness notes (D-6), and
* graceful degradation for rows missing ``content``/``tokens`` (D-7).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skills"
    / "session-introspect"
    / "scripts"
    / "session_signals.py"
)
SKILL_PATH = (
    REPO_ROOT / "skills" / "session-introspect" / "SKILL.md"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "session_signals_mdu51", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_signals = _load_module()

# 2026-10-21T09:24:00Z in epoch ms; the cwd used by every non-CLI fixture.
V2_NEWEST_MS = 1_792_574_640_000
V2_NEWEST_ISO = "2026-10-21T09:24:00Z"
CWD = "/repo"

NOTE_P = (
    "v2 permission extraction: none (permission table is project-scoped, not "
    "session-scoped); permission_thrash reads zero — treat as UNKNOWN"
)

SCHEMA = """
CREATE TABLE session (
    id TEXT PRIMARY KEY,
    directory TEXT,
    parent_id TEXT,
    agent TEXT,
    time_updated
);
CREATE TABLE message (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    data TEXT
);
CREATE TABLE part (
    id TEXT PRIMARY KEY,
    message_id TEXT,
    data TEXT
);
CREATE TABLE session_v2 (
    id TEXT PRIMARY KEY,
    directory TEXT,
    parent_id TEXT,
    agent TEXT,
    time_updated
);
CREATE TABLE session_message (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    type TEXT,
    data TEXT,
    time_created INTEGER
);
"""


def _new_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "opencode.db"
    _new_db(db).close()
    return db


def _add_session(
    conn: sqlite3.Connection,
    table: str,
    sid: str,
    directory: str,
    time_updated,
    *,
    agent: str = "just-code",
    parent_id: str | None = None,
) -> None:
    conn.execute(
        f"INSERT INTO {table} (id, directory, parent_id, agent, time_updated) "
        "VALUES (?, ?, ?, ?, ?)",
        (sid, directory, parent_id, agent, time_updated),
    )


def _add_v1_message(
    conn: sqlite3.Connection,
    mid: str,
    sid: str,
    *,
    agent: str = "just-code",
    parts: list[dict] | None = None,
    tokens_in: int = 0,
    created_ms: int = V2_NEWEST_MS,
) -> None:
    data = {
        "agent": agent,
        "role": "assistant",
        "tokens": {"input": tokens_in, "output": 0},
        "time": {"created": created_ms},
    }
    conn.execute(
        "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
        (mid, sid, json.dumps(data)),
    )
    for idx, part in enumerate(parts or []):
        conn.execute(
            "INSERT INTO part (id, message_id, data) VALUES (?, ?, ?)",
            (f"{mid}-p{idx}", mid, json.dumps(part)),
        )


def _add_v2_message(
    conn: sqlite3.Connection,
    mid: str,
    sid: str,
    *,
    agent: str | None = None,
    content: list | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    include_tokens: bool = True,
    time_created: int = V2_NEWEST_MS,
    raw_data: str | None = None,
) -> None:
    """Insert one v2 assistant row; ``content`` is the typed parts array."""
    if raw_data is not None:
        payload = raw_data
    else:
        data: dict = {"time": {"created": time_created}}
        if agent is not None:
            data["agent"] = agent
        if include_tokens:
            data["tokens"] = {"input": tokens_in, "output": tokens_out}
        if content is not None:
            data["content"] = content
        payload = json.dumps(data)
    conn.execute(
        "INSERT INTO session_message (id, session_id, type, data, time_created) "
        "VALUES (?, ?, 'assistant', ?, ?)",
        (mid, sid, payload, time_created),
    )


def _text(text: str) -> dict:
    return {"type": "text", "text": text}


def _reasoning(text: str) -> dict:
    return {
        "type": "reasoning",
        "text": text,
        "state": {"reasoningField": "cot"},
        "time": {"created": V2_NEWEST_MS},
    }


def _tool(
    name: str,
    *,
    status: str = "completed",
    tool_input: dict | None = None,
    part_id: str = "",
) -> dict:
    return {
        "type": "tool",
        "id": part_id or f"{name}-id",
        "name": name,
        "executed": True,
        "state": {
            "status": status,
            "input": tool_input or {},
            "metadata": {"truncated": False},
        },
        "time": {"created": V2_NEWEST_MS},
    }


def _seed_v2(tmp_path: Path, *messages: dict) -> Path:
    """One v2-only tree rooted at CWD; keyword args become message rows."""
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session_v2", "v2-root", CWD, V2_NEWEST_ISO)
    for idx, kwargs in enumerate(messages, start=1):
        _add_v2_message(conn, f"v2-m{idx}", "v2-root", **kwargs)
    conn.commit()
    conn.close()
    return db


def _collect(db: Path):
    return session_signals._collect_opencode(CWD, None, db_path=db)


def _message_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("role") != "tool"]


def _tool_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("role") == "tool"]


# ---------------------------------------------------------------------------
# AC-1 / D-1: text parts only, reasoning excluded
# ---------------------------------------------------------------------------


def test_reasoning_parts_never_reach_event_text(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "code-reviewer",
            "content": [
                _text("QA GRADE: PASS — COT-FREE approval text"),
                _reasoning(
                    "COT-MARKER I should reject this; request changes to the coder."
                ),
            ],
            "tokens_in": 500,
        },
    )

    events, info, _notes = _collect(db)

    assert len(_message_events(events)) == 1
    message_evt = _message_events(events)[0]
    assert message_evt["text"] == "QA GRADE: PASS — COT-FREE approval text"
    assert "COT-MARKER" not in message_evt["text"]
    assert not any("COT-MARKER" in str(e.get("text") or "") for e in events)
    # The reasoning text would be a rejection if it leaked into the event.
    assert not session_signals._is_rejection(message_evt["text"])
    assert not any(
        sig["kind"] == "review_reject_streak"
        for sig in session_signals.collect_signals(events)
    )
    assert info["v2_extraction"]["text_events"] == 1


def test_multiple_text_parts_join_with_a_single_space(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {"agent": "just-code", "content": [_text("first"), _text("second")]},
    )

    events, _info, _notes = _collect(db)

    assert _message_events(events)[0]["text"] == "first second"


# ---------------------------------------------------------------------------
# AC-2: review rejections are visible again on v2 text parts
# ---------------------------------------------------------------------------


def test_two_rejections_then_approval_fire_the_streak(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "code-reviewer",
            "content": [_text("REQUEST CHANGES: tests missing")],
            "time_created": V2_NEWEST_MS,
        },
        {
            "agent": "code-reviewer",
            "content": [_text("REQUEST CHANGES: docs missing")],
            "time_created": V2_NEWEST_MS + 1_000,
        },
        {
            "agent": "code-reviewer",
            "content": [_text("Approved, LGTM")],
            "time_created": V2_NEWEST_MS + 2_000,
        },
    )

    events, _info, _notes = _collect(db)
    signals = session_signals.collect_signals(events)

    streak = next(s for s in signals if s["kind"] == "review_reject_streak")
    assert "2 consecutive rejections from code-reviewer" in streak["evidence"]


def test_single_rejection_counts_in_metrics(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {"agent": "code-reviewer", "content": [_text("REQUEST CHANGES: rename it")]},
    )

    events, _info, _notes = _collect(db)

    assert session_signals._compute_metrics(events)["review_rejections"] == 1


# ---------------------------------------------------------------------------
# AC-3: standalone QA verdict lines on v2 text parts
# ---------------------------------------------------------------------------


def test_two_standalone_qa_fail_verdicts_fire_the_signal(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "qa",
            "content": [_text("findings: selector drift\nQA GRADE: FAIL")],
            "time_created": V2_NEWEST_MS,
        },
        {
            "agent": "qa",
            "content": [_text("findings: still broken\nQA GRADE: FAIL")],
            "time_created": V2_NEWEST_MS + 1_000,
        },
    )

    events, _info, _notes = _collect(db)
    sig = next(
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "qa_fail_repeat"
    )

    assert "reported FAIL 2 times" in sig["evidence"]


def test_quoted_qa_verdict_instruction_does_not_fire(tmp_path: Path) -> None:
    instruction = "End with exactly: QA GRADE: PASS or QA GRADE: FAIL"
    db = _seed_v2(
        tmp_path,
        {
            "agent": "qa",
            "content": [_text(instruction)],
            "time_created": V2_NEWEST_MS,
        },
        {
            "agent": "qa",
            "content": [_text(instruction)],
            "time_created": V2_NEWEST_MS + 1_000,
        },
    )

    events, _info, _notes = _collect(db)

    assert not any(
        s["kind"] == "qa_fail_repeat"
        for s in session_signals.collect_signals(events)
    )


# ---------------------------------------------------------------------------
# AC-4 / D-2: one message event plus one synthetic event per tool part
# ---------------------------------------------------------------------------


def test_message_and_tool_events_have_the_prescribed_shape(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [
                _text("read then edit"),
                _tool("read", tool_input={"path": "src/a.py"}, part_id="t1"),
                _tool("edit", status="error", tool_input={"path": "src/a.py"}),
            ],
            "tokens_in": 700,
            "tokens_out": 70,
        },
    )

    events, _info, _notes = _collect(db)

    assert len(_message_events(events)) == 1
    assert len(_tool_events(events)) == 2
    message_evt = _message_events(events)[0]
    assert message_evt["role"] == "assistant"
    assert message_evt["text"] == "read then edit"
    assert message_evt["tokens_in"] == 700
    assert message_evt["tokens_out"] == 70
    assert message_evt["tool"] is None
    assert message_evt["tool_path"] is None
    assert message_evt["tool_error"] is False

    read_evt, edit_evt = _tool_events(events)
    assert read_evt["tool"] == "read"
    assert read_evt["tool_path"] == "src/a.py"
    assert read_evt["tool_error"] is False
    assert edit_evt["tool"] == "edit"
    assert edit_evt["tool_path"] == "src/a.py"
    assert edit_evt["tool_error"] is True
    for evt in (read_evt, edit_evt):
        assert evt["agent"] == "just-code"
        assert evt["t"] == message_evt["t"]
        assert evt["tokens_in"] == 0
        assert evt["tokens_out"] == 0
        assert evt["cache_read"] == 0
        assert evt["model"] == ""
        assert evt["text"] == ""
        assert evt["permission_requested"] is False


def test_message_event_is_emitted_before_its_tool_events(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "content": [
                _text("batch"),
                _tool("read", tool_input={"path": "a.py"}),
                _tool("read", tool_input={"path": "b.py"}),
            ],
        },
    )

    events, _info, _notes = _collect(db)

    assert [e["role"] for e in events] == ["assistant", "tool", "tool"]
    assert [e["tool_path"] for e in events[1:]] == ["a.py", "b.py"]


# ---------------------------------------------------------------------------
# AC-5: repeated_tool_error counts per call, status is authoritative
# ---------------------------------------------------------------------------


def test_three_errored_edits_fire_repeated_tool_error(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        *[
            {
                "agent": "just-code",
                "content": [
                    _tool(
                        "edit",
                        status="error",
                        tool_input={"path": f"f{i}.py"},
                    )
                ],
                "time_created": V2_NEWEST_MS + i * 1_000,
            }
            for i in range(3)
        ],
    )

    events, _info, _notes = _collect(db)
    sig = next(
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "repeated_tool_error"
    )

    assert "3 errors on tool edit" in sig["evidence"]


def test_completed_and_failed_statuses_map_to_tool_error(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [
                _tool("edit", status="completed", tool_input={"path": "a.py"}),
                _tool("edit", status="failed", tool_input={"path": "b.py"}),
            ],
        },
    )

    events, _info, _notes = _collect(db)

    assert [e["tool_error"] for e in _tool_events(events)] == [False, True]


def test_three_completed_edits_do_not_fire_repeated_tool_error(
    tmp_path: Path,
) -> None:
    db = _seed_v2(
        tmp_path,
        *[
            {
                "agent": "just-code",
                "content": [
                    _tool("edit", status="completed", tool_input={"path": "a.py"})
                ],
                "time_created": V2_NEWEST_MS + i * 1_000,
            }
            for i in range(3)
        ],
    )

    events, _info, _notes = _collect(db)

    assert not any(e["tool_error"] for e in _tool_events(events))
    assert not any(
        s["kind"] == "repeated_tool_error"
        for s in session_signals.collect_signals(events)
    )


# ---------------------------------------------------------------------------
# AC-6: context_reread targets, pattern-first for grep
# ---------------------------------------------------------------------------


def test_four_reads_of_one_path_fire_context_reread(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [
                _tool("read", tool_input={"path": "src/a.py"}),
                _tool("read", tool_input={"path": "src/a.py"}),
            ],
            "time_created": V2_NEWEST_MS,
        },
        {
            "agent": "just-code",
            "content": [
                _tool("read", tool_input={"path": "src/a.py"}),
                _tool("read", tool_input={"path": "src/a.py"}),
            ],
            "time_created": V2_NEWEST_MS + 1_000,
        },
    )

    events, _info, _notes = _collect(db)
    sig = next(
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "context_reread"
    )

    assert "src/a.py" in sig["evidence"]
    assert "4 times" in sig["evidence"]


def test_grep_target_is_the_pattern_when_no_path_is_given(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [_tool("grep", tool_input={"pattern": "TODO(session)"})],
        },
    )

    events, _info, _notes = _collect(db)

    assert _tool_events(events)[0]["tool_path"] == "TODO(session)"


def test_grep_target_prefers_the_pattern_over_a_scoped_path(
    tmp_path: Path,
) -> None:
    """AC-6: pattern-first even when the grep also carries a ``path`` scope.

    Four distinct patterns over the same searched path must not pool under one
    ``(agent, "grep", path)`` key and false-fire ``context_reread``.
    """
    db = _seed_v2(
        tmp_path,
        *[
            {
                "agent": "just-code",
                "content": [
                    _tool(
                        "grep",
                        tool_input={"pattern": f"pattern{i}", "path": "src/"},
                    )
                ],
                "time_created": V2_NEWEST_MS + i * 1_000,
            }
            for i in range(4)
        ],
    )

    events, _info, _notes = _collect(db)

    assert [e["tool_path"] for e in _tool_events(events)] == [
        f"pattern{i}" for i in range(4)
    ]
    assert not any(
        s["kind"] == "context_reread"
        for s in session_signals.collect_signals(events)
    )


def test_four_distinct_grep_patterns_do_not_fire_context_reread(
    tmp_path: Path,
) -> None:
    db = _seed_v2(
        tmp_path,
        *[
            {
                "agent": "just-code",
                "content": [_tool("grep", tool_input={"pattern": f"pattern{i}"})],
                "time_created": V2_NEWEST_MS + i * 1_000,
            }
            for i in range(4)
        ],
    )

    events, _info, _notes = _collect(db)

    assert [e["tool_path"] for e in _tool_events(events)] == [
        f"pattern{i}" for i in range(4)
    ]
    assert not any(
        s["kind"] == "context_reread"
        for s in session_signals.collect_signals(events)
    )


def test_four_identical_grep_patterns_do_fire(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        *[
            {
                "agent": "just-code",
                "content": [_tool("grep", tool_input={"pattern": "TODO"})],
                "time_created": V2_NEWEST_MS + i * 1_000,
            }
            for i in range(4)
        ],
    )

    events, _info, _notes = _collect(db)

    assert any(
        s["kind"] == "context_reread"
        for s in session_signals.collect_signals(events)
    )


# ---------------------------------------------------------------------------
# AC-7: in-flight and nameless parts produce no events
# ---------------------------------------------------------------------------


def test_streaming_running_and_nameless_parts_yield_no_events(
    tmp_path: Path,
) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [
                _text("in flight"),
                _tool("read", status="streaming", tool_input={"path": "a.py"}),
                _tool("read", status="running", tool_input={"path": "b.py"}),
                {"type": "tool", "state": {"status": "completed", "input": {}}},
                {"type": "tool", "name": "", "state": {"status": "completed"}},
            ],
        },
    )

    events, info, _notes = _collect(db)

    assert len(_message_events(events)) == 1
    assert _tool_events(events) == []
    assert info["v2_extraction"]["tool_events"] == 0


# ---------------------------------------------------------------------------
# AC-8 / D-5: permission extraction is not available on v2
# ---------------------------------------------------------------------------


def test_permission_is_never_requested_and_note_p_is_emitted(
    tmp_path: Path,
) -> None:
    db = _seed_v2(
        tmp_path,
        {"agent": "just-code", "content": [_text("hello")]},
    )

    events, info, notes = _collect(db)

    assert events
    assert not any(e["permission_requested"] for e in events)
    assert info["v2_extraction"]["permission"] is False
    assert NOTE_P in notes
    assert not any(
        s["kind"] == "permission_thrash"
        for s in session_signals.collect_signals(events)
    )


def test_note_p_avoids_the_v1_and_store_selection_substrings(
    tmp_path: Path,
) -> None:
    db = _seed_v2(tmp_path, {"agent": "just-code", "content": [_text("hi")]})

    _events, _info, notes = _collect(db)

    assert not any("v1" in note for note in notes)
    assert not any("store selected" in note for note in notes)


def test_skill_documents_the_v2_permission_unknown() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")

    assert "permission_thrash" in skill
    assert "UNKNOWN" in skill
    assert "permission" in skill.lower()
    # The disclosure sits in the v2 extraction paragraph, not just anywhere.
    v2_paragraphs = [
        block for block in skill.split("\n\n") if "v2" in block and "permission" in block
    ]
    assert any(
        "permission_thrash" in block and "UNKNOWN" in block
        for block in v2_paragraphs
    )


# ---------------------------------------------------------------------------
# AC-9 / D-7: marker counts and graceful degradation
# ---------------------------------------------------------------------------


def test_info_marker_reports_counts_and_capabilities(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [_text("one"), _tool("read", tool_input={"path": "a.py"})],
            "time_created": V2_NEWEST_MS,
        },
        {
            "agent": "just-code",
            "content": [_tool("read", tool_input={"path": "b.py"})],
            "time_created": V2_NEWEST_MS + 1_000,
        },
    )

    _events, info, _notes = _collect(db)

    extraction = info["v2_extraction"]
    assert extraction == {
        "messages": 2,
        "text_events": 1,
        "tool_events": 2,
        "text": True,
        "tools": True,
        "permission": False,
    }


def test_rows_without_content_or_tokens_do_not_crash_and_fire_note_t(
    tmp_path: Path,
) -> None:
    db = _seed_v2(
        tmp_path,
        {"agent": "just-code", "include_tokens": False},
        {"agent": "just-code"},
    )

    events, info, notes = _collect(db)

    assert len(_message_events(events)) == 2
    assert all(e["tokens_in"] == 0 and e["tokens_out"] == 0 for e in events)
    assert info["v2_extraction"]["messages"] == 2
    assert info["v2_extraction"]["text_events"] == 0
    assert any(
        note.startswith(
            "v2 text extraction: none of 2 assistant message(s) carried "
            "extractable text"
        )
        for note in notes
    )
    assert NOTE_P in notes


def test_note_t_does_not_fire_when_text_was_extracted(tmp_path: Path) -> None:
    db = _seed_v2(tmp_path, {"agent": "just-code", "content": [_text("visible")]})

    _events, info, notes = _collect(db)

    assert info["v2_extraction"]["text_events"] == 1
    assert not any("v2 text extraction" in note for note in notes)


def test_odd_content_shapes_are_skipped_without_crashing(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {
            "agent": "just-code",
            "content": [
                "not-a-dict",
                42,
                None,
                {"type": "unknown-type", "text": "ignored"},
                {"type": "text", "text": 123},
                _text("kept"),
            ],
        },
        # content is not a list at all.
        {"agent": "just-code", "content": "not-a-list"},
    )

    events, info, _notes = _collect(db)

    messages = _message_events(events)
    assert [e["text"] for e in messages] == ["kept", ""]
    assert info["v2_extraction"]["messages"] == 2
    assert info["v2_extraction"]["text_events"] == 1


def test_unparseable_data_rows_are_skipped_entirely(tmp_path: Path) -> None:
    db = _seed_v2(
        tmp_path,
        {"agent": "just-code", "raw_data": "{not json"},
        {"agent": "just-code", "raw_data": "[1, 2, 3]"},
        {"agent": "just-code", "content": [_text("real row")]},
    )

    events, info, _notes = _collect(db)

    messages = _message_events(events)
    assert [e["text"] for e in messages] == ["real row"]
    assert info["v2_extraction"]["messages"] == 1


def test_non_dict_tokens_fall_back_to_zeros(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session_v2", "v2-root", CWD, V2_NEWEST_ISO)
    _add_v2_message(
        conn,
        "v2-m1",
        "v2-root",
        raw_data=json.dumps(
            {"agent": "just-code", "tokens": "oops", "content": [_text("still here")]}
        ),
    )
    conn.commit()
    conn.close()

    events, _info, _notes = _collect(db)

    evt = _message_events(events)[0]
    assert evt["text"] == "still here"
    assert evt["tokens_in"] == 0
    assert evt["tokens_out"] == 0


# ---------------------------------------------------------------------------
# AC-11: v1 behaviour is untouched (tool fields stay on the message event)
# ---------------------------------------------------------------------------


def test_v1_tree_keeps_tool_fields_on_its_message_event(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "v1-root", CWD, V2_NEWEST_ISO)
    _add_v1_message(
        conn,
        "v1-m1",
        "v1-root",
        parts=[
            {"type": "text", "text": "v1 text"},
            {
                "type": "tool",
                "name": "read",
                "state": "error",
                "arguments": {"path": "legacy.py"},
            },
        ],
        tokens_in=300,
    )
    conn.commit()
    conn.close()

    events, info, _notes = _collect(db)

    assert info["store"] == "v1"
    assert not any(e["role"] == "tool" for e in events)
    evt = events[0]
    assert evt["text"].strip() == "v1 text"
    assert evt["tool"] == "read"
    assert evt["tool_path"] == "legacy.py"
    assert evt["tool_error"] is True
    assert "v2_extraction" not in info


# ---------------------------------------------------------------------------
# AC-12: no new SQL — the v2 selects stay byte-identical
# ---------------------------------------------------------------------------


def test_v2_collector_sql_is_unchanged() -> None:
    """Extraction is interpretation only: no new SQL, no new table scans."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert source.count("FROM session_v2") == 4
    assert "SELECT session_id, data, time_created FROM session_message" in source
    assert source.count("FROM session_message") == 1
    assert "AND type = 'assistant'" in source
    assert "ORDER BY time_created" in source


# ---------------------------------------------------------------------------
# CLI end to end with an overridden HOME (hermetic)
# ---------------------------------------------------------------------------


def _run_cli(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--harness", "opencode", *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


def test_cli_reports_v2_extraction_and_notes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    db = home / ".local" / "share" / "opencode" / "opencode.db"
    conn = _new_db(db)
    _add_session(conn, "session_v2", "v2-root", str(repo), V2_NEWEST_ISO)
    _add_v2_message(
        conn,
        "v2-m1",
        "v2-root",
        agent="code-reviewer",
        content=[_text("REQUEST CHANGES: tests missing")],
        tokens_in=900,
        time_created=V2_NEWEST_MS,
    )
    _add_v2_message(
        conn,
        "v2-m2",
        "v2-root",
        agent="code-reviewer",
        content=[
            _text("REQUEST CHANGES: docs missing"),
            _tool("read", tool_input={"path": "src/a.py"}),
        ],
        tokens_in=1200,
        time_created=V2_NEWEST_MS + 1_000,
    )
    conn.commit()
    conn.close()

    result = _run_cli(home, "--cwd", str(repo))

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["info"]["store"] == "v2"
    assert data["info"]["v2_extraction"] == {
        "messages": 2,
        "text_events": 2,
        "tool_events": 1,
        "text": True,
        "tools": True,
        "permission": False,
    }
    assert NOTE_P in data["notes"]
    assert any(s["kind"] == "review_reject_streak" for s in data["signals"])
    assert data["metrics"]["review_rejections"] == 2
