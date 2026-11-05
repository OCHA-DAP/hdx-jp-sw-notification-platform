# Agent Instructions — HDX OPENAPI SPECS

These instructions apply to all AI coding assistants working in this repository
(Claude, GitHub Copilot, Gemini, and others). Tool-specific files (CLAUDE.md,
GEMINI.md, .github/copilot-instructions.md) point back to this file.

## Core Principles

1. Understand existing logic before editing.
2. Preserve current behavior unless a change is explicitly requested.
3. Prefer the smallest diff that solves the request.
4. Reuse existing modules, helpers, and patterns before adding new abstractions.
5. Avoid unrelated refactors, renames, or formatting-only edits.
6. Keep public interfaces and config contracts stable unless a change is required.
7. If behavior must change, clearly explain what changed and why.

## Spec-Driven Development

- Specs live in `specs/` — one Markdown file per **feature area**
  (e.g. `authentication.md`, `billing.md`), not per small feature or fix.
  Don't create a new file for every change; add to an existing feature
  area's file when the work fits there. Start from
  `specs/_TEMPLATE.md` when a genuinely new feature area is needed.
- Every requirement has a unique ID — `<FEATURE_AREA>-<NNN>` (e.g.
  `AUTHENTICATION-003`), sequential and scoped to its file. Never reuse or
  renumber an ID, even after removing a requirement; a stable ID is what
  makes it safe to reference elsewhere (commit messages, code comments,
  other specs).
- Status markers: `[x]` implemented, `[ ]` planned/not yet implemented.
- Before implementing a change covered by (or that should be covered by) a
  spec:
  1. Update the relevant specs file first.
  2. Get human approval on the spec change.
  3. Only then implement.
  This is a hard requirement, not a suggestion — do not skip ahead to
  implementation on spec-covered work without approval.
- specs files are the source of truth for functional scope. If code
  and spec disagree, that's a bug in one of them — flag it, don't silently
  pick one.

## Testing

- All code must be covered by unit tests — new code ships with tests in the
  same change, not as a follow-up.
- When changing existing behavior, update the tests that cover it rather
  than leaving them stale or deleting coverage to make a change easier.
- Tests live in `tests/`, mirroring the structure of the code they cover.
- A change isn't done until its tests exist and the full test suite passes —
  not just the tests for the touched area.

## Required Workflow

1. Read the relevant files and existing implementation first.
2. Identify the minimal edit location.
3. Implement only the necessary changes, writing or updating unit tests for
   them in the same change.
4. Run the full test suite, plus lint/type checks, for validation.
5. Summarize the change and any assumptions made, citing the requirement
   ID(s) it addresses, if any.

## Constraints

- Do not rewrite working code when a local patch is sufficient.
- Do not introduce new dependencies unless there is a clear need.
- Do not remove logs, error handling, or guards without replacing equivalent behavior.
- Do not change environment variable names or defaults without an explicit request.
- Never write hardcoded secrets into code: API keys, passwords, tokens,
  private keys, or other credentials. Use environment variables (or the
  project's existing secrets mechanism) instead. If a change seems to
  require a literal credential, stop and ask first rather than writing it
  in. This also means never committing one — if you notice a key-shaped
  string already staged for commit, treat that as a bug to fix, not
  something to commit.

## When Uncertain

- State assumptions explicitly.
- Ask a clarifying question before making broad or risky changes.
