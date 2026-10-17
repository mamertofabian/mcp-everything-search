---
name: maid-implementer
description: Implement code against an approved MAID manifest. Loads only the declared files, writes code to pass behavioral tests, validates with `maid validate --mode implementation`, and iterates until all checks pass. Use after a manifest is approved by maid-planner (or manually).
---

# MAID Implementer

Execute code implementation against an approved MAID manifest. The manifest is the contract.

When the starting point is still `manifests/drafts/*.manifest.yaml`, use
`maid-implement-draft` to harden, lock, and promote first. This skill implements
an already-approved (typically promoted) contract.

## Rules

- Load the manifest first.
- Implement only what the manifest declares.
- `files.create` and `files.edit` declare contracted public artifacts.
- `files.scope` declares writable implementation files that have no stable
  public artifact contract, such as route/page wiring covered by behavioral
  tests.
- `files.read` is dependency context, not writable production scope. Do not
  edit production files listed only in `files.read`; stop for plan revision and
  move intentional no-artifact wiring to `files.scope`.
- Implementer sessions run validation gates with `--packet`; for example,
  `maid validate --packet` and `maid verify --profile agent-retry --since <baseline>`.
- strict gates are the default. Use `--legacy-gates` only as a bounded
  migration aid when comparing behavior against pre-flip defaults.
- Run `maid validate --mode implementation` after implementation.
- Run all manifest `validate` commands.
- NEVER modify files not listed in the manifest `files.create`, `files.edit`,
  `files.scope`, or `files.delete`.
- NEVER modify the manifest during implementation.
- NEVER modify behavioral tests unless the user explicitly approves changing the contract.
- If implementation validation exposes a bad manifest, write `plan-revision.md` explaining the issue and stop. Do not force tests green by working around a bad plan.
- If the manifest has `temptations`, restate the relevant risk/procedure pairs before editing and treat each `instead` as the working procedure.

## Packet-Driven Retry Gates

When a packet-aware gate fails, read `.maid/last-failure-packet.json` instead of re-exploring the repository. The packet is the retry context: failed command argv, exit code, project root, failed manifest excerpts, diagnostics, `next_action` repair recipes, failed-command output tails, and environment versions.

Respect `next_action` exactly. Valid kinds include `edit-implementation`,
`edit-tests`, `edit-manifest`, `run-command`, `revise-plan`, and
`escalate-human`; kinds that change tests or manifests route through explicit
plan revision when the contract must change. Recipes never authorize weakening tests or manifests to silence errors, and they never authorize weakening tests or manifests as the first remedy for an implementation failure.

Stop at the default 5 attempt bound. If the gate still fails, or the packet
requests `escalate-human`, stop and escalate to a human with the final packet
instead of looping, hiding the failure, or broadening scope.

## Plan Revision Recovery

If implementation review requires review-driven behavioral contract changes
after implementation already exists, do not invent a manual stash or worktree
procedure. Use the sanctioned recovery command:

```bash
maid plan revise <manifest> --reason "<text>" --stash-implementation
```

Use `--stash-implementation` only for review-driven behavioral contract changes
that need fresh red evidence while declared implementation changes are
temporarily hidden. For metadata-only cleanup on a locked manifest, use
`maid plan revise <manifest> --reason "<text>" --preserve-red-evidence`
instead.

## Phase 1 — Load the Manifest

Read the approved manifest and extract:

- files to create
- files to edit
- scope-only files
- read-only dependencies
- exact artifacts
- temptations and their `instead` procedures
- validation commands

If the manifest includes `temptations`, identify which entries apply to this implementation. Restate them briefly before coding so the sharp test-passing signal does not override the architectural guidance.

## Phase 2 — Load Dependencies

Read every file listed in `files.read` and the behavioral tests referenced by the manifest.

### Promoted Draft Recall

When implementation starts from a draft manifest, refresh recall before
promotion when completed Outcome records exist:

```bash
uv run maid learn
uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet
```

If `maid learn` finds no completed Outcome records, state that no advisory
history is available and continue. Use recalled lessons to sharpen test focus
and implementation risks. Recall is advisory planning context only; it does
not expand scope or replace red evidence, behavioral validation, plan lock,
implementation validation, or review.

## Outcome-Aware MAID Guidance

Outcome records are deterministic manifest data, not agent-only memory. When
the project has Outcome support, use `maid learn`, `maid recall`, and
`maid insights` as historical evidence only.

For implementation:

- Active insights trigger: review recurring Outcome lessons with `maid insights`
  before implementing the approved manifest. Treat insights as advisory
  aggregate evidence for recurring lessons, not as generated narrative authority.
- Consult recalled Outcome records when choosing focused tests and code patterns.
- Do not broaden the approved manifest scope because an older Outcome mentioned adjacent work.
- Treat `maid insights` as aggregate evidence for recurring lessons, not as
  permission to skip the current manifest contract.
- Use active recall guidance to thread the planner's recalled evidence into
  implementation decisions while staying inside the approved scope.
- To intentionally include instructive failed or abandoned Outcome lessons,
  refresh the index with this opt-in command, then recall from that index:

```bash
maid learn --include-status completed --include-status abandoned
```

  This is an intentional opt-in for failure lessons; the completed-only default
  is unchanged.
- Recalled, aggregated, and digested Outcomes are planning evidence only. They
  do not replace behavioral tests, declared scope, validation, approval, done
  gates, or review, and they do not create an approval, promotion, done, or
  review gate.

### Manifest-Derived Outcome Recall

When choosing focused tests and code patterns, consult related completed
Outcome records for the approved manifest when a learned Outcome index is
available:

```bash
maid recall --for-manifest <path>
maid recall --for-manifest <path> --plan-packet
```

If the index is stale, the stale index fails by default. The remedy is to run
`maid learn`, or pass `--allow-stale-index` only when a stale advisory read is
acceptable. If `.maid/outcomes.json` is missing, run `maid learn` once; if no
completed Outcome records exist, report that no advisory history is available
and skip recall.

Use recall to identify relevant prior lessons, but stay inside the approved
manifest scope. Recalled Outcomes are planning evidence only. They do not
replace behavioral tests, declared artifacts, validation commands, or
implementation review.

### Learning Evidence Digestion

The learning evidence digestion step is advisory evidence handling.

Close the loop between completed Outcome records and current agent decisions;
do not dump a raw recall or insights transcript into the implementation notes.
Identify applicable lessons, reject stale or irrelevant lessons with a reason,
and state what changed because of the evidence. For implementation, name the
effect on focused tests, implementation approach, or risk controls inside the
approved scope. The learning evidence digestion step is advisory evidence
handling, not a separate gate.

## Phase 3 — Implement

If the plan appears wrong, incomplete, or impossible, stop and write `plan-revision.md` instead of editing around it. Include:

- the manifest path
- the contradiction or missing context
- the file/test evidence
- the proposed manifest or test revision

For `files.create`:

- define exactly the declared public artifacts
- keep additional helpers private
- avoid undeclared public symbols

For `files.edit`:

- add or change the declared artifacts conservatively
- preserve existing behavior unless the tests require change

For `files.scope`:

- make only the narrow writable change described by the scope reason
- rely on behavioral tests for route/page wiring or other no-artifact surfaces
- do not add public artifacts to a scope-only file; stop for plan revision if
  the change becomes artifact-bearing

For `files.read`:

- treat the file as contextual and read-only for production code
- behavioral test files listed in `files.read` may be changed only when the user
  explicitly approves a contract revision
- if implementation requires changing a production `files.read` file, stop for
  plan revision and declare it in `files.edit` or `files.scope` as appropriate

### Active Task Scope Guidance

When implementing a promoted draft, run
`maid task start manifests/<slug>.manifest.yaml` after promotion and before
implementation edits so hook integrations can evaluate writes against the
active manifest. At handoff, after implementation review and Outcome capture,
run `maid task stop` to clear the pointer.

Interactive editor sessions use the default fail-open policy: no active task
and internal hook errors allow the edit. Locked-down autonomous loops should
pass `--strict` to deny those outcomes. The hook is advisory edit-time
infrastructure only. maid verify changed-scope checks remain the authoritative handoff evidence.
Hook decisions do not replace validation or add `ErrorCode` entries.

## Phase 4 — Validate Implementation

Run:

```bash
maid validate manifests/<slug>.manifest.yaml --mode implementation
```

Fix structural mismatches in code only. If the manifest itself is wrong, write `plan-revision.md` and stop.

## Phase 5 — Run Behavioral Tests

Run all `validate` commands from the manifest.

- Fix behavior in code, not in tests.
- If a test appears wrong, write `plan-revision.md` and stop.

## Phase 6 — Run Full Validation

Run:

```bash
maid validate
maid test
```

This ensures the implementation does not break other MAID contracts.

## Review-Fix Iteration Recipe

During fix iteration, run the task-scoped inner-loop gate instead of paying for
the full-tree handoff gate after every edit:

```bash
maid verify --summary --plan-lock-scope task --since <baseline>
```

Assess once with the explicit task baseline, then run the exact verify command
it prints:

```bash
maid assess --since <baseline>
```

Assessment scales between `handoff` and `deep`; its deep command retains the
plan-lock and red-evidence requirements. If assessment is unavailable or fails,
use `maid verify --profile handoff --since <baseline>` as the safety floor.

Apply ALL blocking fixes from one review round as a batch. If the contract or
locked tests changed, run one revise after the batch and one re-validation;
never revise once per finding. Run the full strict handoff verify once at the
end.

Choose evidence flags by revision shape:

- A contract-preserving plain revise automatically preserves valid evidence.
- Use `--test-only-green` for a test-only contract.
- Use `--stash-implementation` when tests were tightened after implementation;
  add `--allow-sibling-dirty` only for an intentional multi-manifest session.

## Phase 7 — Review the Implementation

Before reporting completion, run a read-only MAID implementation review using the `maid-implementation-review` skill when available. The reviewer should confirm:

- changed files stayed within manifest scope
- declared artifacts exist
- validation passed
- no implementation-phase drift or process violations were introduced

Use a fresh read-only reviewer with an explicit verdict-neutral packet containing
the task baseline, complete baseline-to-current diff, complete changed-file list,
complete manifest-declared artifact definitions and file inventory, factual validation outcomes,
environment limits, and plan-revision signal. Exclude prior review lineage and
coordinator-owned follow-up state. Do not fork the full session context into the
reviewer and do not rely on the implementation transcript; this preserves the
same independent-review pattern used by loop-style reviewer agents. Do not
require a separate per-turn reviewer approval
when the target repo, active skill, or user prompt grants standing
authorization for MAID reviewer subagents.

Treat the review verdict as a gate. Fix concrete implementation defects, rerun
focused validation, and run another implementation review. Repeat until the
latest review verdict is `Ready to merge`, or stop with `Needs changes` or
`Needs discussion` if the remaining issue requires user or plan revision input.

## Phase 8 — Report

Report changed files, validation results, reviewer verdict, and whether a
subagent reviewer was used. Only call the work ready for commit or further
integration when validation passes and the latest review verdict is ready.
