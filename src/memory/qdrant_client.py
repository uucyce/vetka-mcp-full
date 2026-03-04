"""
VETKA Phase 7.2 - Qdrant Integration
Hierarchical vector storage for VetkaTree with Triple Write atomicity

@file qdrant_client.py
@status active
@phase 108
@depends time, json, uuid, logging, dataclasses, datetime, qdrant_client
@used_by engram_user_memory.py, hybrid_search.py, file_watcher.py, orchestrator_with_elisya.py, vetka_mcp_bridge.py, shared_tools.py, llm_call_tool.py, message_utils.py, semantic_routes.py, watcher_routes.py, mcp_state_manager.py, trash.py, replay_buffer.py, session_tools.py

MARKER_QDRANT_CHAT_INDEX: Phase 103.7 - VetkaGroupChat collection
- Collection name: 'VetkaGroupChat' (COLLECTION_NAMES['chat'])
- Functions: upsert_chat_message() + search_chat_history()
- Message structure: group_id, message_id, sender_id, content, role, agent, model, timestamp
- Embeddings: Generated via get_embedding() for semantic search
- Filters: Can filter by group_id and role
- Status: ✅ READY - messages auto-persisted from group_chat_manager and group_message_handler

MARKER_TODO_QDRANT_CHAT: Items for Phase 108.2-108.4
1. Add pagination to search_chat_history() (offset + limit)
2. Add retry wrapper for upsert failures
3. Verify embedding service availability
4. Make max_messages configurable in chat digest API
5. Add rate limiting for large semantic queries
"""

import time
import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger("VETKA_QDRANT")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition, MatchAny, MatchValue
    # RecreateCollectionRequest is deprecated in qdrant-client 1.15+
    QDRANT_AVAILABLE = True
except ImportError:
    print("⚠️  qdrant-client not installed. Install with: pip install qdrant-client")
    QDRANT_AVAILABLE = False
    QdrantClient = None


@dataclass
class VetkaTreeNode:
    """Hierarchical node in VetkaTree"""
    node_id: str
    path: str  # e.g., "projects/python/ml/scikit-learn"
    content: str
    metadata: Dict[str, Any]
    timestamp: float
    vector: List[float] = None  # Embedding
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['vector'] = self.vector or []
        return data


@dataclass
class VetkaChangeLogEntry:
    """Audit trail entry"""
    workflow_id: str
    action: str  # create, update, delete
    collection: str  # VetkaTree, VetkaLeaf, Weaviate
    node_id: str
    timestamp: float
    user: str = "system"
    status: str = "success"  # success, failed
    error: Optional[str] = None


class QdrantVetkaClient:
    """
    Production Qdrant client for VETKA
    - Manages VetkaTree (hierarchical) and VetkaLeaf (details) collections
    - Implements Triple Write (Weaviate + Qdrant + ChangeLog)
    - Provides hierarchical search by path
    """
    
    COLLECTION_NAMES = {
        'tree': 'VetkaTree',
        'leaf': 'VetkaLeaf',
        'changelog': 'VetkaChangeLog',
        'trash': 'VetkaTrash',  # MARKER-77-02: Phase 77 Memory Sync trash collection
        'chat': 'VetkaGroupChat',  # MARKER_103.7: Phase 103 - Chat history persistence
        'artifacts': 'VetkaArtifacts'  # MARKER_153.IMPL.G07: artifact batch collection
    }
    
    VECTOR_SIZE = 768  # For embeddings (adjustable)
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self.client = None
        self.changelog = []
        
        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(url=f"http://{host}:{port}")
                self._initialize_collections()
                print(f"✅ Qdrant connected ({host}:{port})")
            except Exception as e:
                print(f"❌ Qdrant connection failed: {e}")
                self.client = None
        else:
            print("⚠️  Qdrant unavailable - install qdrant-client")
    
    def health_check(self) -> bool:
        """Check Qdrant connection"""
        if not self.client:
            return False
        try:
            info = self.client.get_collections()
            return bool(info)
        except:
            return False
    
    def _initialize_collections(self):
        """Create collections if they don't exist"""
        if not self.client:
            return
        
        try:
            collections = self.client.get_collections()
            existing = {c.name for c in collections.collections}
            
            for col_name in self.COLLECTION_NAMES.values():
                if col_name not in existing:
                    self.client.recreate_collection(
                        collection_name=col_name,
                        vectors_config=VectorParams(
                            size=self.VECTOR_SIZE,
                            distance=Distance.COSINE
                        )
                    )
                    print(f"   ✅ Created collection: {col_name}")
        except Exception as e:
            print(f"   ⚠️  Collection initialization: {e}")
    
    # ===== TRIPLE WRITE OPERATIONS =====
    def triple_write(
        self,
        workflow_id: str,
        node_id: str,
        path: str,
        content: str,
        metadata: Dict,
        vector: List[float],
        weaviate_write_func: callable = None
    ) -> Dict[str, bool]:
        """
        Atomic Triple Write:
        1. Write to Weaviate (semantic search)
        2. Write to Qdrant (hierarchical)
        3. Write to ChangeLog (audit)
        
        Returns dict with success status for each store
        """
        results = {
            'weaviate': False,
            'qdrant': False,
            'changelog': False,
            'atomic': False
        }
        
        try:
            # 1. Write to Weaviate (if callback provided)
            if weaviate_write_func:
                try:
                    weaviate_write_func({
                        'node_id': node_id,
                        'path': path,
                        'content': content,
                        'metadata': metadata
                    })
                    results['weaviate'] = True
                    print(f"   ✅ Weaviate: {node_id}")
                except Exception as e:
                    print(f"   ❌ Weaviate error: {e}")
            else:
                results['weaviate'] = True  # Skip if no callback
            
            # 2. Write to Qdrant
            if self.client:
                try:
                    qdrant_success = self._write_to_qdrant(
                        node_id, path, content, metadata, vector
                    )
                    results['qdrant'] = qdrant_success
                except Exception as e:
                    # MARKER_ENGRAM_QDRANT_FIX: Catch and log 400 Bad Request errors specifically
                    # Problem: Vector format mismatches causing silent failures
                    # Improvement needed: Add specific handling for 400 errors with diagnostics
                    if "400" in str(e):
                        logger.error(f"[QDRANT_400] Vector format error: {e}")
                    else:
                        logger.error(f"[Qdrant] Write error: {e}")
                    print(f"   ❌ Qdrant error: {e}")
            
            # 3. Write to ChangeLog
            try:
                self._write_to_changelog(
                    workflow_id=workflow_id,
                    node_id=node_id,
                    action='upsert',
                    status='success'
                )
                results['changelog'] = True
            except Exception as e:
                print(f"   ❌ ChangeLog error: {e}")
            
            # Check atomicity
            results['atomic'] = all([
                results.get('weaviate', True),
                results.get('qdrant', True),
                results.get('changelog', True)
            ])
            
            if results['atomic']:
                print(f"   ✅ TRIPLE WRITE ATOMIC: {node_id}")
            else:
                print(f"   ⚠️  TRIPLE WRITE PARTIAL: {results}")
                # Log the inconsistency
                self._write_to_changelog(
                    workflow_id=workflow_id,
                    node_id=node_id,
                    action='upsert',
                    status='partial_failure',
                    error=f"Atomic write failed: {results}"
                )
            
            return results
            
        except Exception as e:
            print(f"   ❌ Triple write error: {e}")
            self._write_to_changelog(
                workflow_id=workflow_id,
                node_id=node_id,
                action='upsert',
                status='failed',
                error=str(e)
            )
            return results
    
    # ===== QDRANT OPERATIONS =====
    def _write_to_qdrant(
        self,
        node_id: str,
        path: str,
        content: str,
        metadata: Dict,
        vector: List[float]
    ) -> bool:
        """Write node to Qdrant"""
        # MARKER_ENGRAM_QDRANT_FIX: Monitor vector format in upsert operations
        # Problem: 400 Bad Request when vector format is invalid or ID conversion fails
        # Audit needed: Verify vector dtype, shape, and ID range before upsert
        if not self.client:
            return False

        try:
            # Use UUID5 for collision-free point IDs (Phase 19 fix)
            point_id = uuid.uuid5(uuid.NAMESPACE_DNS, node_id).int & 0x7FFFFFFFFFFFFFFF
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    'node_id': node_id,
                    'path': path,
                    'content': content[:500],  # Limit payload size
                    'metadata': metadata,
                    'timestamp': time.time()
                }
            )

            self.client.upsert(
                collection_name=self.COLLECTION_NAMES['tree'],
                points=[point]
            )
            return True

        except Exception as e:
            # MARKER_ENGRAM_QDRANT_FIX: Log detailed error info for vector validation
            if "400" in str(e) or "bad request" in str(e).lower():
                logger.error(f"[QDRANT_400_VECTOR] Vector validation failed: {e}")
                logger.debug(f"  Point ID: {point_id}, Vector length: {len(vector) if vector else 'None'}")
            print(f"      Qdrant write error: {e}")
            return False
    
    def search_by_path(
        self,
        path_prefix: str,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Search for nodes by hierarchical path
        Example: "projects/python/ml" → all subnodes
        """
        if not self.client:
            return []
        
        try:
            # Use scroll API to get all points with matching path
            points, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAMES['tree'],
                limit=limit * 2  # Get more to filter
            )
            
            # Filter by path prefix
            results = []
            for point in points:
                path = point.payload.get('path', '')
                if path.startswith(path_prefix):
                    results.append({
                        'node_id': point.payload.get('node_id'),
                        'path': path,
                        'content': point.payload.get('content'),
                        'timestamp': point.payload.get('timestamp')
                    })
            
            return results[:limit]
            
        except Exception as e:
            print(f"   ❌ Path search error: {e}")
            return []
    
    def search_by_vector(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        collection: str = None,
        file_types_only: bool = True
    ) -> List[Dict]:
        """
        Semantic search in Qdrant collection.

        Args:
            collection: Collection name. Defaults to 'vetka_elisya' (main data).
            file_types_only: If True, filter to only scanned_file/browser_file types (excludes chat messages)
        """
        if not self.client:
            return []

        # Phase 68: Use vetka_elisya (has actual data) or specified collection
        collection_name = collection or 'vetka_elisya'

        try:
            # Phase 68.2: Filter to only scanned_file types (excludes chat and browser_file which have no tree nodes)
            search_filter = None
            if file_types_only and QDRANT_AVAILABLE:
                # MARKER_159.CLEAN_SEARCH_EXCLUDE_DELETED
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key='type',
                            match=MatchAny(any=['scanned_file'])  # Only scanned files have tree nodes
                        ),
                        FieldCondition(
                            key='deleted',
                            match=MatchValue(value=False)
                        ),
                    ]
                )

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )

            return [
                {
                    # Phase 68: Flexible payload mapping for different collection schemas
                    'id': str(r.id),
                    'node_id': r.payload.get('node_id') or r.payload.get('name') or str(r.id),
                    'path': r.payload.get('path', ''),
                    'name': r.payload.get('name', ''),
                    'content': r.payload.get('content', ''),
                    'type': r.payload.get('type', 'file'),
                    'score': r.score,
                    # Phase 69.4: Include metadata for UI display
                    'size': r.payload.get('size_bytes') or r.payload.get('size', 0),
                    'modified_time': r.payload.get('modified_time', 0),
                    'created_time': r.payload.get('created_time', 0),
                }
                for r in results
            ]

        except Exception as e:
            print(f"   ❌ Vector search error: {e}")
            return []
    
    def search_by_filename(
        self,
        filename_pattern: str,
        limit: int = 50,
        collection: str = None
    ) -> List[Dict]:
        """
        Phase 68.2: Search files by filename pattern.

        Uses Qdrant scroll with payload filtering to find files
        where the name contains the pattern (case-insensitive).

        Args:
            filename_pattern: Pattern to search in filename (e.g., "3d", "config")
            limit: Maximum results to return
            collection: Collection name (default: vetka_elisya)

        Returns:
            List of matching files with their metadata
        """
        if not self.client:
            logger.warning("[FILENAME] No Qdrant client available")
            return []

        collection_name = collection or 'vetka_elisya'
        pattern_lower = filename_pattern.lower()
        logger.info(f"[FILENAME] Starting search for '{filename_pattern}' in collection '{collection_name}'")

        try:
            # FIX_95.3_FILENAME_SCROLL: Try scanned_file filter first, fallback to all points
            search_filter = None
            if QDRANT_AVAILABLE:
                # MARKER_159.CLEAN_SEARCH_EXCLUDE_DELETED
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key='type',
                            match=MatchAny(any=['scanned_file'])
                        ),
                        FieldCondition(
                            key='deleted',
                            match=MatchValue(value=False)
                        ),
                    ]
                )

            # Get all points with filter (up to 2000 for filename matching)
            # Phase 68.2: Increased from 500 to 2000 for better coverage
            points, _ = self.client.scroll(
                collection_name=collection_name,
                limit=2000,  # Increased for better filename coverage
                scroll_filter=search_filter,
                with_payload=True,
                with_vectors=False
            )

            # FIX_95.3: Fallback - if no scanned_file found, search ALL points by path
            logger.info(f"[FILENAME] Scroll with type=scanned_file returned {len(points)} points")
            if not points:
                logger.info(f"[FILENAME] No scanned_file entries, searching all points for '{filename_pattern}'")
                points, _ = self.client.scroll(
                    collection_name=collection_name,
                    limit=2000,
                    scroll_filter=None,  # No type filter
                    with_payload=True,
                    with_vectors=False
                )
                logger.info(f"[FILENAME] Fallback scroll (no filter) returned {len(points)} points")

            # Filter by filename pattern (case-insensitive substring match)
            # FIX_95.3: Search in BOTH 'name' field AND last part of 'path'
            results = []
            for point in points:
                name = point.payload.get('name', '')
                path = point.payload.get('path', '')
                # Extract filename from path if name is empty
                if not name and path:
                    name = path.split('/')[-1]
                name_lower = name.lower()
                path_lower = path.lower()

                # Check if pattern is in filename OR in path
                if pattern_lower in name_lower or pattern_lower in path_lower:
                    # Score: exact match = 1.0, start match = 0.9, contains = 0.7
                    if name_lower == pattern_lower:
                        score = 1.0
                    elif name_lower.startswith(pattern_lower):
                        score = 0.9
                    else:
                        score = 0.7

                    results.append({
                        'id': str(point.id),
                        'node_id': point.payload.get('node_id') or point.payload.get('name') or str(point.id),
                        'path': point.payload.get('path', ''),
                        'name': name,
                        'content': point.payload.get('content', '')[:200],  # Limit content
                        'type': point.payload.get('type', 'file'),
                        'score': score,
                        # Phase 69.4: Include metadata for UI display
                        'size': point.payload.get('size_bytes') or point.payload.get('size', 0),
                        'modified_time': point.payload.get('modified_time', 0),
                        'created_time': point.payload.get('created_time', 0),
                    })

            # Sort by score (best matches first)
            results.sort(key=lambda x: x['score'], reverse=True)

            return results[:limit]

        except Exception as e:
            print(f"   ❌ Filename search error: {e}")
            return []

    def search_by_content(
        self,
        query: str,
        limit: int = 100,
        collection: str = None
    ) -> List[Dict]:
        """
        Phase 95.4: Keyword search by content (BM25-like fulltext search).

        Searches for query terms in content field using case-insensitive match.
        Used when Weaviate BM25 is unavailable.

        Args:
            query: Search query (will be split into terms)
            limit: Maximum results
            collection: Collection name (default: vetka_elisya)

        Returns:
            List of matching documents with relevance scores
        """
        import math

        if not self.client:
            logger.warning("[KEYWORD/QD] No Qdrant client available")
            return []

        collection_name = collection or 'vetka_elisya'
        query_lower = query.lower()
        terms = query_lower.split()

        logger.info(f"[KEYWORD/QD] Content search for '{query}' in '{collection_name}'")

        try:
            # Get all scanned files
            search_filter = None
            if QDRANT_AVAILABLE:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key='type',
                            match=MatchAny(any=['scanned_file'])
                        )
                    ]
                )

            points, _ = self.client.scroll(
                collection_name=collection_name,
                limit=2000,
                scroll_filter=search_filter,
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"[KEYWORD/QD] Found {len(points)} documents to search")

            # Score each document by term frequency
            results = []
            for point in points:
                content = point.payload.get('content', '').lower()
                path = point.payload.get('path', '').lower()
                name = point.payload.get('name', '')
                if not name:
                    name = path.split('/')[-1] if path else ''

                # Calculate BM25-like score
                score = 0.0
                term_matches = 0
                for term in terms:
                    if term in content:
                        count = content.count(term)
                        term_matches += 1
                        score += math.log(1 + count)
                    if term in path:
                        score += 0.5
                    if term in name.lower():
                        score += 1.0

                if term_matches > 0:
                    doc_len = len(content) + 1
                    score = score * (term_matches / len(terms)) / math.log(doc_len + 1)

                    results.append({
                        'id': str(point.id),
                        'node_id': point.payload.get('node_id') or name or str(point.id),
                        'path': point.payload.get('path', ''),
                        'name': name,
                        'content': point.payload.get('content', '')[:200],
                        'type': point.payload.get('type', 'file'),
                        'score': score,
                        'source': 'qdrant_keyword',
                        'size': point.payload.get('size_bytes') or point.payload.get('size', 0),
                        'modified_time': point.payload.get('modified_time', 0),
                        'created_time': point.payload.get('created_time', 0),
                    })

            results.sort(key=lambda x: x['score'], reverse=True)
            logger.info(f"[KEYWORD/QD] Found {len(results)} matches")
            return results[:limit]

        except Exception as e:
            logger.error(f"[KEYWORD/QD] Content search error: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about collections"""
        if not self.client:
            return {}
        
        try:
            stats = {}
            for col_key, col_name in self.COLLECTION_NAMES.items():
                info = self.client.get_collection(col_name)
                stats[col_key] = {
                    'name': col_name,
                    'points_count': info.points_count,
                    'vectors_count': info.vectors_count
                }
            return stats
        except Exception as e:
            print(f"   ❌ Stats error: {e}")
            return {}
    
    # ===== CHANGELOG OPERATIONS =====
    def _write_to_changelog(
        self,
        workflow_id: str,
        node_id: str,
        action: str,
        status: str = "success",
        error: Optional[str] = None,
        collection: str = "VetkaTree"
    ):
        """Write audit log entry"""
        entry = VetkaChangeLogEntry(
            workflow_id=workflow_id,
            action=action,
            collection=collection,
            node_id=node_id,
            timestamp=time.time(),
            status=status,
            error=error
        )
        
        self.changelog.append(entry)
        
        # Persist to file (simple approach)
        try:
            with open('/tmp/vetka_changelog.jsonl', 'a') as f:
                f.write(json.dumps(asdict(entry)) + '\n')
        except:
            pass
    
    def get_changelog(self, limit: int = 100) -> List[Dict]:
        """Get audit trail"""
        return [asdict(e) for e in self.changelog[-limit:]]

    def get_all_points(self, collection: str = None, limit: int = 1000) -> List:
        """
        Fetch all points from collection for visualization.

        Args:
            collection: Collection name (default: VetkaTree)
            limit: Maximum points to fetch

        Returns:
            List of PointStruct objects with payload
        """
        if not self.client:
            return []

        collection_name = collection or self.COLLECTION_NAMES['tree']

        try:
            result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False  # Don't need vectors for visualization
            )
            return result[0]  # Returns (points, next_page_offset)
        except Exception as e:
            print(f"[Qdrant] Error fetching points: {e}")
            return []

    # ===== PROXY METHODS FOR QDRANT CLIENT =====
    # These methods delegate to the underlying Qdrant client for direct operations

    def upsert(self, collection_name: str, points: List, **kwargs):
        """Proxy to underlying Qdrant client upsert"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.upsert(collection_name=collection_name, points=points, **kwargs)

    def get_collection(self, collection_name: str):
        """Proxy to underlying Qdrant client get_collection"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.get_collection(collection_name=collection_name)

    def delete_collection(self, collection_name: str):
        """Proxy to underlying Qdrant client delete_collection"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.delete_collection(collection_name=collection_name)

    def get_collections(self):
        """Proxy to underlying Qdrant client get_collections"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.get_collections()

    def create_collection(self, collection_name: str, vectors_config: dict = None, **kwargs):
        """Proxy to underlying Qdrant client create_collection"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        # Handle vector_config passed as either dict or VectorParams
        if vectors_config:
            if isinstance(vectors_config, dict):
                from qdrant_client.models import VectorParams, Distance
                size = vectors_config.get('size', 768)
                distance = vectors_config.get('distance', 'Cosine')
                vectors_config = VectorParams(size=size, distance=Distance[distance.upper()])
        return self.client.create_collection(collection_name=collection_name, vectors_config=vectors_config, **kwargs)

    # MARKER_118.5: scroll + retrieve proxies — EngramUserMemory needs these
    def scroll(self, collection_name: str, limit: int = 100, **kwargs):
        """Proxy to underlying Qdrant client scroll"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.scroll(collection_name=collection_name, limit=limit, **kwargs)

    def retrieve(self, collection_name: str, ids: list, **kwargs):
        """Proxy to underlying Qdrant client retrieve"""
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client.retrieve(collection_name=collection_name, ids=ids, **kwargs)


# ===== MARKER_103.7: CHAT HISTORY PERSISTENCE =====

def upsert_chat_message(
    group_id: str,
    message_id: str,
    sender_id: str,
    content: str,
    role: str = "user",  # "user" or "assistant"
    agent: str = None,
    model: str = None,
    metadata: Dict = None
) -> bool:
    """
    Upsert a chat message to VetkaGroupChat collection.

    This enables:
    - Long-term chat memory for Jarvis
    - Semantic search across conversations
    - Context retrieval for multi-turn dialogues

    Args:
        group_id: Group chat ID
        message_id: Unique message ID
        sender_id: Sender (user or agent ID)
        content: Message content
        role: "user" or "assistant"
        agent: Agent name (for assistant messages)
        model: Model used (for assistant messages)
        metadata: Additional metadata

    Returns:
        True if upserted successfully
    """
    client = get_qdrant_client()
    if not client or not client.client:
        logger.warning("[Chat] Qdrant not available for chat persistence")
        return False

    try:
        # Get embedding for semantic search
        from src.utils.embedding_service import get_embedding
        embedding = get_embedding(content[:2000])  # Truncate for efficiency

        if not embedding:
            logger.warning("[Chat] Failed to generate embedding")
            return False

        # Generate deterministic point ID from message_id
        import hashlib
        point_id = int(hashlib.md5(message_id.encode()).hexdigest()[:16], 16)

        payload = {
            "group_id": group_id,
            "message_id": message_id,
            "sender_id": sender_id,
            "content": content[:5000],  # Store more content in payload
            "role": role,
            "agent": agent,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        )

        client.client.upsert(
            collection_name=client.COLLECTION_NAMES['chat'],
            points=[point]
        )

        logger.debug(f"[Chat] Upserted message {message_id[:8]} to VetkaGroupChat")
        return True

    except Exception as e:
        logger.warning(f"[Chat] Upsert failed (graceful): {e}")
        return False


def search_chat_history(
    query: str,
    group_id: str = None,
    role: str = None,
    limit: int = 10
) -> List[Dict]:
    """
    Search chat history using semantic similarity.

    Args:
        query: Search query
        group_id: Optional filter by group
        role: Optional filter by role ("user" or "assistant")
        limit: Max results

    Returns:
        List of matching messages with scores
    """
    client = get_qdrant_client()
    if not client or not client.client:
        return []

    try:
        from src.utils.embedding_service import get_embedding
        query_vector = get_embedding(query)

        if not query_vector:
            return []

        # Build filter
        filter_conditions = []
        if group_id:
            filter_conditions.append(
                FieldCondition(key="group_id", match={"value": group_id})
            )
        if role:
            filter_conditions.append(
                FieldCondition(key="role", match={"value": role})
            )

        query_filter = None
        if filter_conditions:
            query_filter = Filter(must=filter_conditions)

        results = client.client.search(
            collection_name=client.COLLECTION_NAMES['chat'],
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit
        )

        return [
            {
                "score": hit.score,
                **hit.payload
            }
            for hit in results
        ]

    except Exception as e:
        logger.warning(f"[Chat] Search failed: {e}")
        return []


# ===== GLOBAL INSTANCE =====
_qdrant_instance = None

def get_qdrant_client() -> Optional[QdrantVetkaClient]:
    """Factory function - returns singleton Qdrant client"""
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantVetkaClient()
    return _qdrant_instance
