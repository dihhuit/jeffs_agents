"""Regression contracts for MDU-34 (canonical resume-block format).

MDU-34 fixes resume-block *emission* only: one fenced `json` template, one
validator (`scripts/lib/resume_block.py`), and `docs/resume-block.md` as the
single documented source. Read-permissiveness of the session-boundary gate is
explicitly preserved (MDU-28's pins keep passing untouched).

Coverage maps to design doc `docs/design/mdu-34-resume-block.md` section D6:

* AC-1a/1b/1c - doc template == mirror template, key set == schema constants,
  the template itself validates.
* AC-2a..2e - recognition clause, first-turn rule, carve-outs, ordering, and
  the no-strict-parser negative guard in every orchestrator mirror.
* AC-3a..3f - CLI contract: exit codes and exact output phrases (D4).
* AC-4a/4b  - prose fixture section and the two `ROLE_KEYWORDS` clauses.

House style follows `test_mdu_28_resume_detect.py`: path constants, lowercase
phrase matching, raw slicing from anchors, and conditional overlay checks.
"""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

import pytest

import resume_block
import validate

REPO_ROOT = Path(__file__).resolve().parents[1]

DOC = REPO_ROOT / "docs" / "resume-block.md"
ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"

# Private overlay sibling; absent in a standalone clone of the public base.
OVERLAY_GROKESTRATOR = (
    REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"
)

BASE_ORCHESTRATOR_FILES = [ORCHESTRATOR_PROMPT, ORCHESTRATOR_GROK]

# The canonical template's lead-in line and the paragraph that closes the
# emission block. Sliced from raw text so the fence contents stay byte-exact.
RESUME_FENCE_ANCHOR = "The resume block you write must be the canonical shape"
RESUME_FENCE_END = "Emit-strict is emission-only"

JSON_FENCE = re.compile(r"```json\n(.*?)\n[ \t]*```", re.S)

# D3.3 pins: the full purpose-recognition clause and its acceptance sentence.
RECOGNITION_CLAUSE = (
    "recognize a resume block by purpose, not by header or exact phrasing"
)
FIRST_TURN_PHRASES = [
    "any first-turn message whose purpose is to say where to pick up counts",
    "two or more of these keys or their variants",
]

# D3.3 carve-outs proving the gate did not narrow.
PERMISSIVE_CARVE_OUTS = [
    "does not narrow what this gate accepts as input",
    "recognition stays by purpose",
]

# D3.5 negative guard: no mirror may become a strict input parser.
BANNED_STRICT_PARSER_PHRASES = [
    "input must be canonical",
    "only a json object",
    "json-only",
    "must be json to count",
    "reject non-canonical",
    "rejected as input",
    "invalid as input",
]

# D4 fixed wording, pinned as literals (not via the module constants) so a
# message change cannot silently pass by updating the constant.
READ_PERMISSIVE_WORDING = (
    "this tool checks canonical emission only; prose and key: value blocks "
    "remain valid gate input (docs/resume-block.md)"
)

MDU_34_ORCHESTRATOR_CLAUSES = [("resume_block.py",), ("canonical shape",)]


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _all_mirrors() -> list[Path]:
    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)
    return files


def _resume_fence_raw(path: Path) -> str:
    """Return the raw (still indented) content of the resume-block fence."""
    text = path.read_text(encoding="utf-8")
    start = text.find(RESUME_FENCE_ANCHOR)
    assert start != -1, f"{path.name} has no canonical-shape lead-in"
    end = text.find(RESUME_FENCE_END, start)
    assert end != -1, f"{path.name}: emission block has no closing paragraph"
    match = JSON_FENCE.search(text[start:end])
    assert match is not None, f"{path.name}: no ```json template in emission block"
    return match.group(1)


def _doc_fence_raw() -> str:
    text = DOC.read_text(encoding="utf-8")
    fences = JSON_FENCE.findall(text)
    assert len(fences) == 1, (
        f"docs/resume-block.md must hold exactly one ```json template, "
        f"found {len(fences)}"
    )
    return fences[0]


def _template(path: Path) -> dict:
    data = json.loads(textwrap.dedent(_resume_fence_raw(path)))
    assert isinstance(data, dict), f"{path.name}: template is not a JSON object"
    return data


def _canonical_block() -> dict:
    return {
        "mdu_id": "mdu-34",
        "branch": "main",
        "commit_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "harness": "opencode",
        "status": "implemented_tests_pending",
        "done": ["scripts/lib/resume_block.py: validate subcommand"],
        "next": ["tests/test_mdu_34_resume_block.py: AC coverage"],
        "blocked_on": [],
        "design": "docs/design/mdu-34-resume-block.md",
        "backlog": "FEATURE_BACKLOG.md",
        "artifacts": ["docs/resume-block.md"],
    }


def _write_fixture(tmp_path: Path, name: str, payload) -> Path:
    path = tmp_path / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


# --- AC-1: template parity and no-drift fuses --------------------------------


def test_ac_1a_doc_template_matches_each_base_mirror() -> None:
    doc = textwrap.dedent(_doc_fence_raw())
    for path in BASE_ORCHESTRATOR_FILES:
        assert textwrap.dedent(_resume_fence_raw(path)) == doc, (
            f"{path.name}: resume template drifted from docs/resume-block.md"
        )


@pytest.mark.skipif(
    not OVERLAY_GROKESTRATOR.exists(),
    reason="overlay sibling opencode_agents/ not present",
)
def test_ac_1a_overlay_grokestrator_template_matches_doc() -> None:
    doc = textwrap.dedent(_doc_fence_raw())
    assert textwrap.dedent(_resume_fence_raw(OVERLAY_GROKESTRATOR)) == doc, (
        "grokestrator.md resume template drifted from docs/resume-block.md"
    )


def test_ac_1b_template_keys_equal_schema_constants() -> None:
    assert len(resume_block.REQUIRED_KEYS) == 11, "canonical shape is eleven keys"
    assert not set(resume_block.REQUIRED_KEYS) & set(resume_block.OPTIONAL_KEYS)

    expected = set(resume_block.REQUIRED_KEYS) | set(resume_block.OPTIONAL_KEYS)
    for path in [DOC, *BASE_ORCHESTRATOR_FILES]:
        if path is DOC:
            data = json.loads(textwrap.dedent(_doc_fence_raw()))
        else:
            data = _template(path)
        assert set(data) == expected, (
            f"{path.name}: template keys {sorted(set(data) ^ expected)} differ "
            f"from REQUIRED_KEYS | OPTIONAL_KEYS"
        )


def test_ac_1c_doc_template_is_a_valid_block() -> None:
    data = json.loads(textwrap.dedent(_doc_fence_raw()))
    assert resume_block.validate_block(data) == [], (
        "docs/resume-block.md template fails resume_block.validate_block: "
        f"{resume_block.validate_block(data)}"
    )


# --- AC-2: read-permissive gate survives emit-strict ------------------------


def test_ac_2a_full_recognition_clause_in_every_mirror() -> None:
    for path in _all_mirrors():
        assert RECOGNITION_CLAUSE in _lower(path), (
            f"{path.name}: missing the full purpose-recognition clause"
        )


def test_ac_2b_first_turn_acceptance_phrases_in_every_mirror() -> None:
    for path in _all_mirrors():
        text = _lower(path)
        for phrase in FIRST_TURN_PHRASES:
            assert phrase in text, f"{path.name}: missing first-turn phrase {phrase!r}"


def test_ac_2c_permissive_carve_outs_in_every_mirror() -> None:
    for path in _all_mirrors():
        text = _lower(path)
        for phrase in PERMISSIVE_CARVE_OUTS:
            assert phrase in text, f"{path.name}: missing carve-out {phrase!r}"


def test_ac_2d_recognition_precedes_the_canonical_template() -> None:
    # The permissive rule must reach the reader BEFORE the strict template,
    # so the template cannot be read as an input requirement.
    for path in _all_mirrors():
        text = _lower(path)
        recognition = text.index(RECOGNITION_CLAUSE)
        template = text.index(RESUME_FENCE_ANCHOR.lower())
        assert recognition < template, (
            f"{path.name}: recognition clause at {recognition} does not precede "
            f"the canonical template at {template}"
        )


def test_ac_2e_no_strict_input_parser_language_in_any_mirror() -> None:
    assert len(BANNED_STRICT_PARSER_PHRASES) == 7, "D3.5 bans exactly 7 phrases"
    for path in _all_mirrors():
        text = _lower(path)
        for phrase in BANNED_STRICT_PARSER_PHRASES:
            assert phrase not in text, (
                f"{path.name}: contains banned strict-parser phrase {phrase!r}"
            )


# --- AC-3: CLI contract -----------------------------------------------------


def test_ac_3a_canonical_example_exits_zero(tmp_path: Path, capsys) -> None:
    fixture = _write_fixture(tmp_path, "canonical.json", _canonical_block())
    assert resume_block.main(["validate", str(fixture)]) == 0
    out = capsys.readouterr().out
    assert "[ok]" in out, out
    assert f"{fixture} is a canonical resume block" in out, out
    assert "[warn]" not in out, out


def test_ac_3b_missing_commit_sha_exits_one(tmp_path: Path, capsys) -> None:
    block = _canonical_block()
    del block["commit_sha"]
    fixture = _write_fixture(tmp_path, "missing-sha.json", block)

    assert resume_block.main(["validate", str(fixture)]) == 1
    out = capsys.readouterr().out
    assert "[fail]" in out, out
    assert "missing required key: 'commit_sha'" in out, out


def test_ac_3c_extra_key_warns_but_exits_zero(tmp_path: Path, capsys) -> None:
    block = _canonical_block()
    block["sha"] = "deadbeef"
    fixture = _write_fixture(tmp_path, "extra-key.json", block)

    assert resume_block.main(["validate", str(fixture)]) == 0
    out = capsys.readouterr().out
    assert "[ok]" in out, out
    assert (
        "  [warn]  extra key 'sha' is not part of the canonical shape" in out
    ), out


@pytest.mark.parametrize(
    "label,payload,expected",
    [
        (
            "scalar-wrong-type",
            lambda b: b.update({"mdu_id": 34}),
            "'mdu_id' must be a non-empty string",
        ),
        (
            "scalar-empty",
            lambda b: b.update({"branch": "   "}),
            "'branch' must be a non-empty string",
        ),
        (
            "array-not-a-list",
            lambda b: b.update({"done": "no"}),
            "'done' must be an array of strings",
        ),
        (
            "array-element-not-str",
            lambda b: b.update({"next": ["ok", 3]}),
            "'next' must be an array of strings",
        ),
        (
            "harness-outside-enum",
            lambda b: b.update({"harness": "emacs"}),
            "harness must be one of opencode|grok|claude (got 'emacs')",
        ),
        (
            "both-design-backlog-empty",
            lambda b: b.update({"design": "", "backlog": ""}),
            "missing required field: 'design' or 'backlog' (one must be non-empty)",
        ),
        (
            "either-or-wrong-type",
            lambda b: b.update({"design": ["docs/design/x.md"]}),
            "'design' must be a string",
        ),
    ],
)
def test_ac_3d_shape_violations_exit_one(
    tmp_path: Path, capsys, label: str, payload, expected: str
) -> None:
    block = _canonical_block()
    payload(block)
    fixture = _write_fixture(tmp_path, f"{label}.json", block)

    assert resume_block.main(["validate", str(fixture)]) == 1, label
    out = capsys.readouterr().out
    assert expected in out, f"{label}: expected {expected!r} in {out!r}"


def test_ac_3d_top_level_not_an_object_exits_one(tmp_path: Path, capsys) -> None:
    fixture = _write_fixture(tmp_path, "array.json", "[1, 2, 3]")

    assert resume_block.main(["validate", str(fixture)]) == 1
    out = capsys.readouterr().out
    assert "resume block must be a JSON object" in out, out


def test_ac_3e_prose_input_fails_with_read_permissive_message(
    tmp_path: Path, capsys
) -> None:
    fixture = _write_fixture(
        tmp_path,
        "prose.txt",
        "Resuming MDU-34 on main; next: land the validator. Blocked on nothing.\n",
    )

    assert resume_block.main(["validate", str(fixture)]) == 1
    out = capsys.readouterr().out
    assert "not valid JSON" in out, out
    assert READ_PERMISSIVE_WORDING in out, out


def test_ac_3e_missing_fixture_exits_one(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "does-not-exist.json"

    assert resume_block.main(["validate", str(missing)]) == 1
    out = capsys.readouterr().out
    assert "resume block not found" in out, out


def test_ac_3f_no_args_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        resume_block.main([])
    assert excinfo.value.code == 2


# --- AC-4: prose fixture and validator clause binding -----------------------


def test_ac_4a_prose_fixture_section_and_facts() -> None:
    text = DOC.read_text(encoding="utf-8")
    start = text.find("## Prose fixture")
    assert start != -1, "docs/resume-block.md has no prose-fixture section"
    section = text[start:]

    quoted = [
        line[2:].strip()
        for line in section.splitlines()
        if line.startswith("> ")
    ]
    assert quoted, "prose-fixture section has no blockquote fixture"
    fixture = "\n".join(quoted).lower()

    # The fixture is what the gate must still accept: it has to carry the
    # recognition-relevant facts, not just be any paragraph.
    for fact in ["mdu-34", "main", "deadbeef", "next:", "blocked"]:
        assert fact in fixture, (
            f"prose fixture is missing recognition-relevant fact {fact!r}"
        )


def test_ac_4b_role_keywords_bind_to_both_base_mirrors() -> None:
    clauses = validate.ROLE_KEYWORDS["orchestrator"]
    for clause in MDU_34_ORCHESTRATOR_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] missing MDU-34 clause {clause!r}"
        )

    mirror_texts = [_lower(path) for path in BASE_ORCHESTRATOR_FILES]
    for clause in MDU_34_ORCHESTRATOR_CLAUSES:
        bound = [
            alt
            for alt in clause
            if all(alt.lower() in text for text in mirror_texts)
        ]
        assert bound, (
            f"validator clause {clause!r} binds to no alternative present in both "
            f"orchestrator mirrors; it would not track the MDU-34 contract"
        )
