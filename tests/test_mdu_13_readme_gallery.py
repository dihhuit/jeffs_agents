#!/usr/bin/env python3
"""MDU-13 tests: README modernization and artifact gallery."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
OPENCODE = REPO / "opencode.json"
FEATURE_BACKLOG = REPO / "FEATURE_BACKLOG.md"
EXAMPLES_README = REPO / "examples" / "README.md"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 _-]+", "", text)
    text = text.replace(" ", "-")
    return text


def md_links(text: str):
    links = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        links.append((m.group(1), m.group(2)))
    return links


def resolve(target: str):
    if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
        return True, "external"
    target = target.split("#", 1)[0]
    if not target:
        return True, "same"
    p = REPO / target
    if p.exists():
        return True, str(p)
    return False, str(p)


def test_badge_row_present_and_wellformed():
    text = README.read_text()
    first_lines = "\n".join(text.splitlines()[:20])
    assert "[![" in first_lines and "](https://github.com/" in first_lines
    # All workflow badges referenced
    wf_dir = REPO / ".github" / "workflows"
    if wf_dir.exists():
        for wf in wf_dir.iterdir():
            if wf.is_file() and wf.suffix in (".yml", ".yaml"):
                name = wf.name
                # expect badge referencing it
                assert f"actions/workflows/{name}/badge.svg" in text or f"actions/workflows/{name}/badge" in text


def test_whats_inside_table_covers_every_roster_agent():
    data = json.loads(OPENCODE.read_text())
    agents = set(data.get("agents", {}).keys()) if isinstance(data.get("agents"), dict) else set()
    text = README.read_text()
    # Find What's Inside section
    idx = text.find("## What's Inside")
    assert idx >= 0
    # Get until next ## at column 0
    rest = text[idx:]
    m = re.search(r"\n## [^#]", rest)
    section = rest[:m.start()] if m else rest
    for a in agents:
        pattern = r"\|\s*\[`" + re.escape(a) + r"`\]\([^)]+\)"
        assert re.search(pattern, section), f"Missing link for agent {a}"


def test_every_readme_relative_link_resolves():
    text = README.read_text()
    for label, target in md_links(text):
        ok, info = resolve(target)
        if target.startswith("http") or target.startswith("mailto:"):
            continue
        assert ok, f"Broken link: [{label}]({target}) -> {info}"


def test_readme_anchors_resolve():
    text = README.read_text()
    for label, target in md_links(text):
        if "#" not in target:
            continue
        if target.startswith("http"):
            continue  # skip external anchors for now
        path_part, anchor = target.split("#", 1)
        if not path_part:
            p = README
        else:
            p = REPO / path_part
        if not p.exists():
            continue  # will be caught by other test
        content = p.read_text()
        # collect headings
        headings = []
        for hm in re.finditer(r"^#{1,6}\s+(.+)$", content, re.M):
            h = hm.group(1).strip()
            # remove markdown links in heading
            h2 = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", h)
            headings.append(slugify(h2))
        # GitHub style: drop trailing punctuation differences? simple
        assert anchor in headings or anchor.replace(".", "") in headings, f"Missing anchor {anchor} in {p}"


def test_todo_section_removed():
    text = README.read_text()
    assert "### TODO" not in text
    assert "Split agent definitions into Go-only and Zen-only variants" not in text
    assert "Seed the empty `skills/` directory" not in text


def test_backlog_has_mdu33_zen_item():
    text = FEATURE_BACKLOG.read_text()
    assert "### MDU-33" in text
    assert "Zen-only" in text


def test_roadmap_links_both_analysis_docs():
    text = README.read_text()
    idx = text.find("## Roadmap")
    assert idx >= 0
    rest = text[idx:idx+800]
    assert "GAP_ANALYSIS.md" in rest
    assert "FEATURE_BACKLOG.md" in rest
    assert re.search(r"20\d{2}-\d{2}-\d{2}", rest) or "last verified" in rest.lower()


def test_layout_tree_counts_match_reality():
    text = README.read_text()
    idx = text.find("## Repository Layout")
    assert idx >= 0
    rest = text[idx:idx+2000]
    data = json.loads(OPENCODE.read_text())
    agents = len(data.get("agents", {})) if isinstance(data.get("agents"), dict) else 0
    assert str(agents) in rest
    assert "grok/agents" in rest
    assert "skills/" in rest
    assert "prompts/" in rest


def test_gallery_index_and_entries():
    assert EXAMPLES_README.exists()
    text = EXAMPLES_README.read_text()
    # links to gallery entries
    gallery_links = re.findall(r"\((gallery/[^)]+\.md)\)", text)
    assert len(gallery_links) >= 2
    for gl in gallery_links:
        p = REPO / "examples" / gl
        assert p.exists(), f"Missing {p}"
        c = p.read_text()
        assert "examples/runs/" in c
        assert "```json" in c


def test_gallery_manifest_ids_match_runs():
    text = EXAMPLES_README.read_text()
    for gl in re.findall(r"\((gallery/[^)]+\.md)\)", text):
        p = REPO / "examples" / gl
        c = p.read_text()
        m = re.search(r"(examples/runs/([^/]+)/manifest\.json)", c)
        assert m, f"No manifest link in {p}"
        rel = m.group(1)
        mid = m.group(2)
        mp = REPO / rel
        assert mp.exists(), f"Missing manifest {mp}"
        data = json.loads(mp.read_text())
        assert data.get("mdu_id") == mid
        assert data.get("status") == "completed"


def test_every_grok_profile_linked_from_readme():
    text = README.read_text()
    for p in (REPO / "grok" / "agents").glob("*.md"):
        stem = p.stem
        # must appear as a link or in text
        assert stem in text, f"Grok profile {stem} not mentioned in README"
    for p in (REPO / "prompts").glob("*.md"):
        stem = p.stem
        assert stem in text, f"Prompt {stem} not mentioned in README"
