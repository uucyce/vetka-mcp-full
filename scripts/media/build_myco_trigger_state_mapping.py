#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH = ROOT / 'artifacts' / 'myco_motion' / 'team_A' / 'batch_manifest.json'
DEFAULT_OUTPUT = ROOT / 'artifacts' / 'myco_motion' / 'team_A' / 'trigger_state_mapping.json'

SYSTEM_MYCO_ASSETS = {
    'idle': 'client/src/assets/myco/myco_idle_question.png',
    'ready': 'client/src/assets/myco/myco_ready_smile.png',
    'speaking': 'client/src/assets/myco/myco_speaking_loop.apng',
}

SURFACE_POLICY = {
    'top_avatar': {
        'channel': 'system_myco',
        'role_assets_allowed': False,
        'fallback_channel': None,
        'states': ['idle', 'ready', 'speaking'],
    },
    'top_hint': {
        'channel': 'system_myco',
        'role_assets_allowed': False,
        'fallback_channel': None,
        'states': ['idle', 'ready', 'speaking'],
    },
    'mini_chat_compact': {
        'channel': 'role_preview',
        'role_assets_allowed': True,
        'fallback_channel': 'system_myco',
        'states': ['idle', 'ready', 'speaking'],
    },
    'mini_chat_expanded': {
        'channel': 'role_preview',
        'role_assets_allowed': True,
        'fallback_channel': 'system_myco',
        'states': ['idle', 'ready', 'speaking'],
    },
    'mini_stats_compact': {
        'channel': 'role_preview',
        'role_assets_allowed': True,
        'fallback_channel': 'system_myco',
        'states': ['idle', 'ready', 'speaking'],
    },
    'mini_stats_expanded': {
        'channel': 'role_preview',
        'role_assets_allowed': True,
        'fallback_channel': 'system_myco',
        'states': ['idle', 'ready', 'speaking'],
    },
}

TRIGGERS = [
    {
        'trigger': 'idle',
        'target_surfaces': ['top_avatar', 'top_hint'],
        'state': 'idle',
        'channel': 'system_myco',
        'role_source': 'none',
    },
    {
        'trigger': 'ready',
        'target_surfaces': ['top_avatar', 'top_hint'],
        'state': 'ready',
        'channel': 'system_myco',
        'role_source': 'none',
    },
    {
        'trigger': 'speaking',
        'target_surfaces': ['top_avatar', 'top_hint'],
        'state': 'speaking',
        'channel': 'system_myco',
        'role_source': 'none',
    },
    {
        'trigger': 'window_focus_chat',
        'target_surfaces': ['mini_chat_compact', 'mini_chat_expanded'],
        'state': 'ready',
        'channel': 'system_myco',
        'role_source': 'focused_role_or_generic',
    },
    {
        'trigger': 'window_focus_context',
        'target_surfaces': ['mini_chat_compact', 'mini_chat_expanded'],
        'state': 'ready',
        'channel': 'system_myco',
        'role_source': 'focused_role_or_generic',
    },
    {
        'trigger': 'window_focus_stats',
        'target_surfaces': ['mini_stats_compact', 'mini_stats_expanded'],
        'state': 'ready',
        'channel': 'role_preview',
        'role_source': 'active_task_workflow_or_selected_role',
    },
    {
        'trigger': 'window_focus_tasks',
        'target_surfaces': ['mini_stats_compact'],
        'state': 'ready',
        'channel': 'role_preview',
        'role_source': 'active_task_workflow_or_selected_role',
    },
    {
        'trigger': 'window_focus_balance',
        'target_surfaces': ['top_avatar', 'top_hint'],
        'state': 'ready',
        'channel': 'system_myco',
        'role_source': 'none',
    },
    {
        'trigger': 'workflow_selected',
        'target_surfaces': ['mini_stats_compact', 'mini_stats_expanded'],
        'state': 'ready',
        'channel': 'role_preview',
        'role_source': 'workflow_lead_role',
    },
    {
        'trigger': 'model_selected',
        'target_surfaces': ['mini_chat_compact', 'mini_chat_expanded'],
        'state': 'ready',
        'channel': 'role_preview',
        'role_source': 'selected_role',
    },
    {
        'trigger': 'task_started',
        'target_surfaces': ['mini_stats_compact', 'mini_stats_expanded'],
        'state': 'speaking',
        'channel': 'role_preview',
        'role_source': 'active_running_role',
    },
    {
        'trigger': 'task_completed',
        'target_surfaces': ['mini_stats_compact', 'mini_stats_expanded'],
        'state': 'ready',
        'channel': 'role_preview',
        'role_source': 'active_running_role',
    },
    {
        'trigger': 'task_failed',
        'target_surfaces': ['mini_stats_compact', 'mini_stats_expanded'],
        'state': 'speaking',
        'channel': 'role_preview',
        'role_source': 'active_running_role',
    },
    {
        'trigger': 'parallel_role_active',
        'target_surfaces': ['mini_chat_expanded', 'mini_stats_expanded'],
        'state': 'speaking',
        'channel': 'role_preview',
        'role_source': 'parallel_role_set',
    },
]

VARIANT_ASSIGNMENT = {
    'architect': {'strategy': 'singleton_primary', 'order': ['primary'], 'max_parallel': 1},
    'researcher': {'strategy': 'singleton_primary', 'order': ['primary'], 'max_parallel': 1},
    'verifier': {'strategy': 'singleton_primary', 'order': ['primary'], 'max_parallel': 1},
    'coder': {'strategy': 'ordinal_cycle', 'order': ['coder1', 'coder2'], 'max_parallel': 2},
    'scout': {'strategy': 'ordinal_cycle', 'order': ['scout1', 'scout2', 'scout3'], 'max_parallel': 3},
}


def _repo_rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        return str(p)


def build_mapping(batch_manifest_path: Path) -> dict:
    batch = json.loads(batch_manifest_path.read_text(encoding='utf-8'))
    role_assets: dict[str, dict[str, str]] = {}
    for asset in batch.get('assets', []):
        role = str(asset['role'])
        variant = str(asset['variant'])
        output_apng = _repo_rel(asset['output_apng'])
        role_assets.setdefault(role, {})[variant] = output_apng

    return {
        'marker': 'MARKER_168.MYCO.TRIGGER_STATE.MAPPING.V1',
        'version': 1,
        'note': 'Top MYCO surfaces remain system-helper only. Role assets are mapped to role-aware panels and task/workflow surfaces.',
        'source_batch_manifest': _repo_rel(batch_manifest_path),
        'system_myco_assets': SYSTEM_MYCO_ASSETS,
        'role_assets': role_assets,
        'surface_policy': SURFACE_POLICY,
        'variant_assignment': VARIANT_ASSIGNMENT,
        'triggers': TRIGGERS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Build MYCO trigger-state mapping manifest.')
    parser.add_argument('--batch-manifest', type=Path, default=DEFAULT_BATCH)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    mapping = build_mapping(args.batch_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(mapping, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(f"MARKER_168.MYCO.TRIGGER_STATE.MAPPING={args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
