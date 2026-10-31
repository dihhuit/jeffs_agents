# Brief checklist — dispatch-time mirror of the apply-now set

This is a **DOC, not a prompt or agent-definition file**. Editing it changes no
agent behavior and nothing under `prompts/` or `grok/agents/` is derived from
it. `agent-improvements.md` stays the canonical source of every entry; this
checklist is only the dispatch-time mirror the orchestrator reads while writing
a brief, keyed by the same `[id]` citations.

Use it as follows: copy the "Every brief" block into each brief, then copy the
block for the delegated role. Every clause is one line so it can be pasted
verbatim.

## Every brief

- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies; keep per-child summaries to 5 lines. [20261014-2]
- Sequence phases explicitly: devops runs after review and after the last fix cycle; any fix cycle is followed by re-running the affected suite and both builds. [20261021-6]
- Carry a who-executes/who-grades routing table for every command-bearing phase; never assign commands the target agent's allowlist cannot run. [20261021-9]
- Record a top-level model field in the manifest (the session's orchestrator model) so tier compliance is auditable. [20261026-2]
- Finalize the manifest fully before dispatching QA (all phases, verification block, summary, completed_at) and validate to exit 0; after QA only qa_grade flips. [20261027-3]

## architect

- Architect briefs list the authoritative files with short excerpts, forbid full-tree reads, and the design doc opens with its surveyed-file list. [20261024-1]
- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies; keep per-child summaries to 5 lines. [20261014-2]

## just-code / fix child

- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies; keep per-child summaries to 5 lines. [20261014-2]

## code-reviewer

- Tell the reviewer up front: shell is denied by design — scope this static-trace, gate outputs are attached, report a denial in one line and never as a REJECT. [20261030-2]
- Name the evidence producer before dispatching the reviewer (devops preferred); a dated review-evidence.md lists each command, exit code, and output path; re-run it after each fix cycle. [20261021-12]

## test-agent

- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Sequence phases explicitly: devops runs after review and after the last fix cycle; any fix cycle is followed by re-running the affected suite and both builds. [20261021-6]

## devops

- Sequence phases explicitly: devops runs after review and after the last fix cycle; any fix cycle is followed by re-running the affected suite and both builds. [20261021-6]
- Name the evidence producer before dispatching the reviewer (devops preferred); a dated review-evidence.md lists each command, exit code, and output path; re-run it after each fix cycle. [20261021-12]
- Carry a who-executes/who-grades routing table for every command-bearing phase; never assign commands the target agent's allowlist cannot run. [20261021-9]

## qa

- If the first QA reply is empty or lacks the GRADE line, request a re-run and accept only a second response. [20261029-1]
- QA must attest it validated the exact final manifest path; append every completed phase including qa and validate. [20261014-5]
- Finalize the manifest fully before dispatching QA (all phases, verification block, summary, completed_at) and validate to exit 0; after QA only qa_grade flips. [20261027-3]
- Carry a who-executes/who-grades routing table for every command-bearing phase; never assign commands the target agent's allowlist cannot run. [20261021-9]

## introspector

- QA must attest it validated the exact final manifest path; append every completed phase including qa and validate. [20261014-5]
- Record a top-level model field in the manifest (the session's orchestrator model) so tier compliance is auditable. [20261026-2]
