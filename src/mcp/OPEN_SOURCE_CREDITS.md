# Open Source Credits

This module uses open-source protocols, libraries, and infrastructure.
No third-party source tree is intentionally vendored in this folder; integration
is done via dependencies and public APIs.

## Protocol / Core Runtime
- Model Context Protocol Python SDK (`mcp`):
  https://github.com/modelcontextprotocol/python-sdk (MIT)
- FastAPI:
  https://github.com/fastapi/fastapi (MIT)
- Starlette:
  https://github.com/encode/starlette (BSD-3-Clause)
- Uvicorn:
  https://github.com/encode/uvicorn (BSD-3-Clause)

## Networking / Transport
- HTTPX:
  https://github.com/encode/httpx (BSD-3-Clause)
- python-socketio:
  https://github.com/miguelgrinberg/python-socketio (MIT)
- websockets:
  https://github.com/python-websockets/websockets (BSD-3-Clause)

## Data / Validation
- Pydantic:
  https://github.com/pydantic/pydantic (MIT)
- orjson:
  https://github.com/ijl/orjson (Apache-2.0 OR MIT)

## Retrieval / Memory Ecosystem Used by MCP Tools
- Qdrant Client:
  https://github.com/qdrant/qdrant-client (Apache-2.0)
- Weaviate Python Client:
  https://github.com/weaviate/weaviate-python-client (BSD-3-Clause)

## Notes on Attribution
- Keep this file and `LICENSE` when redistributing this module.
- For full transitive dependency licenses, review the lockfile/environment used
  to build and ship this runtime.
- If attribution is incomplete, open an issue or PR.
