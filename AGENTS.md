# AGENTS.md

Project context, commands, and architecture are in `CLAUDE.md`.

## MAID Workflow

This repository uses MAID (Manifest-driven AI Development). The installed MAID skills in `.claude/skills/` and `.codex/skills/` are the authoritative workflow.

Run MAID through the repo wrapper, which needs only `uv`:

```bash
scripts/maid <command>    # wraps: uvx --from "maid-runner[all]@latest" maid
```

maid-runner is not a project dependency, so read `uv run maid ...` in the generated MAID Runner section below as `scripts/maid ...`.

Per change: `maid-planner` -> behavioral tests (red) -> `scripts/maid validate --mode behavioral` -> approval -> `scripts/maid plan lock <manifest>` -> `scripts/maid manifest promote <draft>` -> implement -> `scripts/maid validate --mode implementation` -> `scripts/maid verify --profile handoff --summary` -> implementation review -> `outcome:` + `scripts/maid learn`.

<!-- BEGIN MAID RUNNER -->
## MAID Runner

Instruction payload version: 2026.09.18.1

### MAID Codex Skills Workflow
Use the installed MAID Codex skills for manifest-driven development: `maid-planner`, `maid-plan-review`, `maid-implement-draft`, `maid-implementer`, `maid-implementation-review`, `maid-evolver`, `maid-auditor`, `maid-incident-logger`, `maid-outcome-enrich`, `maid-run-review`.

For new features, bug fixes, and refactors, plan with `maid-planner`, review with `maid-plan-review`, implement with `maid-implementer`, and review the result with `maid-implementation-review` before handoff. When continuing from `manifests/drafts/*.manifest.yaml`, use `maid-implement-draft` to harden, lock, promote, implement, review, and capture Outcome.

Before editing a file during an active MAID task, run `maid hook scope-check --path <file>` and treat exit code 2 as out-of-scope. This pre-edit hook check is advisory and does not replace `maid verify` changed-scope validation.

Before treating a file's language as unsupported, run `maid validators` and install a matching validator plugin when available instead of skipping MAID for that file.

Draft manifests under `manifests/drafts/` are planning inventory, not active contracts. Child implementation drafts live at `manifests/drafts/*.manifest.yaml`; epic planning records live at `manifests/drafts/*.epic.yaml` and use split-before-promote before implementation; archived draft records are historical inventory. Before promoting the selected child draft, refresh the Outcome index when needed and run `uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet` when completed Outcome records exist. Recall is advisory planning context only: it can inform draft hardening and implementation risks, but it does not expand scope or replace red evidence, behavioral validation, plan lock, implementation validation, or review. Use `uv run maid insights` to review recurring Outcome lessons when an index is available. To intentionally include instructive failed or abandoned Outcome lessons, refresh the index with `uv run maid learn --include-status completed --include-status abandoned`, then recall from that index; the completed-only default is unchanged. When related Outcome evidence is retrieved, do not dump a raw recall or insights transcript into the task. Digest it visibly: name applicable lessons, reject stale or irrelevant lessons with a reason, and state what changed because of the evidence for the current planning, implementation, or review phase. Recalled, aggregated, and digested Outcomes remain advisory planning context only; they do not create an approval, promotion, done, or review gate. Promote one selected child draft with `uv run maid manifest promote manifests/drafts/<slug>.manifest.yaml`. Do not manually move or copy draft manifests. For metadata-only reference cleanup on locked active manifests, use `uv run maid plan revise <manifest> --reason "<text>" --preserve-red-evidence`. For review-driven behavioral contract changes while implementation is uncommitted, use `uv run maid plan revise <manifest> --reason "<text>" --stash-implementation` so MAID temporarily hides declared implementation changes while it captures fresh red evidence. This cannot hide committed implementation. If revised tests fail for missing behavior in committed code, plain `maid plan revise` can capture fresh red evidence before the fix. If they already pass and valid evidence cannot be preserved, report the evidence blocker and the pre-implementation baseline needed for recovery; do not reset shared history or bypass evidence requirements. See 'Revision Evidence After Implementation' in `docs/draft-manifest-workflow.md`. While a draft or promoted contract belongs to the current unmerged task, revise that same contract in place; use `maid plan revise` when it is locked. A contract is durable when accepted into shared project history, including integration or release branches regardless of name; a local task commit alone is not acceptance. Check repository policy and history, and clarify uncertain acceptance before rewriting. Use new manifests for genuinely separate work or evolution of durable contracts through chain merging or `maid-evolver` supersession.

Declare each touched source file in `files.create`, `files.edit`, `files.scope`, or `files.delete`; `files.read` is context, not writable scope. When public behavior changes in a touched file, add focused behavioral or characterization tests and declare any affected public artifacts in `files.create` or `files.edit`, even if the file was previously listed only in `files.scope`. Use `files.scope` for narrow no-artifact wiring covered by behavioral tests instead of forcing a whole-file public artifact snapshot.

Always capture an Outcome record after implementation validation and implementation review, before final handoff. Capture Outcome after implementation review so the result records the reviewed evidence. Outcome capture is required for completed, partial, failed, superseded, archived, or abandoned MAID work. The Outcome must cite concrete validation evidence and review notes; it does not replace behavioral tests, declared artifacts, validation commands, or implementation review. After Outcome capture, run `uv run maid learn` to refresh the local `.maid/outcomes.json` advisory index for subsequent recall. `.maid/outcomes.json` is generated and ignored; do not commit it. If `maid learn` fails, report the refresh failure as advisory unless recall or insights are required for the current task. See `docs/draft-manifest-workflow.md` and `docs/manifest-outcome-records.md`.

Installed Codex skill-local agent metadata files: 10.
<!-- END MAID RUNNER -->
