# Open Source Credits

`vetka-bridge-core` builds on open source protocols and libraries that define
its interoperability and runtime behavior.

## Protocol and Architecture Foundations

- Model Context Protocol (MCP)
  - https://modelcontextprotocol.io/introduction
  - License: specification/documentation terms by the MCP maintainers.
  - Role in this module: shapes cross-runtime tool contracts and adapter model.

## Runtime Libraries

- Python
  - https://www.python.org/
  - License: PSF License.
  - Role: primary implementation runtime.

- httpx
  - https://github.com/encode/httpx
  - License: BSD-3-Clause.
  - Role: async HTTP client for bridge tool execution against VETKA APIs.

## Integrated VETKA Ecosystem Dependencies

Bridge tools can invoke capabilities implemented in sibling VETKA modules
(MCP tools, memory, search, orchestration). Those modules may rely on
additional OSS packages documented in their own repository/module credits.

## Attribution Policy

- Keep original license notices when reusing code.
- Preserve upstream attribution in source and docs.
- Prefer contributions upstream when improvements are generic.
