# Open Source Credits

`vetka-memory-stack` relies on open infrastructure and libraries for durable,
retrievable, and compressible memory behavior.

## Vector and Retrieval Infrastructure

- Qdrant
  - https://github.com/qdrant/qdrant
  - License: Apache-2.0.
  - Role: vector persistence and similarity retrieval for long-term memory.

- Weaviate
  - https://github.com/weaviate/weaviate
  - License: BSD-3-Clause.
  - Role: optional retrieval backend used by parts of memory/search pipeline.

## Runtime and Language

- Python
  - https://www.python.org/
  - License: PSF License.
  - Role: runtime for memory orchestration, caching, retry, and compression.

## Attribution Notes

- Keep upstream license notices when reusing code or adapting modules.
- Preserve protocol/library references in docs and source comments.
- Contribute generic fixes upstream where possible.
