---
name: maid-incident-logger
description: Record curated MAID gaming or implementation-drift incidents as chosen/rejected examples for future review, hooks, or DPO datasets. Use when the user asks to log a MAID incident, capture a model gaming pattern, save a chosen/rejected pair, or prepare DPO training material.
---

# MAID Incident Logger

Create a human-curated incident record through MAID's deterministic incident commands. A human or agent decides that an event was a gaming attempt; MAID records and retrieves the supplied evidence deterministically. No inference, classification models, or hidden summarization are involved.

Incident records are YAML files under the repository-local `.maid/incidents/` directory. Do not hand-write incident files, invent metadata fields, or document any unshipped behavior. The skill guidance must add no new CLI behavior.

## Deterministic Incident Commands

Use only the shipped command surface:

```bash
maid incident capture --manifest <path> --packet <path> --rejected-diff <path> --tags <comma-list> [--notes <text>]
maid incident update <incident-path> --chosen-diff <path>
maid incident list [--tag <tag>] [--json]
maid incident export --format dpo --output <path>
maid incident suggest-temptations --paths <comma-list> [--json]
```

## Capture Workflow

When a contract-integrity gate catches a gaming attempt, capture the incident immediately with the failure packet and rejected diff:

```bash
maid incident capture --manifest <path> --packet <path> --rejected-diff <path> --tags <comma-list> [--notes <text>]
```

Then update the same incident after the honest fix lands by attaching the chosen diff:

```bash
maid incident update <incident-path> --chosen-diff <path>
```

Use `maid incident list [--tag <tag>] [--json]` to inspect stored records. Use `maid incident export --format dpo --output <path>` only after records have chosen diffs. Use `maid incident suggest-temptations --paths <comma-list> [--json]` to surface deterministic advisory temptation entries for future manifests.

## Pattern Tags

Use the closed pattern-tag vocabulary exactly:

- `test-weakening`
- `trivial-test`
- `stub-implementation`
- `contract-renegotiation`
- `scope-escape`
- `runner-gaming`
- `false-done`

Unknown tags are rejected as a usage error. Vocabulary changes require a manifest evolution.

## Recall Planning Link

This skill has a documentation-only cross-link to the 066 recall workflow. During planning, related completed Outcomes and incidents may be surfaced with:

```bash
maid recall --for-manifest <path>
maid recall --for-manifest <path> --plan-packet
```

Recall results and incident suggestions are advisory planning evidence. They do not replace the current manifest's behavioral tests, declared scope, validation, or implementation review, and the incident and recall implementations stay independent.

## DPO Curation Rules

Mark an incident as DPO-worthy in notes or downstream review judgment only when:

- the rejected and chosen paths solve the same immediate task
- the chosen path was visible from the model's context
- the rejected behavior is a recurring or likely recurring pattern
- the preference is about architecture or process quality, not just a typo

Do not treat every mistake as DPO-worthy. When the model lacked necessary context, the task was ambiguous, or the issue was a one-off bug, capture only the deterministic evidence needed for review.
