#!/usr/bin/env python3
"""
GEMMA-BRIDGE-2: JSON→tool_use converter proxy for free-code + Gemma4.

Sits between free-code and LiteLLM, intercepting responses to convert
Gemma's raw JSON tool calls into Anthropic tool_use content blocks.

Architecture:
    free-code (port 4001) → THIS PROXY → LiteLLM (port 4000) → Ollama → Gemma4

Gemma outputs tool calls as text:
    {"tool_name": "file_search", "parameters": {"query": "README.md"}}

This proxy converts to Anthropic format:
    {"type": "tool_use", "id": "toolu_xxx", "name": "file_search", "input": {"query": "README.md"}}

Usage:
    # Terminal 1: LiteLLM proxy
    LITELLM_MASTER_KEY=sk-ollama /tmp/litellm_venv/bin/litellm \
        --model ollama/gemma4:e4b --port 4000 --drop_params

    # Terminal 2: This bridge
    python3 scripts/litellm_gemma_bridge.py --port 4001

    # Terminal 3: free-code
    ANTHROPIC_BASE_URL=http://localhost:4001 ANTHROPIC_API_KEY=sk-ollama \
        ./cli-dev --model gemma4:e4b --print "Read README.md"

@file litellm_gemma_bridge.py
@status active
@phase 212
@task tb_1775502957_73663_1
"""

import argparse
import json
import logging
import re
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logging.basicConfig(level=logging.INFO, format="[BRIDGE] %(message)s")
log = logging.getLogger("gemma_bridge")

UPSTREAM = "http://localhost:4000"

# ---------------------------------------------------------------------------
# Tool call detection and conversion
# ---------------------------------------------------------------------------

# Patterns Gemma uses for tool calls (observed empirically)
TOOL_CALL_KEYS = [
    ("tool_name", "parameters"),   # Gemma's native format
    ("name", "parameters"),        # Alternative
    ("name", "input"),             # Anthropic-like
    ("tool_name", "input"),        # Hybrid
    ("function", "arguments"),     # OpenAI-like
    ("function", "args"),          # OpenAI variant (observed in Gemma output)
]


def _extract_tool_calls(text: str) -> list:
    """Extract JSON tool call objects from text response.

    Handles:
    - Clean JSON: {"tool_name": "...", "parameters": {...}}
    - Markdown wrapped: ```json ... ```
    - Multiple tool calls in sequence
    - Mixed text + JSON
    """
    calls = []
    # Strip markdown blocks first
    clean = re.sub(r"```(?:json)?\s*\n?", "", text)
    clean = clean.replace("```", "")

    # Find all JSON objects in the text
    depth = 0
    start = -1
    for i, ch in enumerate(clean):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = clean[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        # Direct tool call
                        if _is_tool_call(obj):
                            calls.append(obj)
                        # Wrapped: {"tool_calls": [...]}
                        else:
                            unwrapped = _unwrap_tool_calls(obj)
                            for tc in unwrapped:
                                if _is_tool_call(tc):
                                    calls.append(tc)
                                elif "function" in tc or "name" in tc:
                                    # Minimal tool call — just name, no params
                                    calls.append(tc)
                except (json.JSONDecodeError, ValueError):
                    pass
                start = -1
    return calls


def _is_tool_call(obj: dict) -> bool:
    """Check if a JSON object looks like a tool call."""
    for name_key, params_key in TOOL_CALL_KEYS:
        if name_key in obj and params_key in obj:
            return True
    return False


def _unwrap_tool_calls(obj: dict) -> list:
    """Handle Gemma's {"tool_calls": [...]} wrapper format.

    Gemma sometimes wraps tool calls in an array:
        {"tool_calls": [{"function": "read_file", "args": {"path": "..."}}]}

    Returns list of individual tool call dicts.
    """
    if "tool_calls" in obj and isinstance(obj["tool_calls"], list):
        return [tc for tc in obj["tool_calls"] if isinstance(tc, dict)]
    return []


def _to_anthropic_tool_use(obj: dict) -> dict:
    """Convert Gemma's tool call JSON to Anthropic tool_use content block."""
    # Extract tool name
    name = obj.get("tool_name") or obj.get("name") or obj.get("function", "")
    # Extract parameters
    params = obj.get("parameters") or obj.get("input") or obj.get("arguments") or obj.get("args", {})

    return {
        "type": "tool_use",
        "id": f"toolu_{uuid.uuid4().hex[:20]}",
        "name": name,
        "input": params if isinstance(params, dict) else {},
    }


def transform_response(body: dict) -> dict:
    """Transform LiteLLM response: convert text tool calls to tool_use blocks.

    Only modifies responses where text content contains valid tool call JSON.
    Pure text responses pass through unchanged.
    """
    if not isinstance(body, dict):
        return body

    content = body.get("content")
    if not isinstance(content, list):
        return body

    new_content = []
    found_tool = False

    for block in content:
        if block.get("type") != "text":
            new_content.append(block)
            continue

        text = block.get("text", "")
        tool_calls = _extract_tool_calls(text)

        if tool_calls:
            # Convert each tool call to tool_use block
            for tc in tool_calls:
                tool_block = _to_anthropic_tool_use(tc)
                new_content.append(tool_block)
                found_tool = True
                log.info(
                    "Converted tool call: %s(%s)",
                    tool_block["name"],
                    json.dumps(tool_block["input"])[:80],
                )

            # Keep any non-JSON text as a separate text block
            remaining = text
            for tc in tool_calls:
                # Remove the JSON from text (rough — good enough)
                try:
                    tc_str = json.dumps(tc)
                    remaining = remaining.replace(tc_str, "")
                except Exception:
                    pass
            remaining = re.sub(r"```(?:json)?\s*```", "", remaining).strip()
            if remaining:
                new_content.append({"type": "text", "text": remaining})
        else:
            new_content.append(block)

    if found_tool:
        body["content"] = new_content
        body["stop_reason"] = "tool_use"
        log.info("Response transformed: %d tool_use blocks", sum(1 for b in new_content if b.get("type") == "tool_use"))

    return body


# ---------------------------------------------------------------------------
# HTTP Proxy
# ---------------------------------------------------------------------------

def _build_tool_use_sse(tool_blocks: list, msg_id: str, model: str) -> bytes:
    """Build SSE event stream for tool_use response.

    Replaces text content_block events with tool_use events so free-code
    recognizes them as native tool calls.
    """
    events = []

    # message_start
    events.append(
        f'event: message_start\ndata: {json.dumps({"type": "message_start", "message": {"id": msg_id, "type": "message", "role": "assistant", "content": [], "model": model, "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0}}})}\n\n'
    )

    for i, block in enumerate(tool_blocks):
        if block["type"] == "tool_use":
            # content_block_start with tool_use
            events.append(
                f'event: content_block_start\ndata: {json.dumps({"type": "content_block_start", "index": i, "content_block": {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}})}\n\n'
            )
            # input_json_delta with full input
            events.append(
                f'event: content_block_delta\ndata: {json.dumps({"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}})}\n\n'
            )
            events.append(
                f'event: content_block_stop\ndata: {json.dumps({"type": "content_block_stop", "index": i})}\n\n'
            )
        elif block["type"] == "text" and block.get("text", "").strip():
            events.append(
                f'event: content_block_start\ndata: {json.dumps({"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}})}\n\n'
            )
            events.append(
                f'event: content_block_delta\ndata: {json.dumps({"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": block["text"]}})}\n\n'
            )
            events.append(
                f'event: content_block_stop\ndata: {json.dumps({"type": "content_block_stop", "index": i})}\n\n'
            )

    # message_delta with stop_reason=tool_use
    events.append(
        f'event: message_delta\ndata: {json.dumps({"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 0}})}\n\n'
    )
    events.append(
        f'event: message_stop\ndata: {json.dumps({"type": "message_stop"})}\n\n'
    )

    return "".join(events).encode()


class BridgeHandler(BaseHTTPRequestHandler):
    """Reverse proxy that intercepts Anthropic Messages API responses."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        # Check if this is a streaming request
        is_stream = False
        is_messages = "/messages" in self.path
        if body and is_messages:
            try:
                req_data = json.loads(body)
                is_stream = req_data.get("stream", False)
            except Exception:
                pass

        # Forward to upstream (LiteLLM)
        upstream_url = f"{UPSTREAM}{self.path}"
        headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
        }
        for h in ["Authorization", "X-Api-Key", "anthropic-version"]:
            val = self.headers.get(h)
            if val:
                headers[h] = val

        try:
            req = Request(upstream_url, data=body, headers=headers, method="POST")
            resp = urlopen(req, timeout=300)
        except HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
            return
        except URLError as e:
            self.send_error(502, f"Upstream error: {e}")
            return

        resp_body = resp.read()
        status = resp.status
        resp_headers = dict(resp.getheaders())

        if is_messages and status == 200 and is_stream:
            # STREAMING: buffer all SSE events, accumulate text, convert at end
            accumulated_text = ""
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            model = "gemma4:e4b"
            raw_events = resp_body.decode("utf-8", errors="replace")

            for line in raw_events.split("\n"):
                if line.startswith("data: "):
                    try:
                        evt = json.loads(line[6:])
                        evt_type = evt.get("type", "")
                        if evt_type == "message_start":
                            msg = evt.get("message", {})
                            msg_id = msg.get("id", msg_id)
                            model = msg.get("model", model)
                        elif evt_type == "content_block_delta":
                            delta = evt.get("delta", {})
                            if delta.get("type") == "text_delta":
                                accumulated_text += delta.get("text", "")
                    except Exception:
                        pass

            # Check if accumulated text contains tool calls
            tool_calls = _extract_tool_calls(accumulated_text)
            if tool_calls:
                tool_blocks = [_to_anthropic_tool_use(tc) for tc in tool_calls]
                # Keep remaining non-JSON text
                remaining = accumulated_text
                for tc in tool_calls:
                    try:
                        remaining = remaining.replace(json.dumps(tc), "")
                    except Exception:
                        pass
                remaining = re.sub(r"```(?:json)?\s*```", "", remaining).strip()
                if remaining:
                    tool_blocks.append({"type": "text", "text": remaining})

                log.info(
                    "SSE converted: %d tool calls from streamed text (%s)",
                    len(tool_calls),
                    ", ".join(b["name"] for b in tool_blocks if b["type"] == "tool_use"),
                )
                resp_body = _build_tool_use_sse(tool_blocks, msg_id, model)
            # else: pass through original SSE unchanged

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

        elif is_messages and status == 200:
            # NON-STREAMING: transform JSON response directly
            try:
                data = json.loads(resp_body)
                data = transform_response(data)
                resp_body = json.dumps(data).encode()
            except (json.JSONDecodeError, Exception) as e:
                log.warning("Transform failed (passing through): %s", e)

            self.send_response(status)
            for k, v in resp_headers.items():
                if k.lower() not in ("transfer-encoding", "content-length", "connection"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        else:
            # Non-messages or error — pass through
            self.send_response(status)
            for k, v in resp_headers.items():
                if k.lower() not in ("transfer-encoding", "content-length", "connection"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

    def do_GET(self):
        """Proxy GET requests (health checks etc)."""
        upstream_url = f"{UPSTREAM}{self.path}"
        headers = {}
        for h in ["Authorization", "X-Api-Key"]:
            val = self.headers.get(h)
            if val:
                headers[h] = val

        try:
            req = Request(upstream_url, headers=headers, method="GET")
            with urlopen(req, timeout=10) as resp:
                resp_body = resp.read()
                status = resp.status
        except HTTPError as e:
            resp_body = e.read()
            status = e.code
        except URLError as e:
            self.send_error(502, f"Upstream error: {e}")
            return

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        """Suppress default HTTP log noise, use our logger."""
        if args and "200" not in str(args[0]):
            log.debug(format, *args)


def main():
    parser = argparse.ArgumentParser(description="Gemma→Anthropic tool_use bridge proxy")
    parser.add_argument("--port", type=int, default=4001, help="Listen port (default: 4001)")
    parser.add_argument("--upstream", default="http://localhost:4000", help="LiteLLM upstream URL")
    args = parser.parse_args()

    global UPSTREAM
    UPSTREAM = args.upstream

    server = HTTPServer(("0.0.0.0", args.port), BridgeHandler)
    log.info("Gemma Bridge listening on port %d → upstream %s", args.port, UPSTREAM)
    log.info("Connect free-code: ANTHROPIC_BASE_URL=http://localhost:%d ANTHROPIC_API_KEY=sk-ollama ./cli-dev --model gemma4:e4b", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.server_close()


if __name__ == "__main__":
    main()
