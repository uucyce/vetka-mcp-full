"""
MARKER_195.22 — Scoped auto-commit proof.

This file exists solely to prove that auto-commit scoping works:
- Task allowed_paths = ["tests/test_scoped_commit_proof.py"]
- Dirty files pulse/ and tools/back_to_ussr_app must NOT appear in this commit
- Only this file should be staged and committed
"""


def test_scoped_commit_proof():
    """Proof: this file was committed via scoped auto-commit."""
    assert True, "If you see this in git log, scoping works"
