# MARKER_157_7_3_VETKA_JARVIS_FILE_FACTS_IMPL_REPORT_2026-03-07

Status: `SUPERSEDED / ROLLED BACK`

This report is retained only as historical note.

Reason for rollback:
- The `file_facts` path introduced new ad-hoc hard limits in voice runtime,
- it duplicated existing context infrastructure instead of reusing the unified chat-grade pipeline,
- it was replaced by model-aware unified context packing (`ContextPacker + ELISION + provider adaptive budget`).

Replacement report:
- `MARKER_157_7_3R_VETKA_JARVIS_UNIFIED_CONTEXT_PACKING_IMPL_REPORT_2026-03-07.md`
