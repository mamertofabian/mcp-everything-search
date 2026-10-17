---
name: maid-run-review
description: Generate optional advisory MAID run reviews outside maid-runner with cloud privacy disclosure.
---

# MAID Run Review

Generate an optional LLM-assisted review of one completed MAID run while
keeping maid-runner itself deterministic and AI-free. This skill is the only
place in the run-review workflow that may call a model or touch provider
credentials.

## Rules

- Keep runner commands deterministic. Use `maid evaluate` only for run evidence,
  prompt request creation, review validation, and markdown rendering.
- Use the model access already available to the hosting agent, or a specific
  model the user chooses.
- CLOUD-PRIVACY: before using a cloud model, disclose that the bounded run
  review request leaves the machine. Name what run evidence leaves the machine:
  deterministic evaluation findings, plan-lock revision evidence, Outcome
  lessons and review notes, incident counts, and any operator-supplied diff
  file included with `--diff-file`.
- A non-zero review validation result is a hard stop. Do not hand-edit citations
  or evidence ids to satisfy validation; regenerate the candidate review from
  the bounded request instead.
- The final report is advisory, never a gate. It must not be fed back to the implementing agent as instructions during an active run.
- Use only registered `maid evaluate` options. Do not invent provider, model,
  base URL, timeout, or API-key options for maid-runner.

## Workflow

1. Show the deterministic run evidence first:

   ```bash
   maid evaluate run <manifest>
   ```

2. Build the bounded review request:

   ```bash
   maid evaluate prompt <manifest> --output .maid/run-review-request.json
   ```

   If the operator wants diff evidence included, prepare a diff file explicitly,
   say how it was prepared, and pass it through the existing option:

   ```bash
   maid evaluate prompt <manifest> --diff-file <diff-file> --output .maid/run-review-request.json
   ```

3. Generate a candidate review with an agent-available model.

   Send only `.maid/run-review-request.json` to the model. If that uses a cloud
   model, disclose CLOUD-PRIVACY first and name what run evidence leaves the
   machine. The model output must be a JSON run review that cites only evidence
   ids from the request.

4. Validate the candidate review:

   ```bash
   maid evaluate validate .maid/run-review.json --request .maid/run-review-request.json
   ```

   Treat any validation failure as fail closed. Do not hand-edit citations or
   evidence ids to force validity. Regenerate or correct the candidate review
   with the model from the bounded request, then validate again.

5. Render the validated advisory report:

   ```bash
   maid evaluate render .maid/run-review.json --request .maid/run-review-request.json --output .maid/run-reviews/<slug>.md
   ```

6. Present the labeled advisory report to the human operator. Do not treat the
   report as a workflow gate, and do not give it to the implementing agent as
   mid-run instructions.

## Output Boundaries

`.maid/run-review-request.json`, `.maid/run-review.json`, and
`.maid/run-reviews/*.md` are generated advisory artifacts. They are not
authoritative Outcome records and must not replace manifest `outcome:`
sections, validation commands, implementation review, or the MAID lifecycle.
