# Phase 170 CUT Debug Inspector / Questions Mock Matrix

## Goal
Minimum route matrix for a browser smoke that verifies the debug-shell Inspector / Questions card.

## Required mocked routes
| Route | Method | Why mocked | Expected request shape | Mock response |
| --- | --- | --- | --- | --- |
| `/api/cut/project-state` | `GET` | Hydrates the inspector card and supports refresh | query includes `sandbox_root` and `project_id` | project-state with `bootstrap_state.last_stats` |

## Minimum project-state shape
The payload can stay minimal as long as it includes:
- `success: true`
- `project.project_id`
- `bootstrap_state.last_stats`
- empty placeholder bundles and queue arrays
- `runtime_ready: false` so refresh settles on `Project loaded`

## Minimum `bootstrap_state.last_stats` shape
Use a structured JSON object with visible keys such as:
- `fallback_questions` as an array of strings
- `source_count` as a number
- `mode` as a string
- `missing_fields` as an array of strings

For refresh coverage, a second payload can add:
- `recovery_hint`
- a changed `fallback_questions` array

## Keep unmocked
- actual `pre` rendering of JSON in the card
- refresh button behavior
- runtime error overlay and `vetka_last_runtime_error` sentinel
