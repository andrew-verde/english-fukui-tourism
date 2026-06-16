# Fukui friction nudge simulator

Static scenario framework for exploring hypothetical friction improvements once
the SEM outputs are finalized.

This is not a causal impact model. It shows sensitivity to assumed nudge
effectiveness and reach using:

```bash
make sem-ftas
make nudge-ranking
make friction-simulator-data
```

Then serve locally:

```bash
make friction-simulator-serve
```

Open <http://localhost:8766>.

## Interpretation boundary

The displayed `estimated intention shift` is in standardized latent
visit-intention units:

```text
max(-friction_code_path_to_satisfaction, 0)
  x prevalence_among_reporters
  x satisfaction_to_intention_path
  x assumed_effectiveness
  x assumed_reach
```

It is a scenario sensitivity value, not a forecast of visitor volume, revenue,
or opportunity-gap closure. Weather, route-intent, people-flow, and reservation
sources can be added as cited context or segmentation inputs later, but they
should stay separate from the SEM scenario math unless a defensible linking
model is added.
