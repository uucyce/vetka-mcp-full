"""
Sequential benchmark — one model at a time, no GPU contention.
Tests quality (accuracy) + speed for each role.
"""
import requests
import json
import time
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# ── ROLE 1: MICRO (Drone) ──
MICRO_MODELS = ["phi4-mini", "gemma4:e2b", "gemma3:1b", "tinyllama"]
MICRO_TESTS = [
    {
        "name": "Code Classification",
        "prompt": "Classify this file: test_auth.py with content 'def test_login(): assert response.status == 200'. Answer with ONE word: test, config, src, docs, or other.",
        "expected": "test",
        "check": lambda r: r.strip().lower().replace('"', '').replace("'", "") == "test",
    },
    {
        "name": "Intent Detection",
        "prompt": "Classify this message: 'The login page crashes when I click submit'. Answer with ONE word: bug_report, feature_request, question, or command.",
        "expected": "bug_report",
        "check": lambda r: "bug" in r.strip().lower(),
    },
    {
        "name": "Error Category",
        "prompt": "Categorize this error: 'ModuleNotFoundError: No module named pandas'. Answer with ONE word: syntax, import, runtime, network, or auth.",
        "expected": "import",
        "check": lambda r: "import" in r.strip().lower(),
    },
]

# ── ROLE 2: SCOUT ──
SCOUT_MODELS = ["gemma4:e2b", "phi4-mini"]
SCOUT_TESTS = [
    {
        "name": "Relevance Scoring",
        "prompt": "Rate relevance 0-10: Search query='authentication middleware' Result='def validate_token(token): return jwt.decode(token, SECRET)'. Answer with just the number.",
        "expected_range": (7, 10),
        "check": lambda r: any(str(n) in r for n in range(7, 11)),
    },
    {
        "name": "File Path Routing",
        "prompt": "Which directory should contain a file called 'test_auth_middleware.py'? Answer with ONE path: src/, tests/, docs/, config/, or scripts/.",
        "expected": "tests/",
        "check": lambda r: "test" in r.strip().lower(),
    },
]

# ── ROLE 3: SHERPA ──
SHERPA_MODELS = ["gemma4:e4b", "qwen3.5"]
SHERPA_TESTS = [
    {
        "name": "Task Enrichment (JSON)",
        "system": "Return ONLY valid JSON. No markdown, no code blocks. Start with { end with }.",
        "prompt": 'Enrich this task: "Fix auth middleware token validation". Return JSON: {"priority": 1-5, "complexity": "low/medium/high", "hints": ["hint1", "hint2"]}',
        "check_json": True,
        "check": lambda r: True,  # checked separately
    },
    {
        "name": "Task Enrichment (XML)",
        "system": "You are a coding assistant. When asked to enrich a task, output ONLY XML. No markdown. Start with <task> end with </task>.",
        "prompt": 'Enrich: "Add rate limiting to API endpoints". Output: <task><priority>1-5</priority><complexity>low/medium/high</complexity><hints><hint>hint1</hint></hints></task>',
        "check_xml": True,
        "check": lambda r: True,
    },
]

# ── ROLE 4: ALPHA-GAMMA (Code Gen + Tool Use) ──
ALPHA_MODELS = ["gemma4:e4b", "qwen3.5"]
ALPHA_TESTS = [
    {
        "name": "Code Generation",
        "prompt": "Write a Python function called `is_palindrome(s: str) -> bool` that checks if a string is a palindrome. Return ONLY the function code, no explanation.",
        "check": lambda r: "def is_palindrome" in r and "return" in r,
    },
    {
        "name": "XML Tool Call",
        "system": """You use tools via XML. Available: read_file(path), search_code(pattern, path).
Format: <tool_use><tool_name>NAME</tool_name><parameters>{"key": "val"}</parameters></tool_use>
Output ONLY the XML block. No markdown, no explanation.""",
        "prompt": "Read the file src/auth.py",
        "check": lambda r: "<tool_use>" in r and "<tool_name>" in r and "</tool_use>" in r,
    },
]


def call_model(model, prompt, system=None, timeout=120):
    start = time.time()
    try:
        payload = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        elapsed = time.time() - start
        data = resp.json()
        return data.get("response", ""), elapsed, None
    except Exception as e:
        return "", time.time() - start, str(e)


def check_json(response):
    """Try to parse JSON, strip markdown if needed."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.startswith("```"))
    try:
        json.loads(text)
        return True, "clean" if not response.strip().startswith("```") else "md-wrapped"
    except:
        return False, "invalid"


def check_xml(response):
    text = response.strip()
    has_tag = "<task>" in text and "</task>" in text
    md_wrap = "```" in text
    return has_tag, "clean" if has_tag and not md_wrap else "md-wrapped" if has_tag else "missing"


def run_role(role_name, models, tests):
    print(f"\n{'='*60}")
    print(f"ROLE: {role_name}")
    print(f"{'='*60}")

    role_results = {}
    for model in models:
        print(f"\n  [{model}]")
        model_scores = []

        for test in tests:
            system = test.get("system", None)
            response, elapsed, error = call_model(model, test["prompt"], system)

            if error:
                status = f"ERROR ({error[:30]})"
                correct = False
            elif test.get("check_json"):
                valid, fmt = check_json(response)
                correct = valid
                status = f"JSON:{fmt}"
            elif test.get("check_xml"):
                valid, fmt = check_xml(response)
                correct = valid
                status = f"XML:{fmt}"
            else:
                correct = test["check"](response)
                status = "PASS" if correct else "FAIL"

            model_scores.append({
                "test": test["name"],
                "correct": correct,
                "elapsed": elapsed,
                "status": status,
                "preview": response[:100].replace("\n", " "),
            })

            icon = "+" if correct else "x"
            print(f"    [{icon}] {test['name']}: {status} ({elapsed:.1f}s)")
            if not correct:
                print(f"        Response: {response[:80].replace(chr(10), ' ')}")

        accuracy = sum(1 for s in model_scores if s["correct"]) / len(model_scores)
        avg_time = sum(s["elapsed"] for s in model_scores) / len(model_scores)
        role_results[model] = {"accuracy": accuracy, "avg_time": avg_time, "details": model_scores}
        print(f"    => Accuracy: {accuracy*100:.0f}% | Avg: {avg_time:.1f}s")

    return role_results


def main():
    print("=" * 60)
    print("SEQUENTIAL BENCHMARK — Phase A (Ollama + Metal, no LiteRT opt)")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_results = {}
    all_results["micro"] = run_role("MICRO (Drone)", MICRO_MODELS, MICRO_TESTS)
    all_results["scout"] = run_role("SCOUT", SCOUT_MODELS, SCOUT_TESTS)
    all_results["sherpa"] = run_role("SHERPA", SHERPA_MODELS, SHERPA_TESTS)
    all_results["alpha"] = run_role("ALPHA-GAMMA (Code+ToolUse)", ALPHA_MODELS, ALPHA_TESTS)

    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"{'Role':<12} {'Model':<18} {'Accuracy':<10} {'Avg Time':<10} {'Grade'}")
    print("-" * 60)

    for role, results in all_results.items():
        for model, r in results.items():
            acc = r["accuracy"]
            grade = "A" if acc == 1.0 else "B" if acc >= 0.66 else "C" if acc >= 0.33 else "F"
            print(f"{role:<12} {model:<18} {acc*100:>5.0f}%     {r['avg_time']:>6.1f}s    {grade}")

    # Save
    output_path = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/210_sherpa_gemma4/BENCHMARK_SEQUENTIAL_PHASE_A.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
