"""MDU-50: OpenCode store freshness selection and wrong-directory recovery.

Every fixture is a throwaway SQLite database built here under ``tmp_path``.
The developer's real session store is never opened.
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


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "session_signals_mdu50", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_signals = _load_module()

# 2026-10-21T09:24:00Z and 2026-10-14T17:13:00Z in epoch seconds/ms.
V2_NEWEST_ISO = "2026-10-21T09:24:00Z"
V1_NEWEST_ISO = "2026-10-14T17:13:00Z"
V2_NEWEST_MS = 1_792_574_640_000
V1_NEWEST_MS = 1_791_997_980_000

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
    text: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    created_ms: int = V1_NEWEST_MS,
) -> None:
    data = {
        "agent": agent,
        "role": "assistant",
        "tokens": {"input": tokens_in, "output": tokens_out},
        "time": {"created": created_ms},
    }
    conn.execute(
        "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
        (mid, sid, json.dumps(data)),
    )
    if text:
        conn.execute(
            "INSERT INTO part (id, message_id, data) VALUES (?, ?, ?)",
            (f"{mid}-part", mid, json.dumps({"type": "text", "text": text})),
        )


def _add_v2_message(
    conn: sqlite3.Connection,
    mid: str,
    sid: str,
    *,
    tokens_in: int = 0,
    tokens_out: int = 0,
    time_created: int = V2_NEWEST_MS,
) -> None:
    data = {"tokens": {"input": tokens_in, "output": tokens_out}}
    conn.execute(
        "INSERT INTO session_message (id, session_id, type, data, time_created) "
        "VALUES (?, ?, 'assistant', ?, ?)",
        (mid, sid, json.dumps(data), time_created),
    )


def _seed_two_store_db(tmp_path: Path) -> Path:
    """v1 tree from Oct 14, v2 tree from Oct 21, both rooted at /repo."""
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "v1-root", "/repo", V1_NEWEST_ISO)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=100, tokens_out=10)
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=3000, tokens_out=400)
    _add_v2_message(
        conn, "v2-m2", "v2-root", tokens_in=2000, tokens_out=100,
        time_created=V2_NEWEST_MS,
    )
    conn.commit()
    conn.close()
    return db


# ---------------------------------------------------------------------------
# D-1: fresh-store selection (defect 1)
# ---------------------------------------------------------------------------


def test_fresher_v2_tree_is_selected_with_its_tokens(tmp_path: Path) -> None:
    db = _seed_two_store_db(tmp_path)

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 5000
    assert info["time_range"]["newest"] == V2_NEWEST_ISO
    assert info["time_range"]["oldest"] == V2_NEWEST_ISO
    candidates = {c["store"]: c for c in info["store_candidates"]}
    assert candidates["v1"]["id"] == "v1-root"
    assert candidates["v2"]["id"] == "v2-root"
    assert candidates["v1"]["newest"] == V1_NEWEST_ISO
    assert candidates["v2"]["newest"] == V2_NEWEST_ISO
    assert any("store selected: v2" in note for note in notes)


def test_clearly_fresher_v1_tree_is_selected_and_its_text_signals_fire(
    tmp_path: Path,
) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(
        conn, "session", "v1-root", "/repo", V2_NEWEST_ISO, agent="code-reviewer"
    )
    _add_v1_message(
        conn,
        "v1-m1",
        "v1-root",
        agent="code-reviewer",
        text="I request changes: tests missing",
        tokens_in=200,
        created_ms=V2_NEWEST_MS,
    )
    _add_v1_message(
        conn,
        "v1-m2",
        "v1-root",
        agent="code-reviewer",
        text="I request changes: docs missing",
        tokens_in=200,
        created_ms=V2_NEWEST_MS,
    )
    _add_session(conn, "session_v2", "v2-root", "/repo", V1_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=9000)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v1"
    assert info["session_id"] == "v1-root"
    assert sum(evt["tokens_in"] for evt in events) == 400
    streak = next(
        sig
        for sig in session_signals.collect_signals(events)
        if sig["kind"] == "review_reject_streak"
    )
    assert "2 consecutive rejections from code-reviewer" in streak["evidence"]
    assert any("store selected: v1" in note for note in notes)


def test_v1_within_eps_of_v2_loses_to_v2(tmp_path: Path) -> None:
    """A near-tie is a dual-write artifact, not a fresher v1 tree."""
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    slightly_newer_v1 = "2026-10-21T09:26:00Z"
    _add_session(conn, "session", "v1-root", "/repo", slightly_newer_v1)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=100)
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=700)
    conn.commit()
    conn.close()

    events, info, _notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 700


def test_v1_only_rows_select_v1(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "v1-root", "/repo", V1_NEWEST_ISO)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=42)
    conn.commit()
    conn.close()

    events, info, _notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v1"
    assert info["session_id"] == "v1-root"
    assert sum(evt["tokens_in"] for evt in events) == 42
    candidates = {c["store"]: c for c in info["store_candidates"]}
    assert candidates["v2"]["id"] is None
    assert candidates["v2"]["newest"] is None


def test_v1_exactly_at_eps_boundary_loses_to_v2(tmp_path: Path) -> None:
    """EPS is an exclusive bound: v1 == v2 + EPS_MS is still a dual-write tie."""
    v1_newest_ms = V2_NEWEST_MS + session_signals.EPS_MS
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "v1-root", "/repo", v1_newest_ms)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=100, tokens_out=10)
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_MS)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=700, tokens_out=70)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    # Guard the fixture itself: the gap is exactly one EPS, no more, no less.
    delta = session_signals._to_epoch_ms(v1_newest_ms) - session_signals._to_epoch_ms(
        V2_NEWEST_ISO
    )
    assert delta == session_signals.EPS_MS

    # v1 would have supplied 100 tokens; seeing 700 proves v2's tree was read.
    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 700
    candidates = {c["store"]: c for c in info["store_candidates"]}
    assert candidates["v1"]["newest"] == session_signals._ms_to_iso(v1_newest_ms)
    assert candidates["v2"]["newest"] == V2_NEWEST_ISO
    assert any("store selected: v2" in note for note in notes)


def test_v2_only_rows_select_v2_without_v1_notes(tmp_path: Path) -> None:
    """Symmetric to test_v1_only_rows_select_v1: planted v2 rows win unopposed."""
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=640, tokens_out=64)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 640
    assert info["time_range"]["newest"] == V2_NEWEST_ISO
    candidates = {c["store"]: c for c in info["store_candidates"]}
    assert candidates["v1"]["id"] is None
    assert candidates["v1"]["newest"] is None
    assert candidates["v2"]["id"] == "v2-root"
    # With no v1 side there is no cross-store comparison to report.
    assert not any("store selected" in note for note in notes)
    assert not any("v1" in note for note in notes)


def test_zero_token_v1_tree_falls_back_to_v2_and_pins_the_note(
    tmp_path: Path,
) -> None:
    """Pins the zero-token fallback branch in _collect_opencode.

    v1 wins freshness but carries no token data, so the collector swaps in the
    v2 events and records ``store selected: v2 (v1 tree had no token data)``.
    """
    v1_newest_ms = V2_NEWEST_MS + 3_600_000
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "v1-root", "/repo", v1_newest_ms)
    # Text signal present, token counters explicitly zero.
    _add_v1_message(
        conn, "v1-m1", "v1-root", text="looks fine", tokens_in=0, tokens_out=0
    )
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=4000, tokens_out=400)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    # The freshness pass picked v1 first...
    assert any(note.startswith("store selected: v1 (newest") for note in notes)
    # ...then the zero-token fallback replaced it with v2 and said exactly that.
    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 4000
    assert "store selected: v2 (v1 tree had no token data)" in notes


def test_no_rows_in_either_store_keeps_the_miss_note(tmp_path: Path) -> None:
    db = _make_db(tmp_path)

    events, info, notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert events == []
    assert info["store"] == ""
    assert info["cwd"] == "/repo"
    assert "No matching OpenCode session for cwd" in notes


def test_to_epoch_ms_reads_iso_ms_seconds_and_garbage() -> None:
    assert int(session_signals._to_epoch_ms(V2_NEWEST_ISO)) == V2_NEWEST_MS
    assert int(session_signals._to_epoch_ms(V2_NEWEST_MS)) == V2_NEWEST_MS
    assert (
        int(session_signals._to_epoch_ms(V2_NEWEST_MS // 1000)) == V2_NEWEST_MS
    )
    assert (
        int(session_signals._to_epoch_ms(str(V2_NEWEST_MS // 1000)))
        == V2_NEWEST_MS
    )
    assert session_signals._to_epoch_ms("not-a-timestamp") == 0.0
    assert session_signals._to_epoch_ms(None) == 0.0


def test_store_selection_accepts_epoch_int_time_updated(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    # v1 stores epoch milliseconds, v2 stores epoch seconds.
    _add_session(conn, "session", "v1-root", "/repo", V1_NEWEST_MS)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=100)
    _add_session(conn, "session_v2", "v2-root", "/repo", V2_NEWEST_MS // 1000)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=800)
    conn.commit()
    conn.close()

    events, info, _notes = session_signals._collect_opencode(
        "/repo", None, db_path=db
    )

    assert info["store"] == "v2"
    assert info["session_id"] == "v2-root"
    assert sum(evt["tokens_in"] for evt in events) == 800


# ---------------------------------------------------------------------------
# D-3 / section 4: wrong-directory detection (defect 2)
# ---------------------------------------------------------------------------


def test_ancestor_directory_id_matches_without_belongs_to_note(
    tmp_path: Path,
) -> None:
    """mdu-45 pin: a session rooted at the workspace parent still matches."""
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "root-id", "/repo", V1_NEWEST_ISO)
    _add_v1_message(conn, "v1-m1", "root-id", tokens_in=55)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo/sub", "root-id", db_path=db
    )

    assert info["session_id"] == "root-id"
    assert info["store"] == "v1"
    assert sum(evt["tokens_in"] for evt in events) == 55
    assert not any("belongs to" in note for note in notes)
    assert "store_candidates" not in info


def test_wrong_directory_id_emits_exact_belongs_to_note(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "other-id", "/elsewhere", V1_NEWEST_ISO)
    _add_v1_message(conn, "v1-m1", "other-id", tokens_in=55)
    conn.commit()
    conn.close()

    events, info, notes = session_signals._collect_opencode(
        "/repo/sub", "other-id", db_path=db
    )

    assert events == []
    assert info["session_id"] == ""
    assert info["store"] == ""
    assert "session id other-id belongs to /elsewhere, not /repo/sub" in notes
    assert info["time_range"] == {"oldest": None, "newest": None}


def test_unknown_id_reports_not_found(tmp_path: Path) -> None:
    db = _make_db(tmp_path)

    _events, info, notes = session_signals._collect_opencode(
        "/repo/sub", "ghost-id", db_path=db
    )

    assert info["session_id"] == ""
    assert "session id ghost-id not found in OpenCode stores" in notes


def test_wrong_directory_parent_recovery_note(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "child-x", "/elsewhere", V1_NEWEST_ISO)
    _add_session(
        conn,
        "session",
        "parent-x",
        "/repo/sub",
        V1_NEWEST_ISO,
        parent_id=None,
    )
    conn.execute("UPDATE session SET parent_id = 'parent-x' WHERE id = 'child-x'")
    conn.commit()
    conn.close()

    _events, _info, notes = session_signals._collect_opencode(
        "/repo/sub", "child-x", db_path=db
    )

    assert (
        "propose parent as root: rerun with --session-id parent-x" in notes
    )


def test_wrong_directory_children_recovery_note(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    _add_session(conn, "session", "parent-x", "/elsewhere", V1_NEWEST_ISO)
    _add_session(
        conn, "session", "kid-1", "/repo/sub", V1_NEWEST_ISO, parent_id="parent-x"
    )
    _add_session(
        conn, "session", "kid-2", "/repo/sub", V1_NEWEST_ISO, parent_id="parent-x"
    )
    conn.commit()
    conn.close()

    _events, _info, notes = session_signals._collect_opencode(
        "/repo/sub", "parent-x", db_path=db
    )

    assert (
        "supplied id has 2 child session(s) under /repo/sub; "
        "rerun without --session-id (freshest-store selection) "
        "or with --cwd /elsewhere" in notes
    )


# ---------------------------------------------------------------------------
# CLI end-to-end with an overridden HOME (hermetic)
# ---------------------------------------------------------------------------


def _seed_home(tmp_path: Path) -> tuple[Path, Path]:
    """Create <home>/.local/share/opencode/opencode.db plus repo dirs."""
    home = tmp_path / "home"
    db = home / ".local" / "share" / "opencode" / "opencode.db"
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    conn = _new_db(db)
    _add_session(conn, "session", "v1-root", str(repo), V1_NEWEST_ISO)
    _add_v1_message(conn, "v1-m1", "v1-root", tokens_in=100)
    _add_session(conn, "session_v2", "v2-root", str(repo), V2_NEWEST_ISO)
    _add_v2_message(conn, "v2-m1", "v2-root", tokens_in=5000)
    conn.commit()
    conn.close()
    return home, repo


def _run_cli(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--harness", "opencode", *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


def test_cli_selects_fresh_v2_store_and_reports_info(tmp_path: Path) -> None:
    home, repo = _seed_home(tmp_path)

    result = _run_cli(home, "--cwd", str(repo))

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["session_id"] == "v2-root"
    assert data["info"]["store"] == "v2"
    candidates = {c["store"]: c for c in data["info"]["store_candidates"]}
    assert candidates["v1"]["id"] == "v1-root"
    assert candidates["v2"]["id"] == "v2-root"
    assert data["info"]["time_range"]["newest"].startswith("2026-10-21")
    assert any("store selected: v2" in note for note in data["notes"])


def test_cli_wrong_directory_exits_zero_with_belongs_to_note(
    tmp_path: Path,
) -> None:
    home, repo = _seed_home(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    conn = sqlite3.connect(home / ".local" / "share" / "opencode" / "opencode.db")
    _add_session(conn, "session_v2", "stray-id", str(elsewhere), V2_NEWEST_ISO)
    conn.commit()
    conn.close()
    sub = repo / "sub"
    sub.mkdir()

    result = _run_cli(home, "--cwd", str(sub), "--session-id", "stray-id")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["session_id"] == ""
    assert data["info"]["store"] == ""
    assert (
        f"session id stray-id belongs to {elsewhere}, not {sub}" in data["notes"]
    )
