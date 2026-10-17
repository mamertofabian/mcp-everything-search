---
name: maid-plan-review
description: "Review a MAID manifest and its behavioral tests before implementation. Verifies the plan is complete, scoped correctly, and the tests form a genuine behavioral contract. Use after maid-planner produces a manifest and before implementation starts. Triggers: review the manifest, review the plan, check the manifest, is this plan ready, maid plan review."
---

# MAID Plan Review

Review a manifest and its behavioral tests before implementation begins. This is the quality gate between planning and coding.

Distinguish draft inventory from an implementation-ready contract. Drafts under
`manifests/drafts/` may exist before behavioral test files are created. Missing
planned tests, pytest "file not found", or `E200` means the draft is not ready
to promote or implement yet; it is not automatically a defect in inventory
planning. Apply the behavioral-test and red-phase gates only when reviewing a
manifest for approval, promotion, or immediate implementation.

## Rules

- NEVER modify the manifest or tests during review.
- NEVER proceed to implementation if blockers are found.
- ALWAYS confirm the red phase.
- Judge the plan, not the idea.
- Treat missing explicit signatures and missing field types as blockers.
- Treat `E200` behavioral misses as blockers only for manifests presented as
  approval-ready, promotion-ready, or implementation-ready.
- Treat missing rationale for important design choices as a revision item.
- Treat generic, missing, or unpaired `temptations` as blockers when the task has obvious implementation shortcuts.

## Phase 1 — Locate the Manifest

Use the path provided by the user. If none is provided, inspect recent `manifests/*.manifest.yaml` files and pick the most likely draft. Ask only if the choice is ambiguous.

## Phase 2 — Structural Review

Check:

- schema version
- specific goal
- manifest type
- created date
- adequate description
- valid `files.create`, `files.edit`, `files.read`, and `validate` sections
- lean task-specific `temptations` when implementation gaming is plausible
- sensible paths and dependency coverage

## Phase 3 — Scope Review

Flag manifests that are too broad, too narrow, or missing critical read dependencies.

For current MAID manifests, distinguish contracted, scope-only, and contextual
files:

- `files.create` and `files.edit` are the public artifact contract.
- `files.scope` is writable implementation scope for files that need narrow
  no-artifact changes, such as route/page wiring covered by behavioral tests.
- `files.read` is dependency context and must not be used to authorize
  production edits. Test files may appear in `files.read` as behavioral
  contract inputs, but production call-site rewiring belongs in `files.scope`
  or `files.edit`.
- Require an intentional production edit to move from `files.read` to
  `files.scope` when the file has no stable public artifact contract, or to
  `files.edit` when the task changes/contracts public artifacts.
- Be wary of forcing large existing public classes into `files.edit`; MAID may
  then require declarations for the class's full public surface, expanding the
  manifest beyond the behavioral contract. Use `files.scope` for narrow
  no-artifact wiring instead.

## Phase 4 — Artifact Quality Review

Confirm:

- public API only
- exact names
- methods/functions include `args` and `returns`
- zero-arg methods/functions use `args: []`
- attributes include `of` and `type`
- type aliases include explicit `type`
- every declared symbol is necessary and complete

## Phase 5 — Test Quality Review

Read the behavioral tests and check:

- behavioral purity
- no private-state or private-helper access unless the public contract explicitly exposes it
- happy path coverage
- edge-case coverage
- failure-mode coverage
- exact symbol references for every declared production artifact

## Phase 5.5 — Adversarial Review

Review the manifest and tests as if trying to make them pass with the lowest-quality implementation. Flag:

- risks named without a concrete `instead`
- broad assertions that allow hollow code
- schema or type looseness that can hide bad behavior
- tests coupled to internals rather than public behavior
- missing rationale that leaves the implementer guessing

Require revisions until the clean implementation path is explicit.

## Outcome-Aware MAID Guidance

Outcome records are deterministic manifest data, not agent-only memory. When
the project has Outcome support, `maid learn`, `maid recall`, and
`maid insights` provide explicit evidence that can inform review questions.

For plan review:

- Active insights trigger: review recurring Outcome lessons with `maid insights`
  before reviewing an implementation-ready plan. Treat insights as advisory
  aggregate evidence for recurring lessons, not as generated narrative authority.
- Use active recall guidance to inspect related completed Outcome records when
  the planner had a learned index, the user requested outcome-aware planning,
  or the review needs to check whether earlier lessons affect scope, tests,
  rationale, or temptations.
- Check whether the draft used relevant recalled Outcome evidence when the
  planner had a learned index or the user requested outcome-aware planning.
- Missing relevant Outcome recall is a review question, not automatic rejection;
  decide whether the omission weakens scope, tests, rationale, or temptations.
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

Before approving or rejecting an implementation-ready plan, consult related
completed Outcome records when a learned Outcome index is available:

```bash
maid recall --for-manifest <path>
maid recall --for-manifest <path> --plan-packet
```

If the index is stale, the stale index fails by default. The remedy is to run
`maid learn`, or pass `--allow-stale-index` only when a stale advisory read is
acceptable. If `.maid/outcomes.json` is missing, run `maid learn` once; if no
completed Outcome records exist, report that no advisory history is available
and skip recall.

### Learning Evidence Digestion

The learning evidence digestion step is advisory evidence handling.

Close the loop between completed Outcome records and current agent decisions;
do not dump a raw recall or insights transcript into the review. Identify
applicable lessons, reject stale or irrelevant lessons with a reason, and state
what changed because of the evidence. For plan review, name the effect on
review findings, approval questions, or requested revisions. The learning
evidence digestion step is advisory evidence handling, not a separate gate.

## Phase 6 — Behavioral Validation

Run:

```bash
maid validate manifests/<slug>.manifest.yaml --mode behavioral
```

Any `E200 Artifact '<name>' not used in any test file` result is a blocker for
approval, promotion, or immediate implementation. For draft inventory, report it
as "not promotion-ready yet" rather than rejecting the draft's existence.

## Phase 7 — Confirm Red Phase

Run the manifest validation commands before implementation. The tests must fail
for the intended reason. If a draft only references planned test files that do
not exist yet, note that red-phase confirmation still needs to happen as the
first promotion/implementation step.

## Phase 8 — Verdict

End with one explicit verdict:

- `Approved`
- `Needs revision`
- `Rejected`

Keep findings concise and actionable.
