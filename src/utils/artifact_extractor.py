"""
VETKA Phase 17-J: Artifact Extractor.

Extracts code artifacts from agent responses.
Finds ```language ... ``` blocks and creates artifact objects.

@status: active
@phase: 96
@depends: re, uuid
@used_by: main.py, chat_handler.py
"""

import re
import uuid
from datetime import datetime
from typing import List, Dict, Optional


def extract_artifacts(agent_output: str, agent_name: str = "Dev") -> List[Dict]:
    """
    Extract code artifacts from agent output.

    Finds patterns like:
    - ### File: name.py\\n```python\\ncode\\n```
    - ```python\\ncode\\n```

    Args:
        agent_output: Full text response from agent
        agent_name: Name of agent that created the artifact

    Returns:
        List of artifact dicts:
        [
            {
                'id': 'uuid',
                'type': 'code',
                'filename': 'example.py',
                'language': 'python',
                'content': 'def foo(): ...',
                'lines': 10,
                'agent': 'Dev',
                'created_at': 'ISO timestamp'
            }
        ]
    """
    artifacts = []
    seen_content = set()

    # Pattern 1: Code blocks with filename header
    # Matches: ### File: name.py\n```python\ncode\n```
    # Also: ## File: name.py or **File: name.py**
    file_pattern = r'(?:###?\s*|\*\*)?(?:File|Файл):\s*`?([^\n`]+)`?\*?\*?\n```(\w+)\n(.*?)```'

    for match in re.finditer(file_pattern, agent_output, re.DOTALL | re.IGNORECASE):
        filename = match.group(1).strip()
        language = match.group(2).lower()
        code = match.group(3).strip()

        # Skip empty or duplicate content
        content_hash = hash(code)
        if not code or content_hash in seen_content:
            continue
        seen_content.add(content_hash)

        # Clean up filename
        filename = filename.strip('`*_ ')

        artifacts.append({
            'id': str(uuid.uuid4()),
            'type': 'code',
            'filename': filename,
            'language': language,
            'content': code,
            'lines': len(code.split('\n')),
            'agent': agent_name,
            'created_at': datetime.now().isoformat()
        })

    # Pattern 2: Standalone code blocks (no filename header)
    # Matches: ```python\ncode\n```
    code_pattern = r'```(\w+)\n(.*?)```'

    for match in re.finditer(code_pattern, agent_output, re.DOTALL):
        language = match.group(1).lower()
        code = match.group(2).strip()

        # Skip empty or already captured
        content_hash = hash(code)
        if not code or content_hash in seen_content:
            continue
        seen_content.add(content_hash)

        # Skip non-code languages
        if language in ('text', 'plaintext', 'markdown', 'md', 'json', 'yaml', 'yml', 'xml', 'html', 'css'):
            continue

        # Generate filename based on language
        ext_map = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'bash': 'sh',
            'shell': 'sh',
            'ruby': 'rb',
            'rust': 'rs',
            'go': 'go',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'csharp': 'cs',
            'php': 'php',
            'swift': 'swift',
            'kotlin': 'kt',
            'scala': 'scala',
            'sql': 'sql'
        }
        ext = ext_map.get(language, language)
        filename = f"artifact_{len(artifacts) + 1}.{ext}"

        artifacts.append({
            'id': str(uuid.uuid4()),
            'type': 'code',
            'filename': filename,
            'language': language,
            'content': code,
            'lines': len(code.split('\n')),
            'agent': agent_name,
            'created_at': datetime.now().isoformat()
        })

    return artifacts


def extract_qa_score(qa_output: str) -> Optional[float]:
    """
    Extract QA score from QA agent output.

    Looks for patterns like:
    - SCORE: 0.85/1.0
    - Score: 0.8
    - ## SCORE: 0.75/1.0

    Returns:
        Float score between 0 and 1, or None if not found
    """
    # Pattern: SCORE: X.X or SCORE: X.X/1.0
    score_patterns = [
        r'SCORE:\s*(\d+\.?\d*)\s*/\s*1\.?0?',  # SCORE: 0.85/1.0
        r'SCORE:\s*(\d+\.?\d*)',  # SCORE: 0.85
        r'Score:\s*(\d+\.?\d*)',  # Score: 0.85
        r'\*\*SCORE\*\*:\s*(\d+\.?\d*)',  # **SCORE**: 0.85
    ]

    for pattern in score_patterns:
        match = re.search(pattern, qa_output, re.IGNORECASE)
        if match:
            try:
                score = float(match.group(1))
                # Normalize if > 1 (e.g., 85 -> 0.85)
                if score > 1:
                    score = score / 100
                return min(max(score, 0.0), 1.0)  # Clamp to 0-1
            except ValueError:
                continue

    return None


def extract_qa_verdict(qa_output: str) -> Optional[str]:
    """
    Extract QA verdict from QA agent output.

    Looks for:
    - ACCEPT / REFINE / REJECT
    - Verdict: ACCEPT

    Returns:
        'ACCEPT', 'REFINE', 'REJECT', or None
    """
    verdict_pattern = r'(?:Verdict|VERDICT):\s*(?:\*\*)?\s*(ACCEPT|REFINE|REJECT)'
    match = re.search(verdict_pattern, qa_output, re.IGNORECASE)

    if match:
        return match.group(1).upper()

    # Also check for emoji indicators
    if 'ACCEPT' in qa_output.upper():
        return 'ACCEPT'
    elif 'REJECT' in qa_output.upper():
        return 'REJECT'
    elif 'REFINE' in qa_output.upper():
        return 'REFINE'

    return None


def format_artifact_for_display(artifact: Dict) -> str:
    """
    Format artifact for text display (e.g., in chat).

    Returns:
        Formatted string like:
        "[ARTIFACT] example.py (python, 15 lines)"
    """
    return f"[ARTIFACT] {artifact['filename']} ({artifact['language']}, {artifact['lines']} lines)"


# ============================================
# EXPORTS
# ============================================
__all__ = [
    'extract_artifacts',
    'extract_qa_score',
    'extract_qa_verdict',
    'format_artifact_for_display'
]
