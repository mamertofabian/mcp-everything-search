---
name: maid-evolver
description: Evolve an existing MAID manifest contract intentionally. Handles signature changes, renames, removals, and splits. Determines whether chain merging suffices or superseding is required. Use when you need to change something that a prior manifest already declared.
---

# MAID Evolver Skill

## Rules

- NEVER silently rewrite a locked manifest. For a contract in the current
  unmerged task, revise the existing draft or promoted manifest in place; use
  `maid plan revise` for a locked plan so its lock and red evidence remain valid.
- Treat a contract accepted into shared project history as durable, regardless
  of branch name (including integration and release branches). Intentional
  changes to a durable contract require a new manifest; do not create follow-on
  or superseding manifests just to revise unmerged work.
- ALWAYS choose the least disruptive evolution strategy (chain merge before supersede).
- ALWAYS validate that the evolution does not break dependent manifests.
- ALWAYS update behavioral tests to match the new contract.

---

## The Core Question

First check repository policy and history to determine whether the affected
manifest belongs to the current unmerged task or is already accepted shared
history. A local task commit alone does not make the contract durable; a
contract accepted from an earlier task is not mutable just because it has not
reached the default branch. If acceptance is unclear, clarify it before rewriting.
For the current task's unaccepted contract, revise it in place. For a locked
plan, run `maid plan revise <manifest> --reason "<text>"`; choose the evidence-preserving or
stash-backed option appropriate to the change. Review the revised contract and
confirm the updated lock before implementation continues.

`--stash-implementation` hides uncommitted implementation changes only; it
cannot remove implementation already committed on a task branch. If revised
tests expose missing behavior in committed code, plain `maid plan revise` can
capture that failure before the fix. If they already pass and the revision
cannot preserve valid evidence, stop and report the evidence blocker with the
pre-implementation baseline needed for recovery. Do not reset shared history,
weaken tests, or bypass evidence requirements. See
`docs/draft-manifest-workflow.md`, "Revision Evidence After Implementation",
for the evidence decision path.

The two evolution paths below apply to durable contracts in accepted shared history:

```
Does the change ADD to the contract, or ALTER it?
  ├─ ADD (new artifact, new file) → Chain merge (no supersede)
  └─ ALTER (rename, remove, change signature) → Supersede (replace contract)
```

This skill determines which path applies and executes it correctly.

---

## Phase 1 — Identify the Change

### Locate the Affected Manifest

```bash
# Find which manifest(s) declare the artifact you want to change
maid manifests <file-path>
```

Read the affected manifest(s) to understand the current contract.

### Classify the Change

| Change | Example | Path |
|--------|---------|------|
| **Add artifact** | New method `verify(token)` | Chain merge |
| **Add file** | New module `auth/middleware.py` | Chain merge |
| **Add arg (optional)** | `login(user, pass)` → `login(user, pass, mfa=None)` | Chain merge (if backward compatible) |
| **Change signature (breaking)** | `login(user, pass)` → `authenticate(credentials)` | Supersede |
| **Rename** | `Token` → `Session` | Supersede |
| **Remove artifact** | Delete `refresh()` | Supersede |
| **Move artifact** | Method moves from `AuthService` to `SessionManager` | Supersede |
| **Change return type** | `-> Token` → `-> Session` | Supersede |
| **Split class** | `AuthService` → `AuthHandler` + `TokenManager` | Supersede |

### Decision Rule

**If an old artifact in a durable contract must stop existing, you MUST
supersede.** Chain merging is additive only — it combines artifacts from all
active manifests. It cannot remove or rename. For the current unmerged task,
revise the existing contract instead.

---

## Phase 2A — Chain Merge Path (Additive Changes)

Use this when the change **adds** to a durable contract without removing anything.

### Steps

1. **Create a new manifest** with `files.edit` for the affected file(s).
2. **Declare only the new artifacts** — chain merging combines them with the existing manifest.
3. **Do NOT use `supersedes`.**
4. **Write behavioral tests** for the new artifacts.
5. **Validate:**

```bash
maid validate manifests/<new-slug>.manifest.yaml --mode behavioral
maid validate manifests/<new-slug>.manifest.yaml --mode implementation
maid validate              # Full codebase — ensures no conflicts
```

### Example: Adding a Method

```yaml
schema: "2"
goal: "Add token refresh validation to AuthService"
type: feature
created: "2026-04-24"

files:
  edit:
    - path: src/auth/service.py
      artifacts:
        - kind: method
          name: validate_refresh
          of: AuthService
          args:
            - name: token
              type: str
          returns: bool
  read:
    - tests/auth/test_service.py

validate:
  - pytest tests/auth/test_service.py -v
```

Chain merging combines this with the original `add-auth.manifest.yaml`:
- Original: `login`, `logout`
- New: `validate_refresh`
- Merged: `login`, `logout`, `validate_refresh` ✅

---

## Phase 2B — Supersede Path (Breaking Changes)

Use this when the change **alters or removes** artifacts from a durable contract.

### Steps

1. **Create a new manifest** that declares the COMPLETE new contract for the affected file(s).
2. **Set `supersedes`** to the manifest(s) being replaced.
3. **Declare ALL current artifacts** (old ones that remain + new ones + modified ones).
4. **Write behavioral tests** for the complete new contract.
5. **Remove or update old behavioral tests** that reference the superseded contract.
6. **Validate:**

```bash
maid validate manifests/<new-slug>.manifest.yaml --mode behavioral
maid validate manifests/<new-slug>.manifest.yaml --mode implementation
maid validate              # Full codebase — ensures no conflicts
maid test                  # All tests — old superseded tests should not run
```

### Example: Renaming a Method

```yaml
schema: "2"
goal: "Rename AuthService.login to authenticate with credentials object"
type: refactor
created: "2026-04-24"
supersedes:
  - add-auth.manifest.yaml

files:
  edit:
    - path: src/auth/service.py
      artifacts:
        # All current artifacts (complete state after change)
        - kind: method
          name: authenticate          # renamed from login
          of: AuthService
          args:
            - name: credentials
              type: Credentials
          returns: Session            # changed from Token
        - kind: method
          name: logout                # unchanged, but must be declared
          of: AuthService
          args:
            - name: session
              type: Session
          returns: bool
  read:
    - tests/auth/test_service.py

validate:
  - pytest tests/auth/test_service.py -v
```

### Why the Complete Declaration Is Required

When you supersede `add-auth.manifest.yaml`, it is completely excluded from validation. The new manifest is the sole source of truth for that file. It must declare everything that should exist.

**This is the transition pattern from snapshot to natural evolution:**
- The superseding manifest is comprehensive (lists ALL current artifacts)
- Future manifests can be incremental (chain merging picks up from here)

### Impact on Tests

**Critical:** When a manifest is superseded, its `validate` commands stop running. You MUST ensure the new manifest's `validate` commands cover all the behavioral tests.

```
Before:
  add-auth.manifest.yaml → pytest tests/auth/test_service.py -v  (RUNS)

After supersede:
  add-auth.manifest.yaml → pytest tests/auth/test_service.py -v  (SKIPPED)
  rename-auth-login.manifest.yaml → pytest tests/auth/test_service.py -v  (RUNS)
```

The test file may be the same, but the `validate` command in the NEW manifest is what triggers it.

---

## Phase 3 — Check Dependent Manifests

Before finalizing the evolution, check if other manifests depend on the changed artifacts:

```bash
# Find all manifests that reference the affected file
maid manifests <file-path>

# Check coherence for cross-manifest issues
maid coherence
```

### Common Dependency Issues

| Issue | Fix |
|-------|-----|
| Another manifest imports the old method name | Update that manifest (supersede it too) |
| Coherence check finds signature mismatch | Align all references to new signature |
| Test file in another manifest references old artifact | Update the test and the manifest's validate command |

### Order of Supersede

If multiple manifests need superseding, do them in dependency order:
1. Supersede the leaf manifest first (the one being changed)
2. Then supersede dependent manifests (the ones that reference it)
3. Validate after each step

---

## Phase 4 — Validate the Evolution

Run the complete validation suite:

```bash
# 1. New manifest validates structurally
maid validate manifests/<new-slug>.manifest.yaml --mode implementation

# 2. New manifest validates behaviorally
maid validate manifests/<new-slug>.manifest.yaml --mode behavioral

# 3. Behavioral tests pass
maid test --manifest manifests/<new-slug>.manifest.yaml

# 4. Full codebase validates (chain merging works correctly)
maid validate

# 5. All tests pass (superseded tests should not run)
maid test

# 6. Coherence is clean
maid coherence
```

### Expected Results After Supersede

```
Validation Results: 60 manifests
  Passed: 58
  Failed: 0
  Skipped: 2 (superseded)    ← includes the old manifest
```

The superseded manifest should appear in "Skipped" — not "Failed." If it appears in "Failed," the supersede is not recognized (check the slug spelling in `supersedes`).

---

## Phase 5 — Report

Present the evolution summary to the user:

```
## Contract Evolution: manifests/<new-slug>.manifest.yaml

**Goal:** <goal text>
**Type:** <feature|fix|refactor>
**Path:** <chain merge | supersede>

### Changes
- Superseded: <old manifest slug>
- Artifacts added: <list>
- Artifacts removed: <list>
- Artifacts modified: <list>
- Artifacts unchanged: <list>

### Impact
- Tests updated: <test files>
- Dependent manifests: <list or "none">

### Validation
✅ Structural: all artifacts defined
✅ Behavioral: all tests passing
✅ Integration: all manifests valid
✅ Coherence: no violations
```

---

## Quick Reference

### Chain Merge vs. Supersede

| | Chain Merge | Supersede |
|--|-------------|-----------|
| **When** | Adding new artifacts | Changing/removing existing artifacts |
| **Old manifest** | Stays active | Becomes superseded (archived) |
| **Old tests** | Keep running | Stop running (new manifest must cover them) |
| **New manifest declares** | Only new artifacts | ALL current artifacts |
| **Regression detection** | Both manifests active | Only new manifest active |
| **Friction** | Low | Higher (must list everything) |

### Evolution Decision Tree

```
Need to change something a manifest declared?
  ├─ Current unmerged task? → Revise the same contract; use maid plan revise if locked
  └─ Durable contract in accepted shared history (any branch)?
      ├─ Add a compatible artifact? → Chain merge in a new manifest
      └─ Rename, remove, move, or break an artifact? → Supersede in a new manifest
```

### When to Use This Skill

- Changing a public API that a prior manifest declared
- Renaming a class, method, or function
- Removing a feature that was manifested
- Splitting or merging modules
- Changing return types or required parameters
- Any intentional modification to an existing contract

### When NOT to Use This Skill

- Adding a completely new module (use `maid-planner`)
- Private-only refactors (use `maid-planner` for the scoped change; use this skill
  only when a prior contract changes)
- Fixing a bug without changing the public API (use `maid-planner` for the scoped
  fix; use this skill only when a prior contract changes)
- An unimplemented draft whose contract does not need revision (continue with
  `maid-implement-draft`; revise the same draft if its contract changes)
