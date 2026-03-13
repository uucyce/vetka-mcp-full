#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib import error, request

DEFAULT_MCC_BASE = "http://127.0.0.1:5001/api/mcc"
JsonFn = Callable[[str, str, Optional[Dict[str, Any]]], Dict[str, Any]]
TERMINAL_RUN_STATES = {"done", "blocked", "failed", "escalated"}


def _normalize_base_url(base_url: str) -> str:
    value = str(base_url or "").rstrip("/")
    if not value:
        return DEFAULT_MCC_BASE
    if value.endswith("/api/mcc"):
        return value
    if value.endswith("/api"):
        return value + "/mcc"
    return value + "/api/mcc"


def _http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Failed to reach MCC server: {exc.reason}") from exc
    return json.loads(raw or "{}")


def fetch_operator_methods(base_url: str = DEFAULT_MCC_BASE, http_json: JsonFn = _http_json) -> List[Dict[str, Any]]:
    payload = http_json("GET", _normalize_base_url(base_url) + "/localguys/operator-methods", None)
    methods = payload.get("methods") or []
    return [dict(row) for row in methods if isinstance(row, dict)]


def _resolve_method(method_or_family: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    needle = str(method_or_family or "").strip().lower()
    for row in rows:
        if needle == str(row.get("method") or "").strip().lower():
            return row
        if needle == str(row.get("workflow_family") or "").strip().lower():
            return row
    raise ValueError(f"Unsupported localguys method '{method_or_family}'")


def _parse_iso(ts: str) -> Optional[datetime]:
    value = str(ts or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _build_metrics(run: Dict[str, Any], contract: Dict[str, Any], latency_ms: float) -> Dict[str, Any]:
    manifest = dict(run.get("artifact_manifest") or {})
    required = list((contract.get("artifact_contract") or {}).get("required") or [])
    missing = list(manifest.get("missing") or [])
    created_at = _parse_iso(str(run.get("created_at") or ""))
    updated_at = _parse_iso(str(run.get("updated_at") or ""))
    runtime_ms = 0
    if created_at and updated_at:
        runtime_ms = max(0, int((updated_at - created_at).total_seconds() * 1000))
    return {
        "latency_ms": int(latency_ms),
        "runtime_ms": runtime_ms,
        "artifact_missing_count": len(missing),
        "required_artifact_count": len(required),
        "run_status": str(run.get("status") or ""),
        "workflow_family": str(run.get("workflow_family") or ""),
    }


def get_localguys_run(
    *,
    base_url: str = DEFAULT_MCC_BASE,
    run_id: str = "",
    task_id: str = "",
    http_json: JsonFn = _http_json,
) -> Dict[str, Any]:
    root = _normalize_base_url(base_url)
    if run_id:
        payload = http_json("GET", root + f"/localguys-runs/{run_id}", None)
    elif task_id:
        payload = http_json("GET", root + f"/tasks/{task_id}/localguys-run", None)
    else:
        raise ValueError("run_id or task_id is required")
    return dict(payload.get("run") or {})


def signal_localguys_run(
    *,
    run_id: str,
    base_url: str = DEFAULT_MCC_BASE,
    status: str = "",
    current_step: str = "",
    active_role: str = "",
    model_id: str = "",
    failure_reason: str = "",
    used_tools: Optional[List[str]] = None,
    write_attempts: Optional[List[str]] = None,
    turn_increment: int = 0,
    recommended_tools: Optional[List[str]] = None,
    filtered_tool_schemas: Optional[List[str]] = None,
    idle_turn_count: Optional[int] = None,
    verification_passed: Optional[bool] = None,
    verification_target: str = "",
    http_json: JsonFn = _http_json,
) -> Dict[str, Any]:
    root = _normalize_base_url(base_url)
    metadata: Dict[str, Any] = {}
    if used_tools:
        metadata["used_tools"] = [str(item).strip() for item in used_tools if str(item).strip()]
    if write_attempts:
        metadata["write_attempts"] = [str(item).strip() for item in write_attempts if str(item).strip()]
    if turn_increment > 0:
        metadata["turn_increment"] = int(turn_increment)
    if recommended_tools:
        metadata["recommended_tools"] = [str(item).strip() for item in recommended_tools if str(item).strip()]
    if filtered_tool_schemas:
        metadata["filtered_tool_schemas"] = [str(item).strip() for item in filtered_tool_schemas if str(item).strip()]
    if idle_turn_count is not None:
        metadata["idle_turn_count"] = max(0, int(idle_turn_count))
    if verification_passed is not None:
        metadata["verification_passed"] = bool(verification_passed)
    if verification_target:
        metadata["verification_target"] = str(verification_target).strip()

    payload: Dict[str, Any] = {}
    if status:
        payload["status"] = status
    if current_step:
        payload["current_step"] = current_step
    if active_role:
        payload["active_role"] = active_role
    if model_id:
        payload["model_id"] = model_id
    if failure_reason:
        payload["failure_reason"] = failure_reason
    if metadata:
        payload["metadata"] = metadata

    response = http_json("PATCH", root + f"/localguys-runs/{run_id}", payload)
    return {
        "success": bool(response.get("success", True)),
        "run": dict(response.get("run") or {}),
        "runtime_guard": dict(response.get("runtime_guard") or {}),
    }


def wait_for_localguys_run(
    run_id: str,
    *,
    base_url: str = DEFAULT_MCC_BASE,
    poll_interval_sec: float = 1.0,
    timeout_sec: float = 120.0,
    http_json: JsonFn = _http_json,
) -> Dict[str, Any]:
    started = time.perf_counter()
    last_run: Dict[str, Any] = {}
    while True:
        last_run = get_localguys_run(base_url=base_url, run_id=run_id, http_json=http_json)
        status = str(last_run.get("status") or "").strip().lower()
        if status in TERMINAL_RUN_STATES:
            return last_run
        if (time.perf_counter() - started) >= timeout_sec:
            raise TimeoutError(f"Timed out waiting for localguys run '{run_id}'")
        time.sleep(max(0.05, float(poll_interval_sec)))


def start_localguys_run(
    method_or_family: str,
    *,
    task_id: str,
    base_url: str = DEFAULT_MCC_BASE,
    project_id: str = "",
    preset: str = "",
    source_branch: str = "main",
    workflow_family: str = "",
    wait: bool = False,
    poll_interval_sec: float = 1.0,
    timeout_sec: float = 120.0,
    http_json: JsonFn = _http_json,
) -> Dict[str, Any]:
    root = _normalize_base_url(base_url)
    methods = fetch_operator_methods(root, http_json=http_json)
    method_row = _resolve_method(workflow_family or method_or_family, methods)
    selected_family = str(method_row.get("workflow_family") or "")
    payload: Dict[str, Any] = {"workflow_family": selected_family, "source_branch": source_branch}
    if project_id:
        payload["project_id"] = str(project_id)
    if preset:
        payload["preset"] = str(preset)

    started = time.perf_counter()
    response = http_json("POST", root + f"/tasks/{task_id}/localguys-run", payload)
    latency_ms = (time.perf_counter() - started) * 1000.0

    run = dict(response.get("run") or {})
    contract = dict(response.get("contract") or {})
    if wait and run.get("run_id"):
        run = wait_for_localguys_run(
            str(run.get("run_id") or ""),
            base_url=root,
            poll_interval_sec=poll_interval_sec,
            timeout_sec=timeout_sec,
            http_json=http_json,
        )
    return {
        "success": bool(response.get("success", True)),
        "task_id": str(task_id),
        "method": str(method_row.get("method") or ""),
        "workflow_family": selected_family,
        "source_family": str(method_row.get("source_family") or ""),
        "run_id": str(run.get("run_id") or ""),
        "playground_id": str(run.get("playground_id") or ""),
        "branch_name": str(run.get("branch_name") or ""),
        "worktree_path": str(run.get("worktree_path") or ""),
        "current_step": str(run.get("current_step") or ""),
        "status": str(run.get("status") or ""),
        "artifact_root": str((run.get("artifact_manifest") or {}).get("base_path") or ""),
        "metrics": _build_metrics(run, contract, latency_ms),
        "run": run,
        "contract": contract,
    }


def benchmark_localguys_runs(
    method_or_family: str,
    *,
    task_ids: List[str],
    base_url: str = DEFAULT_MCC_BASE,
    project_id: str = "",
    preset: str = "",
    source_branch: str = "main",
    workflow_family: str = "",
    wait: bool = False,
    poll_interval_sec: float = 1.0,
    timeout_sec: float = 120.0,
    http_json: JsonFn = _http_json,
) -> Dict[str, Any]:
    rows = []
    for task_id in task_ids:
        rows.append(
            start_localguys_run(
                method_or_family,
                task_id=task_id,
                base_url=base_url,
                project_id=project_id,
                preset=preset,
                source_branch=source_branch,
                workflow_family=workflow_family,
                wait=wait,
                poll_interval_sec=poll_interval_sec,
                timeout_sec=timeout_sec,
                http_json=http_json,
            )
        )

    total = len(rows)
    status_counts: Dict[str, int] = {}
    latency_sum = 0
    missing_sum = 0
    for row in rows:
        status = str((row.get("metrics") or {}).get("run_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        latency_sum += int((row.get("metrics") or {}).get("latency_ms") or 0)
        missing_sum += int((row.get("metrics") or {}).get("artifact_missing_count") or 0)

    return {
        "success": True,
        "method": rows[0]["method"] if rows else str(method_or_family),
        "workflow_family": rows[0]["workflow_family"] if rows else str(workflow_family or method_or_family),
        "task_count": total,
        "results": rows,
        "metrics": {
            "avg_latency_ms": int(latency_sum / total) if total else 0,
            "avg_artifact_missing_count": round(missing_sum / total, 2) if total else 0.0,
            "status_counts": status_counts,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="localguys operator tool")
    parser.add_argument("--server", default=DEFAULT_MCC_BASE, help="MCC base URL or server root")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="list supported localguys methods")

    run_parser = sub.add_parser("run", help="start a localguys run")
    run_parser.add_argument("method", help="operator method or workflow family")
    run_parser.add_argument("--task", required=True, help="task id")
    run_parser.add_argument("--project-id", default="", help="optional project id")
    run_parser.add_argument("--preset", default="", help="optional team preset override")
    run_parser.add_argument("--source-branch", default="main", help="source branch for playground")
    run_parser.add_argument("--workflow-family", default="", help="explicit workflow family override")
    run_parser.add_argument("--wait", action="store_true", help="poll until terminal state")
    run_parser.add_argument("--poll-interval", type=float, default=1.0, help="poll interval in seconds")
    run_parser.add_argument("--timeout", type=float, default=120.0, help="wait timeout in seconds")

    status_parser = sub.add_parser("status", help="read localguys run status")
    status_parser.add_argument("--run-id", default="", help="run id")
    status_parser.add_argument("--task", default="", help="task id for latest run lookup")

    signal_parser = sub.add_parser("signal", help="send lifecycle signal for a localguys run")
    signal_parser.add_argument("--run-id", required=True, help="run id")
    signal_parser.add_argument("--status", default="", help="optional run status")
    signal_parser.add_argument("--step", default="", help="optional current step")
    signal_parser.add_argument("--role", default="", help="optional active role")
    signal_parser.add_argument("--model-id", default="", help="optional active model id")
    signal_parser.add_argument("--failure-reason", default="", help="optional failure reason")
    signal_parser.add_argument("--tool", action="append", dest="tools", default=[], help="tool used during this turn")
    signal_parser.add_argument("--write-scope", action="append", dest="write_scopes", default=[], help="write scope attempted during this turn")
    signal_parser.add_argument("--turns", type=int, default=0, help="turn increment to record")
    signal_parser.add_argument("--recommend-tool", action="append", dest="recommended_tools", default=[], help="recommended tool for next turn")
    signal_parser.add_argument("--filtered-schema", action="append", dest="filtered_schemas", default=[], help="filtered tool schema name")
    signal_parser.add_argument("--idle-turn-count", type=int, default=None, help="explicit idle turn count")
    signal_parser.add_argument("--verification-passed", action="store_true", help="mark verification as passed")
    signal_parser.add_argument("--verification-target", default="", help="verification target label")

    bench_parser = sub.add_parser("benchmark", help="start a benchmark batch")
    bench_parser.add_argument("method", help="operator method or workflow family")
    bench_parser.add_argument("--task", action="append", dest="tasks", default=[], help="task id to include")
    bench_parser.add_argument("--project-id", default="", help="optional project id")
    bench_parser.add_argument("--preset", default="", help="optional team preset override")
    bench_parser.add_argument("--source-branch", default="main", help="source branch for playground")
    bench_parser.add_argument("--workflow-family", default="", help="explicit workflow family override")
    bench_parser.add_argument("--wait", action="store_true", help="poll each run until terminal state")
    bench_parser.add_argument("--poll-interval", type=float, default=1.0, help="poll interval in seconds")
    bench_parser.add_argument("--timeout", type=float, default=120.0, help="wait timeout in seconds")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "catalog":
            payload = {"success": True, "methods": fetch_operator_methods(args.server)}
        elif args.command == "status":
            run = get_localguys_run(base_url=args.server, run_id=args.run_id, task_id=args.task)
            payload = {"success": True, "run": run}
        elif args.command == "signal":
            payload = signal_localguys_run(
                run_id=args.run_id,
                base_url=args.server,
                status=args.status,
                current_step=args.step,
                active_role=args.role,
                model_id=args.model_id,
                failure_reason=args.failure_reason,
                used_tools=list(args.tools),
                write_attempts=list(args.write_scopes),
                turn_increment=int(args.turns or 0),
                recommended_tools=list(args.recommended_tools),
                filtered_tool_schemas=list(args.filtered_schemas),
                idle_turn_count=args.idle_turn_count,
                verification_passed=True if args.verification_passed else None,
                verification_target=args.verification_target,
            )
        elif args.command == "benchmark":
            payload = benchmark_localguys_runs(
                args.method,
                task_ids=list(args.tasks),
                base_url=args.server,
                project_id=args.project_id,
                preset=args.preset,
                source_branch=args.source_branch,
                workflow_family=args.workflow_family,
                wait=args.wait,
                poll_interval_sec=args.poll_interval,
                timeout_sec=args.timeout,
            )
        else:
            payload = start_localguys_run(
                args.method,
                task_id=args.task,
                base_url=args.server,
                project_id=args.project_id,
                preset=args.preset,
                source_branch=args.source_branch,
                workflow_family=args.workflow_family,
                wait=args.wait,
                poll_interval_sec=args.poll_interval,
                timeout_sec=args.timeout,
            )
    except Exception as exc:
        payload = {"success": False, "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
