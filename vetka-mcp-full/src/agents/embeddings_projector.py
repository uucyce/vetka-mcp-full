#!/usr/bin/env python3
"""
VETKA Phase 8.0 - EmbeddingsProjector
UMAP/PCA projection for 3D visualization of embeddings

Transforms high-dimensional embeddings into 3D space for VETKA visualization.

@status: active
@phase: 96
@depends: numpy, sklearn, umap
@used_by: visualization, tree_renderer
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ProjectionMethod(Enum):
    """Available projection methods"""
    UMAP = auto()
    PCA = auto()
    TSNE = auto()


class EmbeddingsProjector:
    """
    Project high-dimensional embeddings to 3D for visualization.

    Phase 8.0: Supports multiple projection methods:
    - UMAP: Best for preserving local structure
    - PCA: Fast, linear projection
    - t-SNE: Good for clusters (slower)

    Output format compatible with VETKA 3D visualization.
    """

    def __init__(
        self,
        method: ProjectionMethod = ProjectionMethod.PCA,
        n_components: int = 3,
        random_state: int = 42,
    ):
        """
        Initialize EmbeddingsProjector.

        Args:
            method: Projection method (UMAP, PCA, t-SNE)
            n_components: Output dimensions (default: 3 for 3D)
            random_state: Random seed for reproducibility
        """
        self.method = method
        self.n_components = n_components
        self.random_state = random_state
        self._projector = None
        self._is_fitted = False

    def _get_projector(self):
        """Lazy initialization of projector."""
        if self._projector is not None:
            return self._projector

        if self.method == ProjectionMethod.UMAP:
            try:
                import umap
                self._projector = umap.UMAP(
                    n_components=self.n_components,
                    random_state=self.random_state,
                    n_neighbors=15,
                    min_dist=0.1,
                    metric='cosine',
                )
            except ImportError:
                logger.warning("UMAP not installed, falling back to PCA")
                self.method = ProjectionMethod.PCA
                return self._get_projector()

        elif self.method == ProjectionMethod.PCA:
            from sklearn.decomposition import PCA
            self._projector = PCA(
                n_components=self.n_components,
                random_state=self.random_state,
            )

        elif self.method == ProjectionMethod.TSNE:
            from sklearn.manifold import TSNE
            self._projector = TSNE(
                n_components=self.n_components,
                random_state=self.random_state,
                perplexity=min(30, max(5, len(self._last_embeddings) - 1)) if hasattr(self, '_last_embeddings') else 30,
            )

        return self._projector

    def project(
        self,
        embeddings: Union[List[List[float]], np.ndarray],
        labels: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Project embeddings to 3D space.

        Args:
            embeddings: High-dimensional embeddings (N x D)
            labels: Optional labels for each point
            metadata: Optional metadata for each point

        Returns:
            {
                'points': [[x, y, z], ...],
                'labels': ['label1', ...],
                'metadata': [{...}, ...],
                'stats': {
                    'original_dim': D,
                    'n_points': N,
                    'method': 'PCA'
                }
            }
        """
        # Convert to numpy array
        embeddings = np.array(embeddings)
        self._last_embeddings = embeddings

        n_points, original_dim = embeddings.shape

        if n_points < 2:
            logger.warning("Need at least 2 points for projection")
            return {
                'points': embeddings[:, :3].tolist() if original_dim >= 3 else [[0, 0, 0]] * n_points,
                'labels': labels or [],
                'metadata': metadata or [],
                'stats': {
                    'original_dim': original_dim,
                    'n_points': n_points,
                    'method': 'identity',
                    'error': 'Not enough points'
                }
            }

        # Get projector
        projector = self._get_projector()

        # Project embeddings
        try:
            if self.method == ProjectionMethod.TSNE:
                # t-SNE doesn't have transform, only fit_transform
                projected = projector.fit_transform(embeddings)
            else:
                projected = projector.fit_transform(embeddings)
                self._is_fitted = True
        except Exception as e:
            logger.error(f"Projection failed: {e}")
            # Fallback to simple truncation
            projected = embeddings[:, :self.n_components]
            if projected.shape[1] < self.n_components:
                # Pad with zeros if needed
                padding = np.zeros((n_points, self.n_components - projected.shape[1]))
                projected = np.hstack([projected, padding])

        # Normalize to [-1, 1] range for visualization
        projected = self._normalize(projected)

        result = {
            'points': projected.tolist(),
            'labels': labels or [f"point_{i}" for i in range(n_points)],
            'metadata': metadata or [{}] * n_points,
            'stats': {
                'original_dim': original_dim,
                'n_points': n_points,
                'method': self.method.name,
                'variance_explained': self._get_variance_explained() if self.method == ProjectionMethod.PCA else None,
            }
        }

        return result

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data to [-1, 1] range."""
        min_vals = data.min(axis=0)
        max_vals = data.max(axis=0)
        range_vals = max_vals - min_vals

        # Avoid division by zero
        range_vals[range_vals == 0] = 1

        normalized = 2 * (data - min_vals) / range_vals - 1
        return normalized

    def _get_variance_explained(self) -> Optional[List[float]]:
        """Get variance explained (PCA only)."""
        if self.method == ProjectionMethod.PCA and self._projector is not None:
            try:
                return self._projector.explained_variance_ratio_.tolist()
            except AttributeError:
                return None
        return None

    def transform_new(self, embeddings: Union[List[List[float]], np.ndarray]) -> List[List[float]]:
        """
        Transform new embeddings using fitted projector.

        Only works with PCA and UMAP (not t-SNE).
        """
        if not self._is_fitted:
            raise ValueError("Projector not fitted. Call project() first.")

        if self.method == ProjectionMethod.TSNE:
            raise ValueError("t-SNE doesn't support transform on new data")

        embeddings = np.array(embeddings)
        projected = self._projector.transform(embeddings)
        normalized = self._normalize(projected)
        return normalized.tolist()

    def project_for_vetka(
        self,
        embeddings: Union[List[List[float]], np.ndarray],
        labels: Optional[List[str]] = None,
        node_ids: Optional[List[str]] = None,
        colors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Project embeddings with VETKA-specific output format.

        Returns format ready for VETKA 3D visualization API.
        """
        result = self.project(embeddings, labels)

        # Convert to VETKA node format
        nodes = []
        for i, (point, label) in enumerate(zip(result['points'], result['labels'])):
            node = {
                'id': node_ids[i] if node_ids else f"node_{i}",
                'position': {
                    'x': point[0],
                    'y': point[1],
                    'z': point[2],
                },
                'label': label,
                'color': colors[i] if colors else self._get_color_for_index(i),
            }
            nodes.append(node)

        return {
            'nodes': nodes,
            'projection_stats': result['stats'],
            'format': 'vetka_3d',
        }

    def _get_color_for_index(self, index: int) -> str:
        """Generate color based on index."""
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8B500', '#00CED1',
        ]
        return colors[index % len(colors)]

    def compute_clusters(
        self,
        embeddings: Union[List[List[float]], np.ndarray],
        n_clusters: int = 5,
    ) -> Dict[str, Any]:
        """
        Compute clusters from embeddings.

        Args:
            embeddings: Input embeddings
            n_clusters: Number of clusters

        Returns:
            {
                'cluster_labels': [0, 1, 2, ...],
                'centroids': [[x, y, z], ...],
                'n_clusters': 5
            }
        """
        from sklearn.cluster import KMeans

        embeddings = np.array(embeddings)

        # Cluster in original space
        kmeans = KMeans(
            n_clusters=min(n_clusters, len(embeddings)),
            random_state=self.random_state,
            n_init=10,
        )
        cluster_labels = kmeans.fit_predict(embeddings)

        # Project centroids
        result = self.project(kmeans.cluster_centers_)

        return {
            'cluster_labels': cluster_labels.tolist(),
            'centroids': result['points'],
            'n_clusters': len(np.unique(cluster_labels)),
        }


def embeddings_projector_factory(
    method: str = "PCA",
    n_components: int = 3,
) -> EmbeddingsProjector:
    """Factory for creating EmbeddingsProjector instance."""
    method_enum = ProjectionMethod[method.upper()]
    return EmbeddingsProjector(method=method_enum, n_components=n_components)


# Convenience function
def project_to_3d(
    embeddings: Union[List[List[float]], np.ndarray],
    labels: Optional[List[str]] = None,
    method: str = "PCA",
) -> Dict[str, Any]:
    """Quick helper to project embeddings to 3D."""
    projector = embeddings_projector_factory(method=method)
    return projector.project(embeddings, labels)
