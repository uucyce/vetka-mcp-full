# PHASE 170 — CUT Scene Graph NLE Pane Card Density

## Goal
Keep the compact NLE graph card readable by limiting summary density while preserving the most useful graph/media cues.

## Density Budget
- line 1: title
- line 2: node label + node type
- line 3: display mode + modality + optional duration
- line 4: marker count
- separate compact sync/bucket line remains allowed

## Guardrails
- avoid packing node type, display mode, modality, duration, and marker count into one long line
- poster preview remains optional and compact
- compact card stays subordinate to DAG viewport
