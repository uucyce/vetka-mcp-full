"""
VETKA Artifact Scanner Service
Phase 108.3 - Artifact Directory Scanning

@file artifact_scanner.py
@status ACTIVE
@phase Phase 108.3
@created 2026-02-02

MARKER_108_3_ARTIFACT_SCAN: Phase 108.3 - Artifact directory scanning

Scans data/artifacts/ directory and returns artifact nodes for 3D tree visualization.
Links artifacts to source chats via staging.json metadata.

Artifact Types:
- code: Python, JavaScript, TypeScript files
- document: Markdown, text files
- data: JSON, CSV files
- image: PNG, JPG, SVG files

Node Structure:
{
    "id": "artifact_{hash}",
    "type": "artifact",
    "name": "filename.ext",
    "parent_id": "chat_{source_chat_id}",  # Linked to source chat
    "metadata": {
        "file_path": "data/artifacts/...",
        "artifact_type": "code|document|data|image",
        "language": "python|javascript|...",
        "size_bytes": 1234,
        "created_at": "2026-02-02T10:30:00Z",
        "source_message_id": "msg_xxx",
        "source_chat_id": "chat_xxx",
        "status": "done|streaming|error"
    },
    "visual_hints": {
        "layout_hint": {"expected_x": 120, "expected_y": 300, "expected_z": 0},
        "color": "#10b981",  # Green for artifacts
        "opacity": 1.0
    }
}
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ============================================================
# CONSTANTS
# ============================================================

ARTIFACTS_DIR = Path("data/artifacts")
STAGING_FILE = Path("data/staging.json")

# Extension to (type, language) mapping
ARTIFACT_TYPES = {
    # Code files
    '.py': ('code', 'python'),
    '.js': ('code', 'javascript'),
    '.ts': ('code', 'typescript'),
    '.tsx': ('code', 'typescript'),
    '.jsx': ('code', 'javascript'),
    '.java': ('code', 'java'),
    '.cpp': ('code', 'cpp'),
    '.c': ('code', 'c'),
    '.go': ('code', 'go'),
    '.rs': ('code', 'rust'),
    '.rb': ('code', 'ruby'),
    '.php': ('code', 'php'),
    '.swift': ('code', 'swift'),
    '.kt': ('code', 'kotlin'),

    # Document files
    '.md': ('document', 'markdown'),
    '.txt': ('document', 'text'),
    '.rst': ('document', 'restructuredtext'),
    '.adoc': ('document', 'asciidoc'),
    '.tex': ('document', 'latex'),
    '.pdf': ('document', 'pdf'),
    '.docx': ('document', 'word'),

    # Data files
    '.json': ('data', 'json'),
    '.yaml': ('data', 'yaml'),
    '.yml': ('data', 'yaml'),
    '.xml': ('data', 'xml'),
    '.csv': ('data', 'csv'),
    '.tsv': ('data', 'tsv'),
    '.toml': ('data', 'toml'),
    '.ini': ('data', 'ini'),
    '.env': ('data', 'env'),

    # Image files
    '.png': ('image', 'image'),
    '.jpg': ('image', 'image'),
    '.jpeg': ('image', 'image'),
    '.gif': ('image', 'image'),
    '.svg': ('image', 'svg'),
    '.webp': ('image', 'image'),
    '.bmp': ('image', 'image'),
    '.ico': ('image', 'image'),
}

# Color mapping for artifact types
ARTIFACT_COLORS = {
    'code': '#10b981',      # Green for code
    'document': '#3b82f6',  # Blue for documents
    'data': '#f59e0b',      # Amber for data
    'image': '#ec4899',     # Pink for images
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _load_staging_links() -> Dict[str, Dict]:
    """
    Load staging.json and create a mapping from filename to metadata.

    Returns:
        Dict[filename, {source_message_id, group_id, ...}]
    """
    staging_links = {}

    if not STAGING_FILE.exists():
        return staging_links

    try:
        with open(STAGING_FILE, 'r', encoding='utf-8') as f:
            staging = json.load(f)

        # Handle both old and new staging.json formats
        # New format: {"artifacts": {"art_1": {...}}, "spawn": {...}}
        # Old format: {"items": [{...}]}

        if 'artifacts' in staging:
            # New format - artifacts dict
            for artifact_id, artifact_data in staging['artifacts'].items():
                filename = artifact_data.get('filename')
                if filename:
                    staging_links[filename] = {
                        'source_message_id': artifact_data.get('source_message_id'),
                        'group_id': artifact_data.get('group_id'),
                        'source_chat_id': artifact_data.get('source_chat_id'),
                        'status': artifact_data.get('status', 'done'),
                        'artifact_id': artifact_id
                    }

        elif 'items' in staging:
            # Old format - items array
            for item in staging.get('items', []):
                filename = item.get('filename')
                if filename:
                    staging_links[filename] = {
                        'source_message_id': item.get('source_message_id'),
                        'group_id': item.get('group_id'),
                        'source_chat_id': item.get('source_chat_id'),
                        'status': item.get('status', 'done')
                    }

    except Exception as e:
        print(f"[ARTIFACT_SCAN] Warning: Could not load staging.json: {e}")

    return staging_links


def _get_artifact_type_and_language(file_path: Path) -> Tuple[str, str]:
    """
    Determine artifact type and language from file extension.

    Args:
        file_path: Path to artifact file

    Returns:
        Tuple of (artifact_type, language)
    """
    ext = file_path.suffix.lower()
    return ARTIFACT_TYPES.get(ext, ('document', 'text'))


def _generate_artifact_id(filename: str) -> str:
    """
    Generate stable artifact ID from filename.

    Args:
        filename: Artifact filename

    Returns:
        Artifact ID string (e.g., "artifact_a1b2c3d4")
    """
    file_hash = hashlib.md5(filename.encode('utf-8')).hexdigest()[:8]
    return f"artifact_{file_hash}"


def _calculate_artifact_position(
    parent_position: Optional[Dict] = None,
    index: int = 0
) -> Dict[str, float]:
    """
    Calculate artifact node position.

    If parent_position is provided, offset from parent (chat node).
    Otherwise, place in artifact cluster area.

    Args:
        parent_position: Parent chat node position {"expected_x": x, "expected_y": y, "expected_z": z}
        index: Artifact index for multi-artifact spacing

    Returns:
        Position dict with expected_x, expected_y, expected_z
    """
    if parent_position:
        # Offset from parent chat node
        # Place artifacts in a small cluster around the chat
        offset_x = 3 + (index % 3) * 2  # 3, 5, 7 spacing
        offset_y = -2 - (index // 3) * 2  # Downward rows

        return {
            "expected_x": parent_position.get("expected_x", 0) + offset_x,
            "expected_y": parent_position.get("expected_y", 0) + offset_y,
            "expected_z": parent_position.get("expected_z", 0)
        }
    else:
        # No parent - place in artifact cluster area (bottom-right quadrant)
        return {
            "expected_x": 100 + (index % 10) * 5,
            "expected_y": -50 - (index // 10) * 5,
            "expected_z": 0
        }


# ============================================================
# MAIN SCANNING FUNCTION
# ============================================================

def scan_artifacts() -> List[Dict]:
    """
    Scan artifacts directory and return artifact node data for 3D tree.

    Returns:
        List of artifact node dicts with:
        - id: Unique artifact ID
        - type: "artifact"
        - name: Filename
        - parent_id: Source chat ID (if linked)
        - metadata: File info, type, language, source, etc.
        - visual_hints: Position, color, opacity
    """
    artifacts = []

    # Check if artifacts directory exists
    if not ARTIFACTS_DIR.exists():
        print(f"[ARTIFACT_SCAN] Artifacts directory not found: {ARTIFACTS_DIR}")
        return artifacts

    # Load staging.json for chat/message links
    staging_links = _load_staging_links()
    print(f"[ARTIFACT_SCAN] Loaded {len(staging_links)} staging links")

    # Scan all files in artifacts directory
    artifact_files = sorted(ARTIFACTS_DIR.iterdir(), key=lambda p: p.stat().st_ctime)

    for index, file_path in enumerate(artifact_files):
        # Skip non-files (directories, symlinks)
        if not file_path.is_file():
            continue

        # Skip hidden files
        if file_path.name.startswith('.'):
            continue

        # Get file metadata
        try:
            stat = file_path.stat()
        except Exception as e:
            print(f"[ARTIFACT_SCAN] Warning: Could not stat {file_path.name}: {e}")
            continue

        # Determine artifact type and language
        artifact_type, language = _get_artifact_type_and_language(file_path)

        # Get staging info (chat/message links)
        staging_info = staging_links.get(file_path.name, {})
        source_chat_id = staging_info.get('source_chat_id') or staging_info.get('group_id')
        source_message_id = staging_info.get('source_message_id')
        status = staging_info.get('status', 'done')

        # Generate artifact ID
        artifact_id = _generate_artifact_id(file_path.name)

        # Determine parent ID (chat node if linked)
        parent_id = None
        if source_chat_id:
            parent_id = f"chat_{source_chat_id}"

        # Get color for artifact type
        color = ARTIFACT_COLORS.get(artifact_type, '#6b7280')  # Gray fallback

        # Calculate position (will be updated later if parent position is known)
        position = _calculate_artifact_position(None, index)

        # Build artifact node
        artifact_node = {
            "id": artifact_id,
            "type": "artifact",
            "name": file_path.name,
            "parent_id": parent_id,
            "metadata": {
                "file_path": str(file_path),
                "artifact_type": artifact_type,
                "language": language,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "source_message_id": source_message_id,
                "source_chat_id": source_chat_id,
                "status": status,
                "extension": file_path.suffix
            },
            "visual_hints": {
                "layout_hint": position,
                "color": color,
                "opacity": 1.0 if status == 'done' else 0.7  # Slightly transparent if not done
            }
        }

        artifacts.append(artifact_node)

    print(f"[ARTIFACT_SCAN] Scanned {len(artifacts)} artifacts from {ARTIFACTS_DIR}")

    return artifacts


def build_artifact_edges(
    artifact_nodes: List[Dict],
    chat_nodes: List[Dict]
) -> List[Dict]:
    """
    Build edges from chat nodes to artifact nodes.

    Args:
        artifact_nodes: List of artifact nodes
        chat_nodes: List of chat nodes

    Returns:
        List of edge dicts {from, to, semantics, metadata}
    """
    edges = []

    # Build chat_id -> chat_node mapping
    chat_map = {node['id']: node for node in chat_nodes}

    for artifact in artifact_nodes:
        parent_id = artifact.get('parent_id')

        if parent_id and parent_id in chat_map:
            # Create edge from chat to artifact
            edge = {
                "from": parent_id,
                "to": artifact['id'],
                "semantics": "artifact",
                "metadata": {
                    "type": "artifact",
                    "color": artifact['visual_hints']['color'],
                    "opacity": 0.5
                }
            }
            edges.append(edge)

    print(f"[ARTIFACT_SCAN] Built {len(edges)} artifact edges")

    return edges


def update_artifact_positions(
    artifact_nodes: List[Dict],
    chat_nodes: List[Dict]
) -> None:
    """
    Update artifact positions based on parent chat node positions.
    Modifies artifact_nodes in-place.

    Args:
        artifact_nodes: List of artifact nodes
        chat_nodes: List of chat nodes
    """
    # Build chat_id -> chat_node mapping
    chat_map = {node['id']: node for node in chat_nodes}

    # Track artifacts per chat for spacing
    chat_artifact_count = {}

    for artifact in artifact_nodes:
        parent_id = artifact.get('parent_id')

        if parent_id and parent_id in chat_map:
            # Get parent chat position
            parent_node = chat_map[parent_id]
            parent_position = parent_node.get('visual_hints', {}).get('layout_hint', {})

            # Get index for this artifact within parent chat
            if parent_id not in chat_artifact_count:
                chat_artifact_count[parent_id] = 0
            index = chat_artifact_count[parent_id]
            chat_artifact_count[parent_id] += 1

            # Calculate offset position
            new_position = _calculate_artifact_position(parent_position, index)
            artifact['visual_hints']['layout_hint'] = new_position

    print(f"[ARTIFACT_SCAN] Updated positions for {len(artifact_nodes)} artifacts")
