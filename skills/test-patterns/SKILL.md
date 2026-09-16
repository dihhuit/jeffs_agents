---
name: test-patterns
description: Test-authoring patterns for the test agent — priority ordering (happy path, edges, error paths, boundaries), property-based/fuzz guidance for complex input domains, meaningful-assertion rules, and the coverage-gap reporting format. Load when writing or extending a test suite.
license: Unlicense
metadata:
  audience: [test-agent]
---

# Test Patterns

Write tests that validate real behavior, not implementation details. Target reads to the relevant source; write targeted tests over sprawling suites.

## Priority ordering

Write tests in this order, most important first:

1. **Happy path** — the primary use case works end to end.
2. **Edge cases** — unusual but valid inputs (empty, single-element, max-size, unicode, etc.).
3. **Error paths** — invalid inputs and failure modes produce the right errors/status codes.
4. **Boundaries** — values at and just past limits (off-by-one, min/max, overflow).

## Property-based / fuzz

Use property-based or fuzz testing for functions with complex input domains:

- Generate a wide input space (fast-check, Hypothesis, etc.) and assert invariants, not exact outputs.
- Good candidates: parsers, validators, serializers, math/aggregation, anything with large string or numeric domains.
- Keep a small set of hand-written example-based tests for readability alongside the property tests.

## Meaningful assertion rules

- NEVER empty asserts or no-op stubs — a test must fail when the behavior it guards breaks.
- Assert on observable behavior (return values, side effects, state), not implementation details.
- Each test asserts the specific thing it names; avoid asserting everything in one test.
- Prefer precise matchers over broad ones (e.g., exact error message where stable).

## Coverage-gap reporting format

Report coverage gaps clearly, e.g.:

```
Coverage gaps:
- <module/function> — <what is untested> — <risk if it breaks> — <suggested test>
```

Also report test results: pass/fail counts, and any flaky or skipped tests with reasons.

## Rules

- NEVER modify source/production code to make tests pass — report bugs to the orchestrator instead.
- NEVER delete or disable existing tests; flag flaky or wrong tests to the orchestrator.
- Follow existing test conventions (framework, style, directory structure).