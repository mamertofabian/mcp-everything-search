---
name: maid-implementation-review
description: Review an implementation produced from an approved MAID manifest. Confirms changed files stay within manifest scope, declared artifacts exist, validations pass, and the behavior matches the contract. Use after maid-implementer or after any MAID-backed code change before merge.
---

# MAID Implementation Review

Review MAID-backed implementation work in read-only mode. Confirm the code matches the approved contract and that validation integrity was preserved.

## Rules

- NEVER edit files.
- NEVER modify tests or manifests during review.
- When you are the coordinating reviewer, run an independent read-only reviewer
  subagent before deciding the handoff verdict whenever reviewer subagents are
  available and have not been explicitly disabled for the turn.
- Reviewer subagents must be fresh, context-minimal review agents. Never use a
  full-history fork or pass prior implementation reasoning, conclusions, or chat
  transcript unless the review explicitly depends on a user quote.
- Keep reviewer prompts verdict-neutral in every review round. Never label a
  reviewer request as final, approval, merge-readiness, blocker-closure, or
  convergence. Never state that fixes work or summarize intended behavior as
  established fact. Do not disclose prior findings, fixes, verdicts, or review-round state.
  Those convergence decisions belong only to the
  coordinator after the independent reviewer responds.
- If your prompt identifies you as the reviewer subagent, do not spawn another
  subagent. Perform the review locally and return the verdict.
- Confirm changed implementation stays within writable production file scope:
  `files.create`, `files.edit`, `files.scope`, or `files.delete`. `files.read`
  is dependency context and does not authorize production edits.
- Artifact validation applies to declarations in `files.create` and `files.edit` only;
  scope-only and deleted files do not declare public artifacts.
- Flag any implementation-phase manifest or behavioral-test edit as a process violation unless explicitly approved by the user.
- Treat concrete behavior regressions, undeclared public API drift, and missing validation as primary findings.
- Audit fidelity to the approved plan, including rationale and `temptations`; passing tests are not sufficient if the implementation took a path the manifest warned against.
- If `plan-revision.md` exists, review it as a stop signal rather than an implementation failure.

## Review Convergence Protocol

- Report every finding you can identify in a single pass. Never drip-feed one
  finding per round.
- After each independent review, the coordinator compares its findings with
  earlier verdicts. For a later finding, the coordinator records why it was not visible in round 1,
  such as being unmasked by an earlier fix, but never passes
  that comparison or review lineage into a later reviewer prompt.
- Classify every finding as **blocking** or **advisory**. Blocking findings are
  contract violations, behavioral bugs, scope drift, or validation failures.
  Advisory findings are style preferences, optional hardening, or future-work
  notes. Advisory findings MUST NOT trigger manifest or locked-test revision
  in the current session. Do not record them in the review packet for possible future draft manifests;
  keep them in a coordinator-owned follow-up log that is explicitly excluded
  from every reviewer subagent packet.
- Continue fresh review rounds after each issue-driven fix until the latest
  verdict contains no blocking or current-scope actionable findings. Do not use
  round count, including two full review rounds, as a reason to stop reviewing
  or pressure approval. Residual advisories may remain only when the reviewer
  explicitly classifies them as non-actionable for the current contract.

## Phase 1 — Identify the Active Manifest

Use the manifest path provided by the user. If none is provided, inspect recent manifests and current changed files to infer the most likely approved contract.

## Phase 2 — Build the Review Packet

Collect the context needed for an independent review:

- active manifest path and whether it was provided or inferred
- complete baseline-to-current implementation delta, including the baseline,
  changed-file list, and full diff reference
- all manifest-declared artifacts, including exact names, kinds, parent
  relationships, signatures or fields, behavioral expectations, and their
  implementation and behavioral-test files, even when unchanged in the latest
  fix iteration
- validation commands already run and their factual results
- known environment limits that prevented validation
- any `plan-revision.md` stop signal

Do not pass the full implementation transcript to the subagent. Keep the review
independent by passing only the explicit packet above. Never narrow a later
review to recent fix hunks or tell the reviewer which changes answer earlier
findings. Frame every round as a first independent review of the complete
change. Never pass the coordinator-owned follow-up log to a reviewer subagent.

## Phase 3 — Run the Reviewer Subagent

Before deciding the coordinator's handoff verdict, spawn one read-only reviewer subagent when
the environment supports subagents and they have not been explicitly disabled
for the turn:

- prefer `agent_type=explorer`
- use a fresh agent with `fork_context=false`; never set `fork_context=true` for
  an independent reviewer
- leave the model unset unless the user or local project instructions require a
  specific model
- pass the review packet explicitly
- instruct the subagent not to edit files and not to spawn further subagents
- wait for the subagent verdict before final handoff
- close the subagent thread after consuming the verdict

Do not skip the subagent because the current turn did not separately mention
subagent authorization when the target repo, active skill, or user prompt grants
standing authorization for MAID reviewer subagents. Fall back to local-only
review only when the subagent tool is technically unavailable or the user
explicitly disables subagents for that turn.

Use this prompt shape:

```text
Read-only MAID implementation review requested. Do not edit files. You are the
independent reviewer subagent; do not spawn additional subagents.

Review the current implementation as if running `/review` on the changed files,
with extra attention to the approved MAID manifest:
<manifest path>

Review packet:
- baseline: <task baseline>
- complete baseline-to-current diff: <diff reference>
- changed files: <complete changed-file list>
- manifest-declared artifact definitions: <complete declarations and parent relationships>
- manifest-declared files: <complete implementation and behavioral-test file list>
- validation results: <commands and outcomes>
- known environment limits: <limits or none>
- plan revision signal: <path or none>

Prioritize findings over summaries. Look for correctness bugs, security or
authorization gaps, privacy leaks, persistence bugs, concurrency/idempotency
failures, runtime incompatibilities, stale manifest references, weak or missing
behavioral tests, and implementation drift from the manifest contract.

Do not treat passing tests or MAID validation as proof of correctness. Inspect
the changed files, relevant call sites, nearby helpers, schema constraints, and
the manifest's declared behavior. Consider how each new public helper or API
will be called from realistic routes, handlers, CLIs, services, or tests.

Return exhaustive review output:
- Report every finding you can identify in this pass.
- Classify every finding as blocking or advisory. Blocking findings are contract violations, behavioral bugs, scope drift, or validation failures. Advisory findings are non-actionable style preferences, optional hardening, or future-work notes.
- findings first, ordered by severity within each classification
- severity labels such as P0/P1/P2 in addition to the blocking/advisory label
- file and line references
- brief impact explanation
- missing tests when they allow a bug to pass

If there are no blocking findings, say that clearly and list any residual advisories,
test gaps, or risk. End with one verdict: ready, needs changes, or needs discussion.
```

## Phase 4 — Review Scope

Compare the working tree or branch state against the manifest:

- only files declared in `files.create`, `files.edit`, `files.scope`, or
  `files.delete` were changed as production implementation files
- `files.read` production files are dependency context, not writable scope;
  flag dirty production files listed only in `files.read` and require plan
  revision to `files.scope` for no-artifact wiring or `files.edit` for public
  artifact changes
- behavioral test files listed in `files.read` may change only as part of an
  approved contract revision
- no undeclared public symbols leaked into strict files
- do not treat `maid validate --mode implementation` alone as proof that a
  dirty `files.read` production file is writable; use the manifest scope model
  and worktree/changed-scope evidence when available

## Phase 5 — Review Declared Artifacts

Artifact validation applies to declarations in `files.create` and `files.edit` only;
scope-only and deleted files do not declare public artifacts. Confirm
those declared artifacts exist with the expected names and parent
relationships. Treat implementation-validation misses as blockers.

## Phase 6 — Review Plan Fidelity

Compare implementation choices against the approved manifest:

- declared rationale was followed or explicitly justified
- `temptations` risks were not taken
- each relevant `instead` procedure was followed
- no private-state access, private-helper imports, schema loosening, or test-coupled shortcuts were introduced
- no undeclared public API was added to make tests pass

Treat a direct violation of a manifest temptation as a finding even when validation passes.

## Phase 7 — Review Behavioral Coverage

Check that the behavioral tests still exercise the approved contract and that implementation changes did not weaken validation.

## Outcome-Aware MAID Guidance

Outcome records are deterministic manifest data, not agent-only memory. Use
`maid learn`, `maid recall`, and `maid insights` as deterministic context, but
keep implementation review focused on the current manifest, tests, validation,
and changed files.

For implementation review:

- Active insights trigger: review recurring Outcome lessons with `maid insights`
  before reviewing the implementation. Treat insights as advisory aggregate
  evidence for recurring lessons, not as generated narrative authority.
- Use active recall guidance to thread the planner's and implementer's recalled
  evidence into review focus, while still grounding findings in the current
  manifest, tests, validation, and diff.
- After the review verdict is ready, check whether the completed manifest needs an `outcome:` record.
- Outcome capture happens after implementation review and before final handoff.
- Confirm new Outcome lessons cite concrete validation, review, or file evidence.
- When capturing `outcome.agent`, prefer `MAID_AGENT_MODEL` and
  `MAID_AGENT_REASONING_EFFORT` environment ground truth. Record the exact
  client-invoked model slug (including version and variant) plus
  `reasoning_effort`; use a self-reported marketing name only as a labeled
  last resort when no ground truth or exact self-known slug is available.
- Do not mark work ready if Outcome claims are not backed by validation and review evidence.
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

### Lesson Type Vocabulary Convergence

Before writing new Outcome lessons, and before coining a new lesson_type, list
the existing lesson_type vocabulary: run `maid insights` and read the
`by_lesson_type` keys. When a fresh validated theme map exists, prefer its
themes' `member_lesson_types` as the canonical families for grouping related
lessons.

Reuse an existing lesson_type when one fits the new lesson. Coin a new
lesson_type only when no existing value fits, and prefer singular,
kebab-or-plain lowercase forms consistent with the existing vocabulary.

This check is advisory and must not block or delay Outcome capture. If
insights or the index is unavailable, capture proceeds with the agent's
best-fit lesson_type and the unavailable vocabulary evidence should be noted
as advisory context only.

### MAID Runner Feedback Candidates

Adding the exact, case-sensitive `maid-runner-feedback` tag must be an explicit
per-lesson decision. Use it only for an individual lesson about generalizable
MAID Runner behavior, validation, CLI behavior, packaging, or MAID workflow.
The reviewer must not infer candidacy from lesson text, paths, error codes, or
other tags, and must not blanket-mark every MAID-adjacent lesson.

Do not mark application-specific findings or summaries containing secrets,
credentials, personal data, or proprietary details. Inspect the authored
Outcome summary before adding the marker and edit or omit unsafe details at the
source. The marker makes the lesson a local export candidate; it is not consent
to upload, submit, or publish the lesson.

### Manifest Outcome Record Check

After the review verdict is ready, check related completed Outcome records to
decide whether this completed manifest needs a new or updated Outcome record:
this Manifest-Derived Outcome Recall step is active recall guidance for review
and Outcome capture.

```bash
maid recall --for-manifest <path>
maid recall --for-manifest <path> --plan-packet
```

If the index is stale, the stale index fails by default. The remedy is to run
`maid learn`, or pass `--allow-stale-index` only when a stale advisory read is
acceptable. If `.maid/outcomes.json` is missing, run `maid learn` once; if no
completed Outcome records exist, report that no advisory history is available
and skip recall.

Use related completed Outcome records to avoid duplicate or unsupported
lessons. Outcome claims still need concrete validation and review evidence.
Recalled Outcomes are planning evidence only. They do not replace behavioral
tests, declared artifacts, validation commands, or implementation review.
After Outcome capture, run `uv run maid learn` to refresh the local `.maid/outcomes.json` advisory index for subsequent recall.
`.maid/outcomes.json` is generated and ignored; do not commit it. If `maid learn` fails, report the refresh failure as advisory unless recall or insights are required for the current task.

### Learning Evidence Digestion

The learning evidence digestion step is advisory evidence handling.

Close the loop between completed Outcome records and current agent decisions;
do not dump a raw recall or insights transcript into the review. Identify
applicable lessons, reject stale or irrelevant lessons with a reason, and state
what changed because of the evidence. For implementation review, name the
effect on review focus, Outcome capture, or candidate follow-up work. The
learning evidence digestion step is advisory evidence handling, not a separate
gate.

## Phase 8 — Run Practical Validation

Where practical, run:

```bash
maid assess --since <baseline>
maid validate manifests/<slug>.manifest.yaml --mode implementation
maid test --manifest manifests/<slug>.manifest.yaml
```

Run the exact verify command emitted by assessment. It scales between `handoff`
and `maid verify --profile deep` for high-risk changes; the deep command retains
the plan-lock and red-evidence requirements
while adding artifact-coverage and knockout checks. If assessment is unavailable
or fails, use `maid verify --profile handoff --since <baseline>` as the safety
floor.

The emitted verify command is the implementation handoff gate for the approved
plan lock and captured red-phase evidence. Treat E700-E706 plan-lock failures as
blockers unless the review
packet explicitly states that opt-in enforcement is out of scope for the task.
E700/E704/E705 requirement errors apply to manifests changed in the task window;
E701/E702/E703/E706 integrity errors are blockers regardless of task window
scope.
E708 PLAN_LOCK_SCOPE_WIDENED is a non-blocking advisory disclosure. It means
the plan-lock gate deliberately enforced manifests outside the requested task
window after changed-scope baseline resolution widened the check. Do not treat
E708 as a handoff blocker by itself; reconcile the manifests it names or rerun
with an explicit baseline when the wider scope was not intended.
Prefer `--summary` for agent and human review handoff because it keeps blocking
failures visible while deduplicating warning storms. Rerun with raw text,
`--json`, `--packet`, or SARIF only when exhaustive machine-readable detail is
needed. Treat older handoff examples such as
`maid verify --require-plan-lock --require-red-evidence --since <baseline>` as superseded unless
raw text is intentionally required.

If the environment or project shape makes a command impractical, say so explicitly.

## Phase 9 — Reconcile and Report

If the reviewer subagent reports findings, decide whether each finding is valid
against the manifest and code. Do not edit files during review. Report valid
findings first; put invalid or out-of-scope reviewer notes in a brief residual
risk or dismissed-notes section only if useful.

Prioritize:

1. blockers
2. should-fix items
3. nitpicks

Include the reviewer subagent result when one was run: subagent id or nickname,
verdict, and whether it found blockers.

End with one explicit verdict:

- `Ready to merge`
- `Needs changes`
- `Needs discussion`
