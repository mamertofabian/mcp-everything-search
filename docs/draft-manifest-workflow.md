# Draft Manifest Workflow

Draft manifests are MAID planning inventory. Promoted manifests are active
contracts.

This workflow is useful when a larger goal can be split into known,
implementation-sized pieces before the first code change starts. Instead of
tracking those pieces in free-form markdown, put each known child task in
`manifests/drafts/` as a draft manifest. The draft queue gives automation a
concrete list to work through while keeping unapproved plans out of the active
manifest chain.

## Directories

- `manifests/drafts/*.manifest.yaml`: mutable child drafts that are not active
  MAID contracts yet.
- `manifests/drafts/*.epic.yaml`: larger planning records that must be split
  before promotion. Treat these as split-before-promote inventory, not
  directly implementable contracts.
- Archived draft records: archived historical inventory outside the top-level child
  queue. Keep explicit archive metadata when a draft or epic is retained only
  for context.
- `manifests/*.manifest.yaml`: promoted, active MAID contracts.

Every child implementation draft must begin with
`# manifest-kind: implementation`. The marker makes its inactive lifecycle
explicit and prevents root validation from treating the file as a hidden active
contract. `maid manifest create --output-dir manifests/drafts` adds this marker
automatically; hand-authored drafts must include it as their first line.
Older `# draft-kind: ...` comments remain accepted for compatibility, but new
draft inventory should use `# manifest-kind: ...`.

Normal validation and test execution should target promoted manifests in
`manifests/`. Draft validation is focused on plan quality before promotion.
Early inventory drafts may reference planned test files that do not exist yet;
that makes them not promotion-ready, but it is not by itself a planning defect.

## Lifecycle

1. Define the larger goal in an issue, spec, roadmap, or epic draft.
2. Split the known work into child draft manifests under `manifests/drafts/`.
3. Refresh the Outcome index when needed and run
   `uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet`
   for the selected child draft when completed Outcome records exist.
4. Review and refine each draft until its scope, declared artifacts, planned or
   actual behavioral tests, validation command, dependencies, and temptations
   are coherent.
5. Promote one implementation-sized draft with
   `uv run maid manifest promote manifests/drafts/<slug>.manifest.yaml`.
   Do not manually move or copy draft manifests; the command migrates the
   promoted manifest's plan lock, red evidence, and self-referencing validate
   paths.
6. Implement strictly inside the promoted manifest's declared file scope.
7. Validate the promoted path, run the declared tests, run the changed-scope
   handoff gate, and review the implementation against the manifest.
8. Capture Outcome after implementation review and before final handoff when
   the schema is available. Outcome records are completion metadata documented
   in `docs/manifest-outcome-records.md`; they do not replace behavioral tests,
   declared artifacts, validation commands, or review.
9. Commit only after the manifest, implementation, validation evidence, review,
   and Outcome capture are ready.
10. Re-scan `manifests/drafts/` for the next child draft.

Downstream repos that ran `maid init` can use `maid-implement-draft` to resume
from a child draft: harden tests, lock, promote, implement, review, and capture
Outcome. Already-promoted contracts with no contract change stay on
`maid-implementer`; contract changes use `maid plan revise` while still part
of the current unmerged task, before acceptance into shared project history.

Unlocked drafts may be edited before promotion. Do not silently rewrite a locked
draft or promoted contract: use `maid plan revise` for the current unmerged
task, and use normal MAID evolution for durable contracts accepted into shared
project history, regardless of branch name. For
metadata-only reference cleanup on locked active manifests, use
`uv run maid plan revise <manifest> --reason "<text>" --preserve-red-evidence`
so valid red evidence remains attached to the revised contract.
If review changes behavioral tests while implementation is still uncommitted, use
`uv run maid plan revise <manifest> --reason "<text>" --stash-implementation`
instead so MAID temporarily removes only declared implementation changes,
while the revised behavioral tests stay in place for fresh red evidence
capture. This does not remove committed implementation; follow
[Revision Evidence After Implementation](#revision-evidence-after-implementation)
when implementation has already been committed. For legacy contracted plans
that listed non-test wiring under
`files.read`, stash-backed revision can hide those paths during recovery, but
`files.read` does not authorize production edits. Move such paths to
`files.scope` for narrow no-artifact wiring or `files.edit` for changed public
artifacts before implementation continues. Undeclared dirty paths still fail
closed. Scope-only manifests also reject separate dirty `files.read` context
paths. A scope-only contract with a non-test writable scope path may also
stash explicitly declared `files.read` epic inventory at
`manifests/drafts/*.epic.yaml`. Those planning changes are hidden during red
capture and restored afterward, including untracked epics. This exception does
not admit ordinary read-only source context or authorize production edits.

Recall is advisory planning context only. It can inform selected-draft
hardening, test focus, and implementation risks, but it does not expand the
draft scope or replace red evidence, behavioral validation, plan lock,
implementation validation, or review.

## Learning Evidence Digestion

Completed Outcome records should close the loop between prior MAID work and
current agent decisions. When selected-draft recall, plan packets, or
`uv run maid insights` return related Outcome evidence, do not paste a raw
recall or insights transcript into the plan or handoff. Digest it visibly:
identify applicable lessons, reject stale or irrelevant lessons with a reason,
and state what changed because of the evidence.

The influence should be phase-specific. During draft hardening, name any effect
on manifest scope, behavioral tests, temptations, or open questions. During
implementation, name the effect on focused tests, implementation approach, or
implementation risks while staying inside the approved scope. During review,
name the effect on review focus, Outcome capture, or candidate follow-up work.

To intentionally learn from failed or abandoned Outcome lessons, refresh the
index with
`uv run maid learn --include-status completed --include-status abandoned` and
then recall from that index. The completed-only default remains unchanged.
Recalled, aggregated, and digested Outcomes are advisory planning context only:
they do not expand scope, and the evidence does not replace red evidence,
behavioral validation, plan lock, implementation validation, or review. They do
not create an approval, promotion, done, or review gate.

## When To Pre-Create Drafts

Pre-create drafts when the work can be enumerated with reasonable confidence:

- parser replacement phases;
- CLI automation follow-ups;
- multi-file features with obvious child boundaries;
- remediation batches discovered during audit or review.

Do not force a complete draft set when discovery is still the main task. It is
valid to start with a small queue and add more draft manifests as gaps become
visible.

## Promotion Criteria

A child draft is ready to promote when:

- it is implementation-sized and not an epic;
- its file scope is narrow and explicit;
- every declared public artifact has the intended kind, owner, signature, and
  type information;
- behavioral tests exist for the declared production artifacts, unless the
  draft is explicitly characterization-only;
- the red phase fails for the intended reason before implementation;
- `maid validate manifests/drafts/<slug>.manifest.yaml --mode behavioral`
  passes;
- dependencies on earlier drafts are clear and ordered.

If a draft fails these checks, refine the draft before promotion.

Do not apply the promotion checklist to every draft in the queue. For an
inventory draft, schema validation and coherent scope may be enough to keep it
as a future work item. For the draft selected for implementation, the first
work is to create or refine the behavioral tests, confirm the red phase, pass
behavioral validation against the draft path, run
`uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet`
when completed Outcome records exist, then promote it to `manifests/`.

## Plan Locks at Promotion

`maid manifest promote` migrates the promoted manifest's plan lock so
promotion never strands tamper evidence. Use
`uv run maid manifest promote manifests/drafts/<slug>.manifest.yaml`; do not
manually move or copy draft manifests. When
`.maid/plan-locks/<slug>.lock.json` exists and records the draft being
promoted, promote:

- rewrites self-referencing validate-command paths in the manifest from the
  drafts/ path to the promoted path (this happens for unlocked drafts too);
- re-locks the promoted manifest through the sanctioned revision path: the
  prior hashes are preserved in the lock's revision history and the revision
  reason records the promotion;
- preserves valid red-phase evidence when the locked contract, validate-command
  strings, and behavioral test hashes are unchanged. Otherwise it
  recaptures evidence when the locked contract or tests changed; pass `--no-run` to skip
  that fallback capture and record null evidence. A self-referencing validate
  path rewritten from drafts/ to manifests/ changes the command identity and is
  therefore recaptured rather than preserved. Evidence handling is lock-gated:
  promoting an unlocked draft never runs validate commands;
- resolves the lock directory from `--project-root` (default `.`), mirroring
  the `maid plan` subcommands.

Promotion fails closed: a lock that exists but is unreadable, or that records
a different manifest path, aborts the promotion with exit code 2 and leaves
the draft and the lock untouched. If lock migration fails mid-promotion, the
promoted file is removed and the draft is kept.

Promote does not edit other manifests. When another active manifest still
references the promoted draft path (for example in `files.read`), promote
prints a warning naming it; update that reference and run `maid plan revise`
for its lock, since silently rewriting a locked manifest would defeat tamper
evidence.

## From-Diff Authoring Loop

`maid manifest from-diff` creates a draft manifest from an implemented change so
the author can review and correct a generated contract. Code the change, then
run the command with exactly one baseline option:

```bash
maid manifest from-diff --since <commit>
maid manifest from-diff --base-ref <ref>
maid manifest from-diff --worktree
```

Supplying zero baseline options or more than one baseline option exits with code
2 and a baseline-required message that follows the `E115` fail-closed rule. MAID
does not guess `main`, `dev`, or a remote branch.

The command writes deterministic, schema-valid drafts under
`manifests/drafts/<slug>.manifest.yaml`. The default slug is
`from-diff-<UTC-date>-<short-commit-hash>`, and callers can use `--slug`,
`--output`, `--force`, `--dry-run`, and `--json`. `--force` is required to
overwrite an existing draft. `--output` must name a path under
`manifests/drafts/` ending in `.yaml` or `.yml`; the command writes YAML only,
so any other suffix — including `.json` — exits 2 without writing anything,
rather than producing a draft MAID cannot load back.

A generated draft starts with the goal placeholder
`"TODO: describe this change"` plus these markers:

```yaml
metadata:
  generated_by: maid-manifest-from-diff
  needs_review: true
```

Generated drafts are not active contracts and do not self-promote. They remain
in `manifests/drafts/` until the author reviews them, replaces the goal
placeholder, fills any placeholder artifacts, clears `needs_review: true`, and
satisfies the promotion criteria above. The `metadata.needs_review: true`
marker means the draft is not promotable yet. Artifacts whose exact types are
not known omit the unknown fields instead of guessing.

Generated drafts suggest pytest commands only for test files that exist and
currently reference at least one changed artifact. Without that evidence, the
draft's `validate:` list contains only:

```bash
maid validate <draft-path> --mode schema --quiet
```

## Outcome Capture

Outcome records close a promoted implementation session after implementation
review and before final handoff. Add or update the manifest's optional
`outcome` section only after the implementation result, validation evidence,
and review notes are known.

The canonical Outcome guide is
[`docs/manifest-outcome-records.md`](manifest-outcome-records.md). Outcome is
completion metadata; it does not loosen manifest scope, replace declared
artifacts, substitute for behavioral tests, skip validation commands, or bypass
implementation review.

## Automation

The local loop scripts treat `manifests/drafts/*.manifest.yaml` as the work
queue and ignore epic drafts:

```bash
npm run maid:codex-loop -- --once
npm run maid:claude-loop -- --once
```

The outer loop owns pass granularity. By default, one selected draft is handed
to a fresh agent session. Use the loop script's explicit batch option only when
several selected drafts are intentionally safe to implement in one pass.

Each ready pass should include the promoted manifest, implementation changes,
test changes, validation evidence, and an implementation review verdict. The
loop must not treat one previous approval as permission to commit future
passes.

### Handoff Scope Gate

`maid verify` runs changed-scope by default, but the task baseline must still
be explicit. Every ready implementation pass should run it before review or
commit so already-committed task changes cannot be hidden by moving a production
file from `files.edit` to `files.read`.

Use one of these forms:

```bash
maid verify --base-ref <parent-branch>
maid verify --since <task-start-commit>
```

`--base-ref` compares from `git merge-base <parent-branch> HEAD` to the current
working tree, which is the usual choice for stacked branches. `--since` compares
from the exact commit-ish supplied by the caller. A manifest may also declare
`metadata.maid_task_base`, but all active manifests that declare it must agree.

If no baseline can be resolved, MAID fails with `E115`; it does not guess
`main`, `master`, `dev`, `development`, or a remote branch. Git does not retain
a reliable branch-origin fact after rebases and merges, and a default commit
count can miss task changes. Use `--include-tests` when changed tests should be
scope-checked too. Use `--no-changed-scope` only for intentionally non-handoff
verification runs.

### Review-fix iteration cost

Keep review rounds convergent and task-scoped:

- Reviewers report every finding they can identify in a single pass and
  classify each as **blocking** or **advisory**. Blocking findings are contract
  violations, behavioral bugs, scope drift, or validation failures. Advisory
  findings are style, optional hardening, or future-work notes and MUST NOT
  trigger manifest or locked-test revision in the current session. Do not record them in the review packet for possible future draft manifests;
  keep them in a coordinator-owned follow-up log that is explicitly excluded
  from every reviewer subagent packet.
- After each independent review, the coordinator compares findings with earlier
  verdicts. If a finding was not visible in round 1, the coordinator records
  why, such as being unmasked by an earlier fix, without passing that comparison
  or review lineage into a later reviewer prompt. Keep every reviewer prompt
  verdict-neutral in every review round: pass the complete baseline-to-current implementation delta,
  all manifest-declared artifacts, factual validation
  outcomes, environment limits, and the plan-revision signal. Do not disclose
  prior findings, fixes, verdicts, or review-round state, and never frame a
  reviewer request as final, approval, or confirmation that fixes work.
- Continue fresh review rounds after each issue-driven fix until the
  latest verdict contains no blocking or current-scope actionable findings.
  Do not use round count, including two full review rounds, as a stopping rule.
  The coordinator decides convergence only after receiving the independent
  verdict; a residual advisory may remain only when the reviewer explicitly
  classifies it as non-actionable for the current contract.
- Apply all blocking fixes from one round as a batch. If the contract or locked
  tests changed, run one revise after the batch and one re-validation rather
  than revising once per finding.
- During fix iteration, run
  `maid verify --summary --plan-lock-scope task --since <baseline>`. Run the
  full strict handoff verify once at the end with
  `maid verify --profile handoff --since <baseline>`.

For revision evidence, a contract-preserving plain revise automatically
preserves valid evidence. Use `--test-only-green` for test-only contracts. Use
`--stash-implementation` when tests were tightened after uncommitted
implementation, with `--allow-sibling-dirty` only for an intentional
multi-manifest session. For committed implementation, use the decision path below.

## Revision Evidence After Implementation

Contract acceptance and evidence recovery are separate decisions. A commit on
an unfinished task branch does not by itself make its contract durable, but
`--stash-implementation` only hides dirty implementation paths, not commits.
Even a partly uncommitted implementation can leave the revised tests green
after stashing if the behavior they exercise is already in `HEAD`.

- For a contract-preserving revision, plain
  `maid plan revise <manifest> --reason "<text>"` automatically preserves
  valid evidence when MAID determines it is compatible. Use
  `--preserve-red-evidence` for metadata-only cleanup, not changed behavioral
  tests or commands.
- If revised tests expose missing behavior in the current committed code,
  run plain `maid plan revise <manifest> --reason "<text>"` before fixing it
  to capture fresh red evidence. Confirm the failure is the intended behavior
  failure, not an environment or dependency error.
- If the relevant implementation is uncommitted, use
  `maid plan revise <manifest> --reason "<text>" --stash-implementation`.
  Confirm it captures valid red evidence and restores the implementation;
  an unmerged branch alone does not establish those conditions.
- If revised tests already pass against committed implementation and valid
  evidence cannot be preserved, stop before implementation or handoff and
  report the manifest, changed tests, current commit, and the verified
  pre-implementation commit needed for recovery (or state that it is unknown).
  Baseline recovery needs a separately verified procedure in an isolated
  worktree that retains the revised tests, demonstrates the intended red
  failure, and validates the resulting lock and restored implementation.
  The stash command does not perform that recovery. Do not reset shared
  history, weaken tests, hand-edit lock evidence, or use `--no-run`,
  `--test-only-green`, or legacy-baseline adoption to bypass a changed
  implementation contract's red requirement. A diagnostic baseline test run
  alone is not a valid replacement plan lock.

## Evolution During Implementation

Implementation will expose gaps sometimes. Handle them based on whether the
affected contract belongs to the current unmerged task or is durable history:

Determine acceptance from repository policy and history, not branch spelling.
A contract accepted into an integration branch such as `develop` or
`release/v2.next`, a release, or another shared project baseline is durable
even before it reaches the default branch. A local commit in the current
unfinished task alone is not acceptance. If acceptance is unclear, clarify
it before rewriting the contract.

- Before promotion: edit an unlocked draft and rerun behavioral validation. For
  a locked draft, use `maid plan revise` so the lock and red evidence stay valid.
- After promotion, while the contract still belongs to the current unfinished
  task and has not been accepted into shared project history:
  revise the same promoted manifest with `maid plan revise`, then review the
  revised behavioral contract and confirm its updated lock. Do not create a
  follow-on or superseding manifest just to revise this unmerged task.
- For a durable contract in accepted shared history, an additive change needs
  a new manifest that adds the artifact or file; chain merging combines the active
  contracts. A breaking change needs a superseding manifest that declares the
  complete replacement contract.
- If a selected draft depends on unimplemented work, stop the pass as blocked
  or add/refine the prerequisite draft rather than implementing outside scope.

The goal is not to predict every implementation detail upfront. The goal is to
make the known plan enumerable, reviewable, and machine-checkable before each
piece becomes an active MAID contract.
