# MDU-43 — Hygiene sweep: registry dead rows, research-delegation wording, backlog reconciliation

Design authored by the orchestrator (small, mechanical MDU; facts verified live in-session 2026-10-30).

## D1 — `config/model-registry.txt` dead rows

Verified this session:

- The registry is a committed snapshot of `opencode models` output (`scripts/lib/model_registry.py` docstring); `load_registry` **ignores `#` comment lines**.
- `timeout 60 opencode models` STILL lists `opencode-go/mimo-v2.5` and `opencode-go/mimo-v2.5-pro` (upstream catalog itself is stale) while the MDU-40 test-phase live probe proved `mimo-v2.5` deprecated upstream (fix cycle 1 evidence; agent rows repointed to mimo-v2.6-flash).
- No config references either ID; `tests/test_mdu_40_paid_default.py::RETIRED_IDS` already forbids `opencode-go/mimo-v2.5` in openopen.json only.

**Decision:** comment out `opencode-go/mimo-v2.5` and `opencode-go/mimo-v2.5-pro` with a dated note, rather than deleting:
- keeps catalog-layout parity visible (the `opencode models` output does list them);
- removes both from the validation set immediately;
- is self-documenting about WHY they must never be referenced/re-activated.

Before commenting `-pro` (no kill evidence on file for that exact ID), run the config-driven probe. If the probe cannot decide, comment it too but record "no live-probe evidence, catalog-stale assumption" in the manifest notes — both IDs are from the same deprecated family the MDU-40 probe killed.

## D2 — `research` → `deep-research` delegation wording

Verified this session (design D5 of MDU-41 covered only the architect mirrors):

- `prompts/devops.md:11`, `grok/agents/devops.md:17`, `prompts/code-reviewer.md:13`, `grok/agents/code-reviewer.md:19` all say "Delegate to `research`".
- The correct agent id is `deep-research` (see architect mirrors after the MDU-41 fix: "Delegate to `deep-research` when you need to investigate libraries, patterns, or best practices.").
- `opencode.json` source already repointed `research` permission allows to `deep-research` (test_mdu_40 asserts it).

**Decision:** replace bare `research` with `deep-research` in the 4 files, keeping each file's sentence otherwise intact (minimal hunk).

## D3 — FEATURE_BACKLOG.md status reconciliation

- MDU-12 → `Done — 2026-09-15` (commit `5caf6d1` "feat(MDU-06,08,12,14): … autonomy gates …"; `docs/autonomy.md` is its artifact).
- MDU-14 → `Done — 2026-09-15` (same commit; parity checks live in `scripts/lib/validate.py` + `tests/test_validate_parity.py`).
- MDU-33 → `Superseded by MDU-40 — 2026-10-30` (the zen tier it was scoped around was retired: deploy default paid, `--tier=zen` exit 2, gen_zen map deleted; the user's actual pain was solved inversely by the single paid config + fallback ladder).
- MDU-35 → `Done — 2026-10-26` (question-tool forensics + the QUESTION TOOL discipline clause shipped in all three mirrors; see the mdu-35 session record and `docs/design/mdu-35-question-tool.md`).

## D4 — Pins (test-agent)

New `tests/test_mdu_43_hygiene.py`:

1. Registry snapshot has no ACTIVE (uncommented) `mimo-v2.5` model rows.
2. The four delegated files (`prompts/devops.md`, `grok/agents/devops.md`, `prompts/code-reviewer.md`, `grok/agents/code-reviewer.md`) contain `deep-research` and no bare `research` delegation.

## D5 — Who executes / who grades

| Step | Executes | Grades / verifies |
|---|---|---|
| snapshot/pytest/prompt gate/build | just-code (implement child) | orchestrator attaches outputs to the review brief |
| review | nobody — static-trace (read-only sandbox by design) | code-reviewer |
| suites | test-agent | — |
| both builds + prompt gate + secret gate + live deploy | devops | QA |
| validation | per re-run/verified-from-record split | qa |
