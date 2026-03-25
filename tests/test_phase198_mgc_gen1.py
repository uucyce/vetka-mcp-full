"""
Tests for 198.P1.3: MGC Gen1 — replace Qdrant stub with SQLite
"""
import pytest
import json
import asyncio
from pathlib import Path


@pytest.mark.asyncio
async def test_gen1_store_and_get(tmp_path):
    """Store in Gen1 SQLite, retrieve by key."""
    import src.memory.mgc_cache as mgc_mod
    original_path = mgc_mod._GEN1_DB_PATH
    mgc_mod._GEN1_DB_PATH = tmp_path / "test_gen1.db"
    mgc_mod.reset_mgc_cache()
    try:
        cache = mgc_mod.get_mgc_cache()
        from src.memory.mgc_cache import MGCEntry
        entry = MGCEntry(key="test_key", value={"hello": "world"})
        await cache._store_in_qdrant(entry)

        result = await cache._get_from_qdrant("test_key")
        assert result == {"hello": "world"}
    finally:
        mgc_mod._GEN1_DB_PATH = original_path
        mgc_mod.reset_mgc_cache()


@pytest.mark.asyncio
async def test_gen1_miss_returns_none(tmp_path):
    """Non-existent key returns None."""
    import src.memory.mgc_cache as mgc_mod
    original_path = mgc_mod._GEN1_DB_PATH
    mgc_mod._GEN1_DB_PATH = tmp_path / "test_gen1.db"
    mgc_mod.reset_mgc_cache()
    try:
        cache = mgc_mod.get_mgc_cache()
        result = await cache._get_from_qdrant("nonexistent")
        assert result is None
    finally:
        mgc_mod._GEN1_DB_PATH = original_path
        mgc_mod.reset_mgc_cache()


@pytest.mark.asyncio
async def test_gen1_access_count_increments(tmp_path):
    """Each get increments access_count in SQLite."""
    import sqlite3
    import src.memory.mgc_cache as mgc_mod
    original_path = mgc_mod._GEN1_DB_PATH
    mgc_mod._GEN1_DB_PATH = tmp_path / "test_gen1.db"
    mgc_mod.reset_mgc_cache()
    try:
        cache = mgc_mod.get_mgc_cache()
        from src.memory.mgc_cache import MGCEntry
        entry = MGCEntry(key="counter_key", value="data")
        await cache._store_in_qdrant(entry)

        await cache._get_from_qdrant("counter_key")
        await cache._get_from_qdrant("counter_key")
        await cache._get_from_qdrant("counter_key")

        import hashlib
        key_hash = hashlib.md5(b"counter_key").hexdigest()
        conn = sqlite3.connect(str(tmp_path / "test_gen1.db"))
        row = conn.execute("SELECT access_count FROM mgc_gen1 WHERE key_hash = ?", (key_hash,)).fetchone()
        conn.close()
        assert row[0] >= 3
    finally:
        mgc_mod._GEN1_DB_PATH = original_path
        mgc_mod.reset_mgc_cache()


@pytest.mark.asyncio
async def test_gen1_delete(tmp_path):
    """Delete removes entry from Gen1."""
    import src.memory.mgc_cache as mgc_mod
    original_path = mgc_mod._GEN1_DB_PATH
    mgc_mod._GEN1_DB_PATH = tmp_path / "test_gen1.db"
    mgc_mod.reset_mgc_cache()
    try:
        cache = mgc_mod.get_mgc_cache()
        from src.memory.mgc_cache import MGCEntry
        entry = MGCEntry(key="del_key", value="to_delete")
        await cache._store_in_qdrant(entry)
        assert await cache._get_from_qdrant("del_key") == "to_delete"

        await cache._delete_from_qdrant("del_key")
        assert await cache._get_from_qdrant("del_key") is None
    finally:
        mgc_mod._GEN1_DB_PATH = original_path
        mgc_mod.reset_mgc_cache()


def test_gen1_stats_includes_count(tmp_path):
    """get_stats() includes gen1 count."""
    import src.memory.mgc_cache as mgc_mod
    original_path = mgc_mod._GEN1_DB_PATH
    mgc_mod._GEN1_DB_PATH = tmp_path / "test_gen1.db"
    mgc_mod.reset_mgc_cache()
    try:
        cache = mgc_mod.get_mgc_cache()
        stats = cache.get_stats()
        assert "gen1_count" in stats or "gen1" in str(stats)
    finally:
        mgc_mod._GEN1_DB_PATH = original_path
        mgc_mod.reset_mgc_cache()
