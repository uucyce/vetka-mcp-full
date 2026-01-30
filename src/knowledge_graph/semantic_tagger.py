# src/knowledge_graph/semantic_tagger.py
"""
VETKA Semantic Tagger - Phase 16
Dynamic tagging based on embeddings similarity and content analysis.

Instead of searching for a non-existent "tags" field in Qdrant,
this module uses vector similarity to find files semantically related
to a tag/topic.

@status: active
@phase: 96
@depends: qdrant_client, numpy, src.utils.embedding_service
@used_by: src.knowledge_graph.graph_builder
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchText, MatchValue
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticTagger:
    """
    Dynamic semantic tagging using Qdrant embeddings.

    Instead of stored tags, we compute semantic similarity to find
    files that belong to a conceptual "tag" or topic.
    """

    # Predefined semantic anchors for common tags
    TAG_ANCHORS = {
        "readme": ["README", "documentation", "overview", "getting started", "introduction"],
        "3d": ["three.js", "visualization", "3D", "render", "scene", "camera", "mesh"],
        "api": ["endpoint", "route", "REST", "HTTP", "request", "response", "API"],
        "config": ["configuration", "settings", "environment", "setup", ".env", "yaml"],
        "test": ["test", "spec", "unittest", "pytest", "jest", "coverage"],
        "agent": ["agent", "orchestrator", "workflow", "PM", "Dev", "QA", "eval"],
        "embedding": ["embedding", "vector", "Qdrant", "Weaviate", "semantic", "UMAP"],
        "phase": ["PHASE", "sprint", "milestone", "session", "status", "summary"],
        "knowledge": ["knowledge graph", "KG", "semantic", "edges", "nodes", "graph"],
        "visualization": ["visualization", "visual", "display", "render", "UI", "frontend"],
        "backend": ["backend", "server", "Flask", "API", "database", "Qdrant"],
        "memory": ["memory", "context", "vector", "embedding", "semantic memory"],
    }

    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection: str = "vetka_elisya",
        embedding_model: str = "embeddinggemma:300m"
    ):
        self.qdrant = qdrant_client
        self.collection = collection
        self.embedding_model = embedding_model
        self._anchor_embeddings: Dict[str, np.ndarray] = {}

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Delegate to unified EmbeddingService (Phase 36.1)"""
        from src.utils.embedding_service import get_embedding
        embedding = get_embedding(text)
        if embedding:
            return np.array(embedding)
        return None

    def _get_anchor_embedding(self, tag: str) -> Optional[np.ndarray]:
        """Get or compute embedding for a tag anchor."""
        tag_lower = tag.lower()

        if tag_lower in self._anchor_embeddings:
            return self._anchor_embeddings[tag_lower]

        # Get anchor words for this tag
        anchors = self.TAG_ANCHORS.get(tag_lower, [tag])
        anchor_text = " ".join(anchors)

        embedding = self._get_embedding(anchor_text)
        if embedding is not None:
            self._anchor_embeddings[tag_lower] = embedding

        return embedding

    def find_files_by_semantic_tag(
        self,
        tag: str,
        limit: int = 50,
        min_score: float = 0.35
    ) -> List[Dict]:
        """
        Find files semantically related to a tag using vector similarity.

        This replaces the broken build_graph_for_tag() that searched for
        a non-existent "tags" field.

        Args:
            tag: Semantic tag/topic to search for
            limit: Maximum number of results
            min_score: Minimum cosine similarity threshold

        Returns:
            List of file dicts with scores
        """
        if not self.qdrant:
            logger.warning("Qdrant client not available")
            return []

        # Get embedding for tag
        tag_embedding = self._get_anchor_embedding(tag)

        if tag_embedding is None or len(tag_embedding) == 0:
            logger.warning(f"Could not get embedding for tag: {tag}")
            return self._fallback_text_search(tag, limit)

        # Search by vector similarity
        try:
            # Phase 16 FIX: Filter ONLY scanned_file entries, exclude conversations
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=tag_embedding.tolist(),
                limit=limit,
                score_threshold=min_score,
                query_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="scanned_file"))
                    ]
                ),
                with_payload=True,
                with_vectors=True  # Need vectors for KG building
            )

            files = []
            for hit in results:
                files.append({
                    'id': str(hit.id),
                    'score': hit.score,
                    'name': hit.payload.get('name', 'unknown'),
                    'path': hit.payload.get('path', ''),
                    'extension': hit.payload.get('extension', ''),
                    'created_time': hit.payload.get('created_time', 0),
                    'modified_time': hit.payload.get('modified_time', 0),
                    'content': hit.payload.get('content', '')[:500] if hit.payload.get('content') else '',
                    'embedding': hit.vector if hit.vector else [],
                    'payload': hit.payload
                })

            logger.info(f"[SemanticTag] '{tag}' found {len(files)} files (threshold={min_score})")
            return files

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return self._fallback_text_search(tag, limit)

    def _fallback_text_search(self, tag: str, limit: int) -> List[Dict]:
        """
        Fallback to text-based search when semantic search fails.
        Searches in name, path, and content fields.
        """
        if not self.qdrant:
            return []

        try:
            # Scroll with text filter
            # Phase 16 FIX: Filter ONLY scanned_file entries
            results, _ = self.qdrant.scroll(
                collection_name=self.collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="scanned_file"))
                    ],
                    should=[
                        FieldCondition(key="name", match=MatchText(text=tag)),
                        FieldCondition(key="path", match=MatchText(text=tag)),
                        FieldCondition(key="content", match=MatchText(text=tag)),
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=True
            )

            files = []
            for point in results:
                files.append({
                    'id': str(point.id),
                    'score': 0.5,  # Default score for text match
                    'name': point.payload.get('name', 'unknown'),
                    'path': point.payload.get('path', ''),
                    'extension': point.payload.get('extension', ''),
                    'created_time': point.payload.get('created_time', 0),
                    'modified_time': point.payload.get('modified_time', 0),
                    'content': point.payload.get('content', '')[:500] if point.payload.get('content') else '',
                    'embedding': point.vector if point.vector else [],
                    'payload': point.payload
                })

            logger.info(f"[TextFallback] '{tag}' found {len(files)} files")
            return files

        except Exception as e:
            logger.error(f"Text search error: {e}")
            return []

    def auto_tag_file(self, file_embedding: np.ndarray) -> List[Dict]:
        """
        Automatically assign semantic tags to a file based on its embedding.

        Returns list of tags with confidence scores.
        """
        if file_embedding is None or len(file_embedding) == 0:
            return []

        tags = []
        file_norm = np.linalg.norm(file_embedding)

        if file_norm == 0:
            return []

        for tag_name in self.TAG_ANCHORS.keys():
            anchor_emb = self._get_anchor_embedding(tag_name)

            if anchor_emb is None:
                continue

            anchor_norm = np.linalg.norm(anchor_emb)
            if anchor_norm == 0:
                continue

            # Cosine similarity
            similarity = np.dot(file_embedding, anchor_emb) / (file_norm * anchor_norm)

            if similarity > 0.3:  # Threshold for tag assignment
                tags.append({
                    'tag': tag_name,
                    'confidence': float(similarity)
                })

        # Sort by confidence
        tags.sort(key=lambda x: x['confidence'], reverse=True)

        return tags[:5]  # Top 5 tags

    def get_available_tags(self) -> List[str]:
        """Return list of predefined semantic tags."""
        return list(self.TAG_ANCHORS.keys())

    def add_custom_tag(self, tag_name: str, anchor_words: List[str]):
        """Add a custom semantic tag with anchor words."""
        self.TAG_ANCHORS[tag_name.lower()] = anchor_words
        # Clear cached embedding to force recomputation
        if tag_name.lower() in self._anchor_embeddings:
            del self._anchor_embeddings[tag_name.lower()]

    def get_tag_description(self, tag: str) -> Optional[Dict]:
        """Get description and anchor words for a tag."""
        tag_lower = tag.lower()
        if tag_lower in self.TAG_ANCHORS:
            return {
                'tag': tag_lower,
                'anchor_words': self.TAG_ANCHORS[tag_lower],
                'description': f"Files related to: {', '.join(self.TAG_ANCHORS[tag_lower])}"
            }
        return None
