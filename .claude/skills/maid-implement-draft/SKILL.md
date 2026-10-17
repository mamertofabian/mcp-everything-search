---
name: maid-implement-draft
description: Implement a MAID draft manifest through the remaining workflow phases. Use when the user asks to implement manifests/drafts/*.manifest.yaml, continue from a planner handoff packet, or invoke maid-implement-draft. Hardens tests, captures red evidence, plan-reviews, locks, promotes, then delegates to maid-implementer and maid-implementation-review before Outcome capture.
---

# MAID Implement Draft

Continue a draft under `manifests/drafts/` through contract hardening, promotion,
implementation, review, and Outcome capture. This skill coordinates existing phase skills; it does not replace them.

## When To Use This Skill

- The starting point is `manifests/drafts/<slug>.manifest.yaml`.
- A planner handoff packet named this skill as the receiving agent.

If the contract is already promoted at `manifests/<slug>.manifest.yaml`, use `maid-implementer` instead.

## Skill Coordination

- Use `maid-plan-review` before lock and promotion.
- Use `maid-implementer` for manifest-scoped implementation after promotion.
- Use `maid-implementation-review` before final handoff.
- Use `maid-evolver` if an already-promoted contract must change; do not
  silently rewrite the locked draft after promotion.

## Workflow

1. Read repository instructions (`AGENTS.md`, `CLAUDE.md` when present).
2. Inspect the selected draft, related epic or planning files, declared tests,
   and artifacts. If the message has no path, inspect likely
   `manifests/drafts/*.manifest.yaml` candidates and ask only when more than
   one plausible target exists. Ignore `*.epic.yaml`.
3. Recall related Outcomes before creating or tightening tests:

   ```bash
   maid learn
   maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet
   maid insights
   ```

   If no completed Outcome records exist, say so and continue. Digest visibly:
   name applicable lessons, reject irrelevant ones with a reason, and state
   what changed. Recall does not expand scope or replace red evidence,
   behavioral validation, plan lock, implementation validation, or review.
4. Write or update focused behavioral tests before changing implementation
   code. Confirm the red phase fails for the intended reason. Do not create after-the-fact red evidence after implementation is already green.
5. Run `maid validate manifests/drafts/<slug>.manifest.yaml --mode behavioral`.
6. Run `maid-plan-review`. Stop for user approval when the contract is not
   already approved.
7. Lock the draft, then promote. Never manually move or copy draft manifests:

   ```bash
   maid plan lock manifests/drafts/<slug>.manifest.yaml
   maid manifest promote manifests/drafts/<slug>.manifest.yaml
   ```

   If the lock is missing after implementation has begun or tests are already
   green, stop and report a workflow gap.
8. After promotion and before implementation edits:

   ```bash
   maid task start manifests/<slug>.manifest.yaml
   ```

9. Implement with `maid-implementer` inside the promoted scope.
10. Assess from the task baseline and run the printed verify command:

    ```bash
    maid assess --since <baseline>
    ```

    If assessment is unavailable, use
    `maid verify --profile handoff --since <baseline>`. Prefer `--summary` for
    handoff. Treat plan-lock and red-evidence failures as workflow blockers.
11. Run `maid-implementation-review` with a verdict-neutral packet. If
    subagents are unavailable, perform an explicit self-review using the same
    stance. Do not report ready while review or Outcome is missing.
12. Capture `outcome:` after review, then `maid learn`. Then `maid task stop`.

## Operating Preferences

- Do not commit or push unless the user explicitly approves that exact git
  action.
- Do not weaken tests or rewrite the manifest to silence failures.
- Keep Claude and Codex procedure identical; tool-specific reviewer mechanics
  live in `maid-implementation-review`.
