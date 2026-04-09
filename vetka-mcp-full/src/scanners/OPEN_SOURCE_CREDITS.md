# Open Source Credits

`vetka-ingest-engine` builds on open tooling for file monitoring, extraction,
and indexing workflows.

## Runtime and Libraries

- Python
  - https://www.python.org/
  - License: PSF License.
  - Role: core runtime for ingestion, scanning, and orchestration.

- watchdog
  - https://github.com/gorakhargosh/watchdog
  - License: Apache-2.0.
  - Role: filesystem event monitoring for live reindex flows.

## Vector/Index Ecosystem

- Qdrant
  - https://github.com/qdrant/qdrant
  - License: Apache-2.0.
  - Role: downstream vector/index target used by ingestion update paths.

## OCR/Content Extraction Ecosystem

- PyMuPDF (fitz)
  - https://github.com/pymupdf/PyMuPDF
  - License: AGPL-3.0 OR commercial.
  - Role: PDF text extraction in related OCR intake paths.

## Notes

- Some ingestion-adjacent modules use additional extraction/parsing packages
  at monorepo level; expand this file as boundaries are extracted further.
- Preserve upstream notices and licenses when reusing code.
