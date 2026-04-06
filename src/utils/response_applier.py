"""
MARKER_196.CORE_GAP_2: Response Applier — Code extraction hook for chat/MCP responses.

Thin wrapper that extracts code blocks from LLM responses and writes them to disk.
Wired into chat_routes.py and llm_call_tool.py as optional apply_code=True flag.

Usage:
    from src.utils.response_applier import apply_response_code

    # From a chat/MCP response text
    files_written = apply_response_code(response_text, dry_run=False)

    # With explicit file paths
    files_written = apply_response_code(
        response_text,
        file_map={"src/new_feature.py": "python"},
        task_id="tb_xxx",
    )
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.utils.staging_utils import extract_code_blocks, write_file_safe

logger = logging.getLogger(__name__)

# Language → file extension mapping
_LANG_EXT = {
    "python": "py",
    "py": "py",
    "typescript": "ts",
    "ts": "ts",
    "tsx": "tsx",
    "javascript": "js",
    "js": "js",
    "rust": "rs",
    "go": "go",
    "html": "html",
    "css": "css",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "bash": "sh",
    "shell": "sh",
    "sql": "sql",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "ruby": "rb",
    "text": "txt",
}


def apply_response_code(
    content: str,
    file_map: Optional[Dict[str, str]] = None,
    task_id: Optional[str] = None,
    dry_run: bool = False,
) -> List[str]:
    """Extract code blocks from response text and write them to disk.

    Priority:
    1. If file_map provided, write content blocks to specified paths
    2. Extract code blocks from markdown (```lang ... ```)
    3. Detect filenames from code comments (# file: path)
    4. Fallback: generate filenames based on language

    Args:
        content: LLM response text
        file_map: Optional {filepath: language} mapping for explicit routing
        task_id: Optional task ID for commit message tracking
        dry_run: If True, return list of files that would be written without writing

    Returns:
        List of file paths that were written (or would be written in dry_run)
    """
    if not content or not content.strip():
        return []

    files_written: List[str] = []

    # Strategy 1: Use explicit file_map if provided
    if file_map:
        for filepath, lang in file_map.items():
            if len(file_map) == 1:
                # Single file — write entire content
                result = write_file_safe(filepath, content, dry_run=dry_run)
            else:
                # Multiple files — try to extract relevant block
                block = _extract_block_for_language(content, lang)
                if block:
                    result = write_file_safe(filepath, block, dry_run=dry_run)
                else:
                    result = None

            if result:
                files_written.append(filepath)
                logger.info(
                    "[ResponseApplier] Wrote %s (%d chars)%s",
                    filepath,
                    len(content),
                    " [DRY_RUN]" if dry_run else "",
                )
        return files_written

    # Strategy 2: Extract code blocks from markdown
    blocks = extract_code_blocks(content)
    if not blocks:
        # Check if entire content looks like code
        if _looks_like_code(content):
            blocks = [{"language": "python", "code": content, "filename": None}]

    for block in blocks:
        code = block.get("code", "").strip()
        if not code or len(code) < 10:
            continue

        lang = block.get("language", "python") or "python"
        filename = block.get("filename")

        # Determine filepath
        filepath = _resolve_filepath(filename, code, lang, task_id, len(files_written))
        if not filepath:
            continue

        result = write_file_safe(filepath, code, dry_run=dry_run)
        if result:
            files_written.append(filepath)
            logger.info(
                "[ResponseApplier] Wrote %s (%d chars)%s",
                filepath,
                len(code),
                " [DRY_RUN]" if dry_run else "",
            )

    return files_written


def apply_response_code_with_commit(
    content: str,
    task_id: Optional[str] = None,
    commit_message: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[List[str], Optional[str]]:
    """Extract code, write files, and create a git commit.

    Args:
        content: LLM response text
        task_id: Task ID for commit message
        commit_message: Optional custom commit message
        dry_run: If True, skip actual writes and commit

    Returns:
        Tuple of (files_written, commit_hash or None)
    """
    files_written = apply_response_code(content, task_id=task_id, dry_run=dry_run)

    if not files_written or dry_run:
        return files_written, None

    # Git commit
    commit_hash = _git_commit_files(files_written, task_id, commit_message)
    return files_written, commit_hash


# ── Internal Helpers ───────────────────────────────────────────────────


def _extract_block_for_language(content: str, lang: str) -> Optional[str]:
    """Extract a code block matching a specific language."""
    blocks = extract_code_blocks(content)
    for block in blocks:
        if block.get("language", "").lower() == lang.lower():
            return block.get("code")
    return None


def _looks_like_code(content: str) -> bool:
    """Check if content looks like code rather than prose."""
    code_indicators = [
        "def ",
        "class ",
        "import ",
        "from ",
        "async def ",
        "@router",
        "@app",
        "fn ",
        "func ",
        "const ",
        "let ",
        "pub fn ",
        "package ",
        "struct ",
        "impl ",
    ]
    first_500 = content[:500]
    return any(indicator in first_500 for indicator in code_indicators)


def _resolve_filepath(
    filename: Optional[str],
    code: str,
    lang: str,
    task_id: Optional[str],
    index: int,
) -> Optional[str]:
    """Resolve the final filepath for a code block."""
    # 1. Explicit filename
    if filename:
        return filename

    # 2. Detect from code comments: # file: path or // file: path
    inline_match = re.search(r"(?://|#)\s*file:\s*([^\s\n]+)", code[:200])
    if inline_match:
        return inline_match.group(1).strip()

    # 3. Detect from code content for common patterns
    # e.g., looking for file path references in the code
    path_match = re.search(
        r"((?:src|data|client)/[^\s]+?\.(?:py|js|ts|tsx|md|json))",
        code[:500],
        re.IGNORECASE,
    )
    if path_match:
        return path_match.group(1)

    # 4. Fallback: generate a filename
    ext = _LANG_EXT.get(lang.lower(), lang)
    if task_id:
        return f"src/generated/{task_id}_{index}.{ext}"
    return f"src/generated/block_{index}.{ext}"


def _git_commit_files(
    files: List[str],
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Optional[str]:
    """Create a git commit for the given files."""
    import subprocess as _sub

    if not files:
        return None

    try:
        # git add
        _sub.run(["git", "add"] + files, capture_output=True, text=True, timeout=10)

        # git commit
        if message:
            commit_msg = message
        elif task_id:
            commit_msg = (
                f"phase196.CORE_GAP_2: Response code extraction [task:{task_id}]"
            )
        else:
            commit_msg = "phase196.CORE_GAP_2: Response code extraction"

        result = _sub.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            if "nothing to commit" not in result.stderr.lower():
                logger.warning(
                    "[ResponseApplier] Git commit failed: %s", result.stderr.strip()
                )
                return None

        # Get commit hash
        hash_r = _sub.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return hash_r.stdout.strip() if hash_r.returncode == 0 else None

    except Exception as e:
        logger.error("[ResponseApplier] Git commit exception: %s", e)
        return None
