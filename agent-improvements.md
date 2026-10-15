# Agent improvement log

Orchestrators: read "Open suggestions" at session start and after every MDU. Apply "apply-now" items in the next delegation. Do not edit agent definition files unless the user asked.

## Open suggestions

- [ ] id: 20261014-1 | severity: high | target: grokestrator | kind: long_cycle
  - evidence: opencode session ses_ec32e70b8ffeoSxBhBeVezU1Jg; grokestrator active 1126s, wall 1126s across 36 events while driving MDU-20 (promote inception agent). One orchestrator agent is doing the work of design + many implement iterations.
  - definition change: Before any delegation, write a one-paragraph "what done looks like" (file list + tests run + verdict format) at the top of the brief. Decompose any MDU whose brief exceeds ~200 lines into two sequential MDUs.
  - apply-now: Narrow the next MDU brief handed to grokestrator to a single deliverable (e.g. "port prompts/inception.md and grok/agents/inception.md, do not touch opencode.json until review passes"). Require a concrete file list and the test/QA outcome before grokestrator moves to the next delegation.

- [ ] id: 20261014-2 | severity: warn | target: grokestrator | kind: token_hotspot
  - evidence: opencode session ses_ec32e70b8ffeoSxBhBeVezU1Jg; grokestrator consumed 344,267 tokens (43% of session total). Inputs 332,571 vs outputs 11,696 — ~28:1 in:out ratio, a sign the orchestrator is re-reading its own context.
  - definition change: Do not paste whole files into the orchestrator context. Pass file paths + a 20-line excerpt at most. After each sub-agent reply, summarise the result in <=5 lines before the next delegation.
  - apply-now: In the next brief, list the three or four files the orchestrator actually has to look at and forbid quoting full file bodies. Tell it to keep its own scratch notes to 5 lines per sub-agent reply.

- [ ] id: 20261014-3 | severity: warn | target: grok-just-code | kind: token_hotspot
  - evidence: opencode session ses_ec32e70b8ffeoSxBhBeVezU1Jg; grok-just-code consumed 115,084 tokens (14% of session) over 18 messages. Active time only 141s, so the model is being asked to ingest a lot of context per message.
  - definition change: Receive only the failing test, the target files, and the explicit constraints. Do not re-derive architecture from prompts/ in the brief — assume it is already known.
  - apply-now: When delegating to grok-just-code next, give it the diff scope (target file paths + acceptance test command) and forbid reading more than two unrelated files.

- [ ] id: 20261014-4 | severity: warn | target: code-reviewer | kind: token_hotspot
  - evidence: opencode session ses_ec32e70b8ffeoSxBhBeVezU1Jg; code-reviewer emitted 104 messages (most of any agent) and consumed 111,170 tokens (14% of session). 103,242 in vs 7,928 out — reviewer is being shown too much context per check.
  - definition change: Review only the listed diff. Read each touched file once. Output the verdict as a file:line + severity table and stop. Do not re-read unrelated files or repeat the same check across many turns.
  - apply-now: In the next code-reviewer brief, list the exact files added/changed by this MDU and cap the review at a single pass with one verdict (APPROVE / REQUEST CHANGES) plus a numbered findings list.

## Session records

### 2026-10-14T16:52-07:00 — opencode session ses_ec32e70b8ffeoSxBhBeVezU1Jg — mdu mdu-20
MDU-20 ("Promote inception agent to the public base") is still in_progress per runs/mdu-20/manifest.json. The OpenCode session shows a grok-orchestrator driving the loop: design (architect, 10 msgs, ~68k tok), implement/rework (grok-just-code, 18 msgs, ~115k tok), many small review passes (code-reviewer, 104 msgs, ~111k tok), qa (29 msgs, ~63k tok), grok-test-agent (9 msgs, ~43k tok), devops (5 msgs, ~21k tok), and the introspector itself (13 msgs, ~33k tok). fix_iterations=0 and no phase failed, so the manifest-derived signals (fix_loop / phase_fail_streak) did not fire. The four collected signals are: long_cycle high on grokestrator (1126s active across 36 events) and token_hotspot warn on grokestrator (344,267 tok / 43% share), grok-just-code (115,084 tok / 14% share), and code-reviewer (111,170 tok / 14% share). No review-rejection streak, no QA-fail repeat, no permission thrash, no context reread beyond the script's CONTEXT_REREAD_THRESHOLD=4.

## Definition proposals

Used only in review mode. List proposed definition diffs here. Mark each as `status: not applied` until the user says the exact phrase `apply the definition diffs`; then mark only the accepted diffs as `status: applied`.

- status: not applied — target: opencode_agents/grok/agents/grokestrator.md and base grok/agents/orchestrator.md — append: "Decompose any MDU whose brief exceeds ~200 lines into two sequential MDUs. Before any delegation, write a one-paragraph 'what done looks like' (file list + tests + verdict format) at the top of the brief. Do not paste whole files into the orchestrator context; pass file paths + a 20-line excerpt at most. After each sub-agent reply, summarise the result in <=5 lines before the next delegation."
- status: not applied — target: opencode_agents/overlays/grok/agents/grok-just-code.md and base grok/agents/just-code.md — append: "Receive only the failing test, the target files, and the explicit constraints. Do not re-derive architecture from prompts/ in the brief — assume it is already known. Cap unrelated file reads at two."
- status: not applied — target: base prompts/code-reviewer.md and base grok/agents/code-reviewer.md — append: "Review only the listed diff. Read each touched file once. Output the verdict as a file:line + severity table and stop. Do not re-read unrelated files or repeat the same check across many turns. Cap the review at one verdict (APPROVE / REQUEST CHANGES) plus a numbered findings list."