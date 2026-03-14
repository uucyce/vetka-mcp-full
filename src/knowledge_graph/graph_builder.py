# src/knowledge_graph/graph_builder.py
"""
VETKA Knowledge Graph Builder - Phase 16
Builds semantic graph from Qdrant embeddings using cosine similarity.

Phase 16 Changes:
- Fixed build_graph_for_tag() to use SemanticTagger instead of non-existent "tags" field
- Added _build_graph_from_file_data() for building graph from file data directly
- Added _find_semantic_edges() for computing edges from embeddings

@status: active
@phase: 96
@depends: qdrant_client, networkx, numpy, semantic_tagger
@used_by: src.api.routes.tree_routes, src.visualizer.tree_renderer
"""

from qdrant_client import QdrantClient
import networkx as nx
import numpy as np
from typing import List, Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class VETKAKnowledgeGraphBuilder:
    """
    Builds knowledge graph from Qdrant embeddings.
    Uses Gemma embedding thresholds for edge classification.
    """

    # Gemma embedding thresholds (calibrated for 768-dim vectors)
    THRESHOLDS = {
        "near_duplicate": 0.92,   # Almost identical content
        "similar_to": 0.75,       # Strong semantic similarity
        "depends_on": 0.45,       # Weak but meaningful connection
        "min_edge": 0.45          # Below this = no edge
    }

    # Edge colors for Three.js (Itten palette)
    EDGE_COLORS = {
        "near_duplicate": "#E63946",  # Red - danger/duplicate
        "similar_to": "#4A6B8A",      # Muted blue - relation
        "depends_on": "#8AA0B0"       # Light blue-gray - weak
    }

    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.client = QdrantClient(url=f"http://{qdrant_host}:{qdrant_port}")
        self.collection_name = "vetka_elisya"  # Default collection

    def build_graph_for_files(
        self,
        file_ids: List[str],
        collection: str = None
    ) -> nx.Graph:
        """
        Build knowledge graph for a set of files.

        Args:
            file_ids: List of file IDs (point IDs in Qdrant)
            collection: Qdrant collection name (default: vetka_files)

        Returns:
            NetworkX graph with nodes and weighted edges
        """
        if collection:
            self.collection_name = collection

        graph = nx.Graph()

        # Fetch all points with vectors
        points = self._fetch_points(file_ids)

        if not points:
            logger.warning("No points fetched from Qdrant")
            return graph

        # Add nodes with full payload (needed for Y position calculation by time)
        for point in points:
            payload = point.get("payload", {})
            graph.add_node(
                point["id"],
                path=payload.get("path", "unknown"),
                name=payload.get("name", "unknown"),
                language=payload.get("language", "unknown"),
                embedding=point.get("vector", []),
                payload=payload  # Store full payload for time-based Y positioning
            )

        # Find edges using similarity
        edges = self._find_edges(points)

        for edge in edges:
            graph.add_edge(
                edge["source"],
                edge["target"],
                weight=edge["score"],
                edge_type=edge["type"],
                color=self.EDGE_COLORS.get(edge["type"], "#8AA0B0")
            )

        logger.info(f"Built graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph

    def _fetch_points(self, file_ids: List[str]) -> List[Dict]:
        """Fetch points from Qdrant with vectors."""
        try:
            # Convert string IDs to integers for Qdrant
            int_ids = []
            for fid in file_ids:
                try:
                    int_ids.append(int(fid))
                except (ValueError, TypeError):
                    logger.warning(f"Skipping non-integer ID: {fid}")

            if not int_ids:
                logger.warning("No valid integer IDs to fetch, using scroll fallback")
                raise ValueError("No valid IDs")

            # Try to fetch by IDs
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=int_ids,
                with_vectors=True,
                with_payload=True
            )
            return [
                {
                    "id": str(point.id),
                    "vector": point.vector,
                    "payload": point.payload or {}
                }
                for point in result
            ]
        except Exception as e:
            logger.error(f"Failed to fetch points by IDs: {e}")
            # Fallback: scroll all points
            try:
                result, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    with_vectors=True,
                    with_payload=True
                )
                return [
                    {
                        "id": str(point.id),
                        "vector": point.vector,
                        "payload": point.payload or {}
                    }
                    for point in result
                ]
            except Exception as e2:
                logger.error(f"Scroll fallback also failed: {e2}")
                return []

    def _find_edges(self, points: List[Dict]) -> List[Dict]:
        """
        Find edges between points using Qdrant recommend API.
        Uses cosine similarity thresholds.
        """
        edges = []
        seen_pairs: Set[tuple] = set()

        for point in points:
            point_id = point["id"]
            vector = point.get("vector")

            if not vector:
                continue

            try:
                # Search for similar points
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    limit=20,  # Top 20 similar
                    score_threshold=self.THRESHOLDS["min_edge"]
                )

                for scored_point in results:
                    target_id = str(scored_point.id)
                    score = scored_point.score

                    # Skip self
                    if target_id == point_id:
                        continue

                    # Skip if already seen (undirected graph)
                    pair = tuple(sorted([point_id, target_id]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    # Classify edge type
                    edge_type = self._classify_edge(score)
                    if edge_type:
                        edges.append({
                            "source": point_id,
                            "target": target_id,
                            "score": score,
                            "type": edge_type
                        })

            except Exception as e:
                logger.warning(f"Failed to find edges for {point_id}: {e}")

        return edges

    def _classify_edge(self, score: float) -> Optional[str]:
        """Classify edge type based on cosine similarity score."""
        if score >= self.THRESHOLDS["near_duplicate"]:
            return "near_duplicate"
        elif score >= self.THRESHOLDS["similar_to"]:
            return "similar_to"
        elif score >= self.THRESHOLDS["depends_on"]:
            return "depends_on"
        return None

    def export_for_threejs(self, graph: nx.Graph) -> Dict:
        """
        Export graph in format suitable for Three.js rendering.

        Returns:
            {
                "nodes": [{"id", "path", "name", "language", "x", "y", "z"}],
                "edges": [{"source", "target", "type", "color", "weight"}]
            }
        """
        nodes = []
        for node_id, data in graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "path": data.get("path", "unknown"),
                "name": data.get("name", "unknown"),
                "language": data.get("language", "unknown"),
                # Positions will be calculated by VETKAPositionCalculator
                "x": 0,
                "y": 0,
                "z": 0
            })

        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("edge_type", "depends_on"),
                "color": data.get("color", "#8AA0B0"),
                "weight": data.get("weight", 0.5)
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0
            }
        }

    def build_graph_for_tag(self, tag: str, collection: str = None) -> nx.Graph:
        """
        Build Knowledge Graph for files semantically related to a tag.

        Phase 16: Uses SemanticTagger instead of broken "tags" field search.
        The Qdrant payload does NOT have a "tags" field, so we use semantic
        similarity to find files related to the tag concept.
        """
        from .semantic_tagger import SemanticTagger

        collection = collection or self.collection_name

        # Use semantic tagger to find related files
        tagger = SemanticTagger(
            qdrant_client=self.client,
            collection=collection
        )

        files = tagger.find_files_by_semantic_tag(tag, limit=100, min_score=0.35)

        if not files:
            logger.warning(f"No files found for tag: {tag}")
            return nx.Graph()

        # Build graph from found files
        graph = nx.Graph()

        # Add nodes with embeddings
        for file_data in files:
            node_id = file_data['id']
            graph.add_node(
                node_id,
                name=file_data['name'],
                path=file_data['path'],
                embedding=file_data.get('embedding', []),
                payload=file_data.get('payload', {}),
                tag_score=file_data['score']  # Relevance to tag
            )

        # Find edges using embedding similarity
        self._find_semantic_edges_on_graph(graph)

        logger.info(
            f"[KG] Built graph for tag '{tag}': "
            f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )

        return graph

    def _find_semantic_edges_on_graph(self, graph: nx.Graph):
        """
        Find edges between nodes based on embedding similarity.
        Uses VETKA thresholds from Technical Specification.
        Modifies graph in place.
        """
        nodes = list(graph.nodes())

        for i, node_i in enumerate(nodes):
            emb_i = graph.nodes[node_i].get('embedding', [])
            if not emb_i or len(emb_i) == 0:
                continue

            emb_i = np.array(emb_i)
            norm_i = np.linalg.norm(emb_i)

            if norm_i == 0:
                continue

            for j, node_j in enumerate(nodes):
                if i >= j:  # Avoid duplicates and self-loops
                    continue

                emb_j = graph.nodes[node_j].get('embedding', [])
                if not emb_j or len(emb_j) == 0:
                    continue

                emb_j = np.array(emb_j)
                norm_j = np.linalg.norm(emb_j)

                if norm_j == 0:
                    continue

                # Cosine similarity
                similarity = float(np.dot(emb_i, emb_j) / (norm_i * norm_j))

                # Classify edge type
                if similarity > self.THRESHOLDS['near_duplicate']:
                    edge_type = 'near_duplicate'
                elif similarity > self.THRESHOLDS['similar_to']:
                    edge_type = 'similar_to'
                elif similarity > self.THRESHOLDS['depends_on']:
                    edge_type = 'depends_on'
                else:
                    continue  # No edge

                graph.add_edge(
                    node_i, node_j,
                    weight=similarity,
                    edge_type=edge_type,
                    color=self.EDGE_COLORS[edge_type]
                )

    def _build_graph_from_file_data(self, files: List[Dict]) -> nx.Graph:
        """
        Build graph directly from file data (when IDs not available).
        Used when creating VETKA from search selection.

        Phase 16: New method for building graph from frontend file selection.
        """
        graph = nx.Graph()

        for file_data in files:
            node_id = (
                file_data.get('qdrant_id') or
                file_data.get('id') or
                file_data.get('path', str(id(file_data)))
            )

            graph.add_node(
                str(node_id),
                name=file_data.get('name', 'unknown'),
                path=file_data.get('path', ''),
                embedding=file_data.get('embedding', []),
                payload={
                    'name': file_data.get('name', ''),
                    'path': file_data.get('path', ''),
                    'extension': file_data.get('extension', ''),
                    'content': file_data.get('content', ''),
                    'created_time': file_data.get('created_time', 0),
                    'modified_time': file_data.get('modified_time', 0),
                }
            )

        # Find semantic edges
        self._find_semantic_edges_on_graph(graph)

        logger.info(
            f"[KG] Built graph from file data: "
            f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )

        return graph
