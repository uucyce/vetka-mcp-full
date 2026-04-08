# Open Source Credits

`vetka-search-retrieval` stands on top of open retrieval and search ecosystem
components.

## Retrieval Backends and Concepts

- Qdrant
  - https://github.com/qdrant/qdrant
  - License: Apache-2.0.
  - Role: vector similarity search backend used by hybrid retrieval paths.

- Weaviate
  - https://github.com/weaviate/weaviate
  - License: BSD-3-Clause.
  - Role: keyword/BM25-style retrieval backend in hybrid mode.

- Reciprocal Rank Fusion (RRF)
  - Research concept used for multi-source result fusion.
  - Role: deterministic blending of heterogeneous search channels.

## Runtime and Tooling

- Python
  - https://www.python.org/
  - License: PSF License.
  - Role: runtime for retrieval orchestration and ranking logic.

- ripgrep
  - https://github.com/BurntSushi/ripgrep
  - License: MIT OR Unlicense.
  - Role: local content search fallback for file retrieval.

## Notes

- Local OS tooling integration (for example, platform file indexing utilities)
  is used as a fallback strategy for practical retrieval latency/coverage.
- Additional dependency attributions can be expanded as module boundaries
  continue to separate from the monorepo.
