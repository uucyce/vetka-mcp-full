# Phase 170 CUT Debug Inspector / Questions Recon

## Scope
Browser-only smoke for the `Inspector / Questions` card in CUT debug shell.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Card title: `page.getByText('Inspector / Questions')`
- Card subtitle: `page.getByText('Bootstrap stats')`
- Refresh action: `page.getByRole('button', { name: 'Refresh Project State' })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Readiness anchors
The inspector/questions lane is ready when these keys are visible inside the card payload:
- `fallback_questions`
- `source_count`
- `mode`
- `missing_fields`

Useful example values for the smoke:
- `Need language`
- `Need pacing`
- `duration_sec`

## Expected status text
### Refresh Project State
- transient: `Hydrating project state...`
- settled after non-runtime payload: `Project loaded`
- failure fallback: `Project state error`

## Refresh proof
After one refresh, the inspector card should show a changed JSON payload, for example:
- `Need audience`
- `recovery_hint`
- `ask one short clarifier`

The old first-pass question such as `Need language` should disappear if the second mocked payload replaces the first one.
