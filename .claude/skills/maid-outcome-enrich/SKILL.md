---
name: maid-outcome-enrich
description: Generate optional advisory Outcome enrichment outside maid-runner by orchestrating maid enrich prompt, agent-available model generation, maid enrich validate, and maid enrich render with cloud privacy disclosure.
---

# MAID Outcome Enrich

Generate optional advisory Outcome enrichment while keeping maid-runner itself
deterministic and AI-free. This skill is the only place in the enrichment
workflow that may call a model or touch provider credentials.

## Rules

- Keep runner commands deterministic. Use `maid enrich` only for prompt corpus
  creation, digest validation, and markdown rendering.
- Use the model access already available to the hosting agent, or a specific model the user chooses.
- CLOUD-PRIVACY: sending the lesson corpus to an external provider publishes Outcome lessons externally. Use external generation only after the user deliberately accepts that privacy boundary.
- A non-zero `maid enrich validate` result is a hard stop. Do not hand-edit `.maid/outcomes-digest.json` to satisfy validation; regenerate the candidate digest from the bounded corpus instead.
- Use only registered `maid enrich` and `maid insights` options. Do not invent
  provider, model, base URL, timeout, or API-key options for maid-runner.

## Workflow

1. Refresh the learned Outcome index when needed:

   ```bash
   maid learn
   ```

2. Build the bounded corpus the model may see:

   ```bash
   maid enrich prompt --output .maid/outcomes-enrichment-prompt.json
   ```

   If the index is intentionally stale, use the existing explicit opt-in:

   ```bash
   maid enrich prompt --allow-stale-index --output .maid/outcomes-enrichment-prompt.json
   ```

3. Send only `.maid/outcomes-enrichment-prompt.json` to a model.

   Use the model access already available to the hosting agent, or a specific
   model the user chooses. If that sends the corpus to an external provider,
   disclose CLOUD-PRIVACY first: sending the lesson corpus externally publishes
   Outcome lessons outside the local repository boundary.

   The model output must be a candidate `.maid/outcomes-digest.json`.

4. Validate the candidate digest:

   ```bash
   maid enrich validate --digest .maid/outcomes-digest.json
   ```

   Treat a non-zero `maid enrich validate` result as a hard stop. Do not
   hand-edit `.maid/outcomes-digest.json` to satisfy validation. Regenerate the
   candidate digest from the bounded corpus and validate again.

5. Render advisory markdown from the validated digest:

   ```bash
   maid enrich render --digest .maid/outcomes-digest.json --md-output .maid/outcomes-digest.md
   ```

6. Optionally view deterministic theme aggregation through insights:

   ```bash
   maid insights --theme-map .maid/outcomes-digest.json
   ```

## Output Boundaries

`.maid/outcomes-digest.json` and `.maid/outcomes-digest.md` are advisory,
generated, ignored artifacts. They are not authoritative Outcome records and
must not replace manifest `outcome:` sections, validation commands, review
evidence, or the MAID implementation lifecycle.
