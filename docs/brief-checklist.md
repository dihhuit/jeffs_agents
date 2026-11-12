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
- For wording/term sweeps, grep the old term across BOTH repos (source and built/installed trees), attach the file:line hit list to the implement brief, pin zero live hits rather than a file count, and name excluded dead copies with the reason. [20261030-3]
- If any edit/write tool result looks corrupted or unexpected, verify the file on disk (grep/read) before quoting it in a brief, manifest, or verdict. [20261031-2]

## architect

- Architect briefs list the authoritative files with short excerpts, forbid full-tree reads, and the design doc opens with its surveyed-file list. [20261024-1]
- Design docs write paths repo-relative or as `$WORKSPACE/<subpath>`, never literal absolute paths. [20261030-5]
- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies; keep per-child summaries to 5 lines. [20261014-2]

## just-code / fix child

- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies; keep per-child summaries to 5 lines. [20261014-2]

## code-reviewer

- Tell the reviewer up front: shell is denied by design — scope this static-trace, gate outputs are attached, report a denial in one line and never as a REJECT. [20261030-2]
- Prompt-text checks are traced as procedures (one line per repo variant), not presence-ticked. [20261021-11]
- Name the evidence producer before dispatching the reviewer (devops preferred); a dated review-evidence.md lists each command, exit code, and output path; re-run it after each fix cycle. [20261021-12]

## test-agent

- The working tree is the source of truth; never run destructive git state commands. [20261017-1]
- Open every brief with a one-paragraph what-done-looks-like (file list, tests run, verdict format); one single deliverable per brief; split any brief over ~200 lines. [20261014-1]
- Sequence phases explicitly: devops runs after review and after the last fix cycle; any fix cycle is followed by re-running the affected suite and both builds. [20261021-6]

## devops

- Sequence phases explicitly: devops runs after review and after the last fix cycle; any fix cycle is followed by re-running the affected suite and both builds. [20261021-6]
- Name the evidence producer before dispatching the reviewer (devops preferred); a dated review-evidence.md lists each command, exit code, and output path; re-run it after each fix cycle. [20261021-12]
- Carry a who-executes/who-grades routing table for every command-bearing phase; never assign commands the target agent's allowlist cannot run. [20261021-9]

## qa

- If the first QA reply is empty or lacks the GRADE line, request a re-run and accept only a second response. [20261029-1]
- Denied shell → one simple `timeout <n> <command>` attempt, then fast fallback with 'verified via orchestrator-attached output' labels. [20261021-8]
- Pre-state the exact probe commands (plain allowlisted form) and the file-tool fallback (read/grep/sed) in every command-bearing QA brief; a denial QA reports is a form/permission event, not missing coverage. [20261110-1]
- Name the durable-artifact writer (just-code/devops) in every QA brief whose verdict must persist as a file; QA does not write artifacts. [20261112-2]
- The QA reply is the deliverable; a write-capable agent persists durable artifacts; QA briefs pre-state "do not attempt writes." [20261112-2]
- Prompt-text acceptance criteria are traced, not presence-ticked. [20261021-11]
- QA must attest it validated the exact final manifest path; append every completed phase including qa and validate. [20261014-5]
- Finalize the manifest fully before dispatching QA (all phases, verification block, summary, completed_at) and validate to exit 0; after QA only qa_grade flips. [20261027-3]
- Carry a who-executes/who-grades routing table for every command-bearing phase; never assign commands the target agent's allowlist cannot run. [20261021-9]

## introspector

- QA must attest it validated the exact final manifest path; append every completed phase including qa and validate. [20261014-5]
- Record a top-level model field in the manifest (the session's orchestrator model) so tier compliance is auditable. [20261026-2]
- Before recording a definition change unapplied, grep the target file(s) for the clause text and cite the commit hash when git is available; correct or close stale claims with evidence. [20261101-1]
- Add the plain-form retry line to the introspector brief: run the signal script as `timeout N python3 <script>`, no compounds, pipes, or redirects; bare `echo`/`pwd` and compound denials are by design. [20261110-1]
