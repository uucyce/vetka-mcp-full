"""
Memory Transfer Protocol for VETKA.

Export and import VETKA memory in portable .vetka-mem format.
Supports transferring knowledge between VETKA instances and AI agents.

Format: .vetka-mem (JSON with metadata and knowledge graph)

Usage:
    from src.mcp.memory_transfer import MemoryTransfer

    transfer = MemoryTransfer()

    # Export memory
    result = transfer.export_memory("project_backup.vetka-mem")

    # Import memory
    result = transfer.import_memory("project_backup.vetka-mem")

@status: active
@phase: 96
@depends: json, hashlib, gzip, datetime, pathlib, shutil
@used_by: MCP tools, CLI
"""

import json
import hashlib
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class MemoryTransfer:
    """Export and import VETKA memory snapshots"""

    VERSION = "1.0.0"
    MAGIC_HEADER = "VETKA-MEM"

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path) if project_path else PROJECT_ROOT
        self.exports_dir = self.project_path / "data" / "memory_exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_memory(
        self,
        filename: Optional[str] = None,
        include_history: bool = True,
        include_tree: bool = True,
        include_reactions: bool = True,
        compress: bool = False
    ) -> Dict[str, Any]:
        """Export VETKA memory to .vetka-mem file

        Args:
            filename: Output filename (auto-generated if None)
            include_history: Include chat history
            include_tree: Include knowledge tree
            include_reactions: Include user reactions
            compress: Use gzip compression

        Returns:
            Export result with path and stats
        """
        timestamp = datetime.now()

        if filename is None:
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"vetka_memory_{date_str}.vetka-mem"

        output_path = self.exports_dir / filename
        if compress and not filename.endswith('.gz'):
            output_path = self.exports_dir / f"{filename}.gz"

        # Collect memory data
        memory_data = {
            "_meta": {
                "magic": self.MAGIC_HEADER,
                "version": self.VERSION,
                "created_at": timestamp.isoformat(),
                "project_path": str(self.project_path),
                "includes": {
                    "history": include_history,
                    "tree": include_tree,
                    "reactions": include_reactions
                }
            }
        }

        stats = {"sections": 0, "items": 0, "errors": []}

        # Export knowledge tree
        if include_tree:
            tree_data, count = self._export_tree()
            memory_data["tree"] = tree_data
            stats["sections"] += 1
            stats["items"] += count

        # Export chat history
        if include_history:
            history_data, count = self._export_history()
            memory_data["history"] = history_data
            stats["sections"] += 1
            stats["items"] += count

        # Export reactions
        if include_reactions:
            reactions_data, count = self._export_reactions()
            memory_data["reactions"] = reactions_data
            stats["sections"] += 1
            stats["items"] += count

        # Calculate checksum
        content = json.dumps(memory_data, ensure_ascii=False, sort_keys=True)
        memory_data["_meta"]["checksum"] = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Write file
        final_content = json.dumps(memory_data, ensure_ascii=False, indent=2)

        if compress:
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                f.write(final_content)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

        stats["size_bytes"] = output_path.stat().st_size
        stats["path"] = str(output_path)
        stats["filename"] = output_path.name

        return {
            "success": True,
            "path": str(output_path),
            "stats": stats
        }

    def import_memory(
        self,
        filepath: str,
        merge_strategy: str = "merge",  # "merge", "replace", "skip_existing"
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Import VETKA memory from .vetka-mem file

        Args:
            filepath: Path to .vetka-mem file
            merge_strategy: How to handle conflicts
            dry_run: If True, only validate without importing

        Returns:
            Import result with stats
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return {"success": False, "error": f"File not found: {filepath}"}

        # Read file
        try:
            if filepath.suffix == '.gz' or str(filepath).endswith('.vetka-mem.gz'):
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    memory_data = json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}

        # Validate magic header
        meta = memory_data.get("_meta", {})
        if meta.get("magic") != self.MAGIC_HEADER:
            return {"success": False, "error": "Invalid file format: missing VETKA-MEM header"}

        # Validate checksum
        stored_checksum = meta.get("checksum")
        if stored_checksum:
            # Remove checksum for validation
            meta_copy = dict(meta)
            del meta_copy["checksum"]
            data_copy = dict(memory_data)
            data_copy["_meta"] = meta_copy
            content = json.dumps(data_copy, ensure_ascii=False, sort_keys=True)
            calculated = hashlib.sha256(content.encode()).hexdigest()[:16]
            if calculated != stored_checksum:
                return {"success": False, "error": "Checksum mismatch: file may be corrupted"}

        stats = {
            "version": meta.get("version"),
            "created_at": meta.get("created_at"),
            "source_project": meta.get("project_path"),
            "sections": [],
            "items_processed": 0,
            "items_skipped": 0,
            "items_merged": 0,
            "dry_run": dry_run
        }

        # Import tree
        if "tree" in memory_data:
            tree_stats = self._import_tree(memory_data["tree"], merge_strategy, dry_run)
            stats["sections"].append({"name": "tree", **tree_stats})
            stats["items_processed"] += tree_stats.get("processed", 0)
            stats["items_skipped"] += tree_stats.get("skipped", 0)
            stats["items_merged"] += tree_stats.get("merged", 0)

        # Import history
        if "history" in memory_data:
            history_stats = self._import_history(memory_data["history"], merge_strategy, dry_run)
            stats["sections"].append({"name": "history", **history_stats})
            stats["items_processed"] += history_stats.get("processed", 0)
            stats["items_skipped"] += history_stats.get("skipped", 0)
            stats["items_merged"] += history_stats.get("merged", 0)

        # Import reactions
        if "reactions" in memory_data:
            reactions_stats = self._import_reactions(memory_data["reactions"], merge_strategy, dry_run)
            stats["sections"].append({"name": "reactions", **reactions_stats})
            stats["items_processed"] += reactions_stats.get("processed", 0)
            stats["items_skipped"] += reactions_stats.get("skipped", 0)
            stats["items_merged"] += reactions_stats.get("merged", 0)

        return {
            "success": True,
            "stats": stats,
            "message": "Dry run completed - no changes made" if dry_run else "Import completed"
        }

    def _export_tree(self) -> tuple:
        """Export knowledge tree structure"""
        tree_file = self.project_path / "data" / "tree.json"
        if not tree_file.exists():
            return {}, 0

        try:
            with open(tree_file, 'r', encoding='utf-8') as f:
                tree_data = json.load(f)

            # Count nodes
            def count_nodes(node):
                count = 1
                for child in node.get("children", []):
                    count += count_nodes(child)
                return count

            node_count = sum(count_nodes(n) for n in tree_data.get("nodes", []))
            return tree_data, node_count
        except Exception:
            return {}, 0

    def _export_history(self) -> tuple:
        """Export chat history"""
        history_dir = self.project_path / "data" / "chat_history"
        if not history_dir.exists():
            return [], 0

        history = []
        for file in history_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history.append({
                        "id": file.stem,
                        "data": data
                    })
            except Exception:
                continue

        return history, len(history)

    def _export_reactions(self) -> tuple:
        """Export user reactions"""
        reactions_file = self.project_path / "data" / "reactions.json"
        if not reactions_file.exists():
            return {}, 0

        try:
            with open(reactions_file, 'r', encoding='utf-8') as f:
                reactions_data = json.load(f)
            return reactions_data, len(reactions_data.get("reactions", []))
        except Exception:
            return {}, 0

    def _import_tree(self, tree_data: Dict, strategy: str, dry_run: bool) -> Dict:
        """Import tree data"""
        tree_file = self.project_path / "data" / "tree.json"
        stats = {"processed": 0, "skipped": 0, "merged": 0}

        if not tree_data:
            return stats

        def count_nodes(node):
            count = 1
            for child in node.get("children", []):
                count += count_nodes(child)
            return count

        new_count = sum(count_nodes(n) for n in tree_data.get("nodes", []))
        stats["processed"] = new_count

        if dry_run:
            return stats

        if strategy == "replace" or not tree_file.exists():
            with open(tree_file, 'w', encoding='utf-8') as f:
                json.dump(tree_data, f, ensure_ascii=False, indent=2)
        elif strategy == "skip_existing":
            stats["skipped"] = new_count
            stats["processed"] = 0
        # merge would require complex tree merging logic

        return stats

    def _import_history(self, history_data: List, strategy: str, dry_run: bool) -> Dict:
        """Import chat history"""
        history_dir = self.project_path / "data" / "chat_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        stats = {"processed": 0, "skipped": 0, "merged": 0}

        for item in history_data:
            chat_id = item.get("id")
            data = item.get("data")
            if not chat_id or not data:
                continue

            file_path = history_dir / f"{chat_id}.json"

            if file_path.exists():
                if strategy == "skip_existing":
                    stats["skipped"] += 1
                    continue
                elif strategy == "merge":
                    stats["merged"] += 1
                    # Merge messages
                    if not dry_run:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            existing = json.load(f)
                        existing_ids = {m.get("id") for m in existing.get("messages", [])}
                        for msg in data.get("messages", []):
                            if msg.get("id") not in existing_ids:
                                existing.setdefault("messages", []).append(msg)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(existing, f, ensure_ascii=False, indent=2)
                    continue

            stats["processed"] += 1
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

        return stats

    def _import_reactions(self, reactions_data: Dict, strategy: str, dry_run: bool) -> Dict:
        """Import reactions data"""
        reactions_file = self.project_path / "data" / "reactions.json"
        stats = {"processed": 0, "skipped": 0, "merged": 0}

        if not reactions_data:
            return stats

        new_count = len(reactions_data.get("reactions", []))

        if reactions_file.exists() and strategy == "skip_existing":
            stats["skipped"] = new_count
            return stats

        if reactions_file.exists() and strategy == "merge":
            if not dry_run:
                with open(reactions_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                existing_ids = {r.get("id") for r in existing.get("reactions", [])}
                for reaction in reactions_data.get("reactions", []):
                    if reaction.get("id") not in existing_ids:
                        existing.setdefault("reactions", []).append(reaction)
                        stats["merged"] += 1
                    else:
                        stats["skipped"] += 1
                with open(reactions_file, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            else:
                stats["merged"] = new_count
            return stats

        stats["processed"] = new_count
        if not dry_run:
            with open(reactions_file, 'w', encoding='utf-8') as f:
                json.dump(reactions_data, f, ensure_ascii=False, indent=2)

        return stats

    def list_exports(self) -> List[Dict]:
        """List available memory exports"""
        exports = []
        for file in self.exports_dir.glob("*.vetka-mem*"):
            try:
                stat = file.stat()
                exports.append({
                    "filename": file.name,
                    "path": str(file),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue

        return sorted(exports, key=lambda x: x["created_at"], reverse=True)

    def delete_export(self, filename: str) -> Dict[str, Any]:
        """Delete a memory export file"""
        file_path = self.exports_dir / filename
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {filename}"}

        # Security check - must be in exports dir
        if not str(file_path.resolve()).startswith(str(self.exports_dir.resolve())):
            return {"success": False, "error": "Invalid path"}

        file_path.unlink()
        return {"success": True, "deleted": filename}


# Global instance
memory_transfer = MemoryTransfer()
