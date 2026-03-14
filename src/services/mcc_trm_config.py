"""
MARKER_161.TRM.CONFIG.CONTRACT.V1
Phase-161 W1 TRM policy contract.

W1 scope:
- normalize request-level TRM profile/policy
- clamp unsafe values
- keep builder behavior unchanged (TRM disabled path)
"""

from __future__ import annotations

from typing import Any, Dict


_ALLOWED_PROFILES = {"off", "light", "balanced", "aggressive"}


def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
    try:
        raw = int(value)
    except Exception:
        raw = default
    return max(low, min(high, raw))


def resolve_trm_policy(trm_profile: str = "off", trm_policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
    profile = str(trm_profile or "off").strip().lower()
    if profile not in _ALLOWED_PROFILES:
        profile = "off"

    policy = dict(trm_policy or {})
    policy_profile = str(policy.get("profile") or "").strip().lower()
    if policy_profile in _ALLOWED_PROFILES:
        profile = policy_profile

    enabled = bool(policy.get("enabled", profile != "off"))
    if profile == "off":
        enabled = False

    max_refine_steps_default = {
        "off": 0,
        "light": 2,
        "balanced": 4,
        "aggressive": 8,
    }[profile]
    max_candidate_edges_default = {
        "off": 0,
        "light": 24,
        "balanced": 64,
        "aggressive": 160,
    }[profile]

    return {
        "profile": profile,
        "enabled": enabled,
        "seed": _clamp_int(policy.get("seed"), 0, 2_147_483_647, 42),
        "max_refine_steps": _clamp_int(
            policy.get("max_refine_steps"), 0, 64, max_refine_steps_default
        ),
        "max_candidate_edges": _clamp_int(
            policy.get("max_candidate_edges"), 0, 2_000, max_candidate_edges_default
        ),
    }

