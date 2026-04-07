"""
Benchmark: XML Tool-Call Output for Claude Code / Free-Code harness
Phase A: Before LiteRT optimization
Tests each model's ability to produce clean XML tool calls.

Usage: python tests/benchmark_xml_toolcall.py
"""
import requests
import json
import time
import re
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"

MODELS = [
    "gemma4:e2b",
    "gemma4:e4b",
    "phi4-mini",
    "qwen3.5",
]

# Strict system prompt — forces XML output (Polaris approach adapted for XML)
SYSTEM_PROMPT = """You are a coding assistant that uses tools. When you need to use a tool, output ONLY the XML tool call block. No markdown, no code fences, no explanation before or after.

Available tools:
- read_file: Read a file. Parameters: {"path": "string"}
- list_files: List files in directory. Parameters: {"directory": "string"}
- search_code: Search for pattern. Parameters: {"pattern": "string", "path": "string"}

Format your tool call EXACTLY like this (start with <tool_use> end with </tool_use>):
<tool_use>
<tool_name>TOOL_NAME</tool_name>
<parameters>
{"param": "value"}
</parameters>
</tool_use>

CRITICAL: Output ONLY the XML block. Nothing else. No explanation. No markdown."""

TEST_PROMPTS = [
    ("Read the file src/main.py", "read_file", "path"),
    ("List all files in the tests/ directory", "list_files", "directory"),
    ("Search for 'def authenticate' in src/", "search_code", "pattern"),
]


def call_model(model: str, prompt: str, system: str = SYSTEM_PROMPT) -> tuple[str, float]:
    """Call Ollama and return (response_text, elapsed_seconds)."""
    start = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
        }, timeout=120)
        elapsed = time.time() - start
        data = resp.json()
        return data.get("response", ""), elapsed
    except Exception as e:
        return f"ERROR: {e}", time.time() - start


def validate_xml_toolcall(response: str, expected_tool: str, expected_param: str) -> dict:
    """Check if response is valid XML tool call."""
    result = {
        "has_tool_use_tag": "<tool_use>" in response and "</tool_use>" in response,
        "has_tool_name": f"<tool_name>{expected_tool}</tool_name>" in response,
        "has_parameters": "<parameters>" in response,
        "has_markdown_wrap": "```" in response,
        "has_explanation": len(response.split("<tool_use>")[0].strip()) > 5 if "<tool_use>" in response else True,
        "clean_xml": False,
    }

    # Check if it's clean (no markdown, no extra text)
    stripped = response.strip()
    result["clean_xml"] = (
        result["has_tool_use_tag"]
        and result["has_tool_name"]
        and not result["has_markdown_wrap"]
        and not result["has_explanation"]
    )

    return result


def run_benchmark():
    print("=" * 70)
    print("XML TOOL-CALL BENCHMARK — Phase A (before LiteRT optimization)")
    print(f"Ollama: {OLLAMA_URL}")
    print(f"Models: {', '.join(MODELS)}")
    print(f"Tests: {len(TEST_PROMPTS)} prompts x {len(MODELS)} models")
    print("=" * 70)

    results = {}

    for model in MODELS:
        print(f"\n--- {model} ---")
        model_results = []

        for prompt, expected_tool, expected_param in TEST_PROMPTS:
            print(f"  Prompt: {prompt[:50]}...", end=" ", flush=True)

            response, elapsed = call_model(model, prompt)
            validation = validate_xml_toolcall(response, expected_tool, expected_param)

            status = "CLEAN" if validation["clean_xml"] else "DIRTY" if validation["has_tool_use_tag"] else "FAIL"
            md_warn = " [MD-WRAP]" if validation["has_markdown_wrap"] else ""
            extra_warn = " [EXTRA-TEXT]" if validation["has_explanation"] else ""

            print(f"{status} {elapsed:.1f}s{md_warn}{extra_warn}")

            model_results.append({
                "prompt": prompt,
                "elapsed": elapsed,
                "status": status,
                "validation": validation,
                "response_preview": response[:200],
            })

        # Summary for model
        clean = sum(1 for r in model_results if r["status"] == "CLEAN")
        dirty = sum(1 for r in model_results if r["status"] == "DIRTY")
        fail = sum(1 for r in model_results if r["status"] == "FAIL")
        avg_time = sum(r["elapsed"] for r in model_results) / len(model_results)

        results[model] = {
            "clean": clean,
            "dirty": dirty,
            "fail": fail,
            "avg_time": avg_time,
            "details": model_results,
        }

        print(f"  => {clean}/{len(TEST_PROMPTS)} clean, {dirty} dirty, {fail} fail | avg {avg_time:.1f}s")

    # Final comparison table
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Model':<20} {'Clean':<8} {'Dirty':<8} {'Fail':<8} {'Avg Time':<10} {'Grade'}")
    print("-" * 70)

    for model, r in results.items():
        total = len(TEST_PROMPTS)
        grade = "A" if r["clean"] == total else "B" if r["clean"] + r["dirty"] == total else "F"
        print(f"{model:<20} {r['clean']:<8} {r['dirty']:<8} {r['fail']:<8} {r['avg_time']:<10.1f} {grade}")

    # Save JSON results
    output_path = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/210_sherpa_gemma4/BENCHMARK_XML_TOOLCALL_PHASE_A.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    return results


if __name__ == "__main__":
    run_benchmark()
