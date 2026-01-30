# Building Knowledge Graphs from Embeddings: VETKA Technical Specification

The VETKA project can transform file embeddings into a rich, navigable 3D knowledge graph by combining proven 2025 techniques: Qdrant's vector similarity for edge discovery, UMAP for semantic positioning, HDBSCAN for hierarchical clustering, and Three.js force-directed layouts with axis constraints. This specification provides the exact thresholds, parameters, and code patterns needed for implementation.

## Gemma embedding thresholds vary dramatically from older models

Modern embedding models like Gemma produce significantly lower cosine similarity scores than predecessors. Where OpenAI's ada-002 returned ~85% similarity for related documents, text-embedding-3 and Gemma embeddings return ~45%. This critical insight shapes every threshold in your system.

**VETKA-specific similarity thresholds for Gemma embeddings:**

| Relationship Type | Cosine Threshold | Edge Semantics |
|-------------------|------------------|----------------|
| Near-duplicate | >0.92 | Z-axis compression, same content |
| Highly related | 0.75-0.92 | "similar_to", "alternative" |
| Semantically connected | 0.45-0.75 | "depends_on", "continues" |
| Weak connection | 0.30-0.45 | Display only on zoom |
| Noise floor | <0.30 | No edge |

Google's EmbeddingGemma documentation confirms these ranges: identical-meaning sentences score ~0.80, related topics ~0.45, and unrelated content ~0.22. **Calibrate empirically** by sampling 1000 random document pairs and plotting the similarity distribution to find natural cluster boundaries in your specific corpus.

## Prerequisite inference requires asymmetric signals beyond cosine similarity

Pure cosine similarity is symmetric—it cannot distinguish "A depends on B" from "B depends on A". For directed edges like prerequisites and continuation relationships, VETKA needs asymmetric features:

```python
def compute_directed_edge_features(emb_a, emb_b, meta_a, meta_b):
    """Features for classifying prerequisite/continuation relationships."""
    cosine_sim = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
    
    # Asymmetric projections capture directionality
    proj_a_on_b = np.dot(emb_a, emb_b) / np.linalg.norm(emb_b)
    proj_b_on_a = np.dot(emb_b, emb_a) / np.linalg.norm(emb_a)
    
    # Temporal ordering is essential for "continues" relationships
    time_delta = meta_b['created_at'] - meta_a['created_at']
    is_temporal_successor = time_delta > 0
    
    return {
        'base_similarity': cosine_sim,
        'a_depends_on_b': proj_a_on_b,  # Higher means A needs B
        'b_depends_on_a': proj_b_on_a,  # Higher means B needs A
        'is_continuation': is_temporal_successor and cosine_sim > 0.60,
        'dependency_ratio': proj_a_on_b / (proj_b_on_a + 1e-8)
    }
```

For true prerequisite detection in learning paths, academic research recommends training a lightweight classifier (Random Forest or small neural network) on manually labeled pairs using these asymmetric features. The PREREQ model achieves this using Siamese networks on embedding differences.

## UMAP with independent axis computation best serves VETKA's 3D constraints

Since Y-axis is already fixed to creation time, VETKA needs dimensionality reduction only for X (semantic similarity) and Z (depth/clusters). The optimal approach separates these concerns:

```python
import umap
from hdbscan import HDBSCAN
import numpy as np

class VETKAPositionCalculator:
    def __init__(self, gemma_embeddings, creation_times):
        self.embeddings = gemma_embeddings
        self.times = creation_times
        
    def compute_positions(self):
        # Y-AXIS: Time (normalized, already working in VETKA)
        y_positions = (self.times - self.times.min()) / (self.times.max() - self.times.min())
        
        # X-AXIS: Semantic similarity via 1D UMAP
        semantic_reducer = umap.UMAP(
            n_components=1,
            n_neighbors=15,      # Balance local/global structure
            min_dist=0.1,        # Tight clusters but visible separation
            metric='cosine',     # Essential for text embeddings
            random_state=42
        )
        x_positions = semantic_reducer.fit_transform(self.embeddings).flatten()
        
        # Z-AXIS: Cluster depth via HDBSCAN hierarchy
        clusterer = HDBSCAN(
            min_cluster_size=10,
            min_samples=5,
            metric='euclidean',  # On raw embeddings
            cluster_selection_method='eom'
        )
        clusterer.fit(self.embeddings)
        
        # Convert cluster probabilities to depth (higher confidence = deeper)
        z_positions = clusterer.probabilities_
        
        return np.column_stack([x_positions, y_positions, z_positions])
```

**UMAP parameter guidance for knowledge graphs:**

| Parameter | VETKA Recommendation | Rationale |
|-----------|---------------------|-----------|
| n_neighbors | 15-30 | Balances local detail with global relationships |
| min_dist | 0.05-0.15 | Allows tight clusters while maintaining separation |
| metric | 'cosine' | Standard for semantic embeddings |
| n_components | 1 (for X-axis only) | Y is fixed, Z computed separately |

For **real-time updates** when new files are added, use Parametric UMAP which learns a neural network projection function:

```python
from umap.parametric_umap import ParametricUMAP

# Initial training
p_reducer = ParametricUMAP(n_components=1, n_neighbors=15, metric='cosine')
p_reducer.fit(existing_embeddings)

# Transform new files in ~1ms instead of recomputing
new_x_position = p_reducer.transform(new_embedding.reshape(1, -1))
```

## Hyperbolic embeddings naturally encode hierarchy for the Z-axis

While UMAP works well for semantic similarity, **Poincaré ball embeddings** are mathematically superior for representing hierarchies. Hyperbolic space has exponentially growing volume, allowing tree structures to embed with arbitrarily low distortion—impossible in Euclidean space.

```python
from gensim.models.poincare import PoincareModel
import numpy as np

# If you have explicit file relationships (folder structure, references)
relations = [
    ('project_root', 'src_folder'),
    ('src_folder', 'main.py'),
    ('src_folder', 'utils.py'),
    # ... semantic relationships extracted from similarity
]

poincare_model = PoincareModel(relations, size=2, negative=10)
poincare_model.train(epochs=100)

# Distance from origin = depth in hierarchy
def get_z_from_poincare(file_id):
    embedding = poincare_model.kv[file_id]
    return np.linalg.norm(embedding)  # Root near 0, leaves near 1
```

**Practical hybrid approach:** Use Poincaré embeddings for Z-axis if you have explicit parent-child relationships. Use HDBSCAN cluster depth if working purely from embedding similarity.

## HDBSCAN outperforms alternatives for document clustering

HDBSCAN handles varying-density clusters without requiring a fixed cluster count—essential for document collections where some topics have many files and others few.

**Recommended HDBSCAN configuration for VETKA:**

```python
from hdbscan import HDBSCAN

# Fine-grained clustering (near-duplicate detection)
clusterer_fine = HDBSCAN(
    min_cluster_size=5,
    min_samples=3,
    metric='cosine',
    cluster_selection_method='leaf',  # More granular
    prediction_data=True  # Enable approximate_predict for new files
)

# Coarse topic clustering
clusterer_coarse = HDBSCAN(
    min_cluster_size=20,
    min_samples=10,
    metric='cosine',
    cluster_selection_method='eom',  # Excess of mass, more stable
    cluster_selection_epsilon=0.3    # Merge clusters closer than this
)
```

**Handling noise points** (documents not assigned to any cluster):

```python
from hdbscan import approximate_predict

# Option 1: Soft assignment to nearest cluster
soft_labels, strengths = approximate_predict(clusterer, noise_embeddings)

# Option 2: Assign to nearest cluster centroid if similarity > threshold
for idx in np.where(labels == -1)[0]:
    nearest_cluster = find_nearest_cluster_centroid(embeddings[idx], centroids)
    if similarity(embeddings[idx], centroids[nearest_cluster]) > 0.7:
        labels[idx] = nearest_cluster
```

For community detection in the knowledge graph structure, **Leiden algorithm** is strongly recommended over Louvain—Louvain can produce up to 16% disconnected communities, while Leiden guarantees well-connected results.

## Qdrant integration follows batch-search patterns for efficiency

The knowledge graph construction pipeline uses Qdrant's APIs strategically:

```python
from qdrant_client import QdrantClient, models
import networkx as nx
import asyncio

class VETKAKnowledgeGraphBuilder:
    def __init__(self, qdrant_url: str, collection: str):
        self.client = QdrantClient(url=qdrant_url)
        self.collection = collection
        self.graph = nx.DiGraph()  # Directed for prerequisite edges
        
        self.thresholds = {
            'near_duplicate': 0.92,
            'similar_to': 0.75,
            'depends_on': 0.45
        }
    
    async def build_graph(self):
        """Batch process all documents to extract edges."""
        # Scroll through all points
        all_points = []
        offset = None
        while True:
            response, offset = self.client.scroll(
                collection_name=self.collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_points.extend(response)
            if offset is None:
                break
        
        # Batch search for edges using recommend API
        point_ids = [p.id for p in all_points]
        for batch_start in range(0, len(point_ids), 50):
            batch = point_ids[batch_start:batch_start + 50]
            edges = await self._find_edges_for_batch(batch)
            self._add_edges(edges)
        
        return self.graph
    
    async def _find_edges_for_batch(self, point_ids):
        """Use recommend API for efficient similarity discovery."""
        edges = []
        for pid in point_ids:
            similar = self.client.recommend(
                collection_name=self.collection,
                positive=[pid],
                limit=20,
                score_threshold=self.thresholds['depends_on']
            )
            for hit in similar:
                if hit.id != pid:
                    edge_type = self._classify_edge(hit.score)
                    edges.append({
                        'source': pid,
                        'target': hit.id,
                        'weight': hit.score,
                        'type': edge_type
                    })
        return edges
    
    def _classify_edge(self, score):
        if score > self.thresholds['near_duplicate']:
            return 'near_duplicate'
        elif score > self.thresholds['similar_to']:
            return 'similar_to'
        else:
            return 'depends_on'
    
    def add_file_incrementally(self, file_id, embedding, metadata):
        """Real-time update when new file is added."""
        # 1. Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(id=file_id, vector=embedding, payload=metadata)]
        )
        
        # 2. Find similar documents
        similar = self.client.recommend(
            collection_name=self.collection,
            positive=[file_id],
            limit=20,
            score_threshold=self.thresholds['depends_on']
        )
        
        # 3. Add node and edges to graph
        self.graph.add_node(file_id, **metadata)
        for hit in similar:
            if hit.id != file_id:
                self.graph.add_edge(
                    file_id, hit.id,
                    weight=hit.score,
                    type=self._classify_edge(hit.score)
                )
        
        return len(similar)
    
    def export_for_threejs(self):
        """Export in Three.js force-graph format."""
        return {
            'nodes': [
                {'id': n, 'group': self.graph.nodes[n].get('cluster', 0), **self.graph.nodes[n]}
                for n in self.graph.nodes()
            ],
            'links': [
                {'source': u, 'target': v, 'value': d['weight'], 'type': d['type']}
                for u, v, d in self.graph.edges(data=True)
            ]
        }
```

## Three.js visualization uses constrained force-directed layout

The **3d-force-graph** library (5.6k GitHub stars) provides the ideal foundation, with d3-force-3d physics supporting axis constraints:

```javascript
import ForceGraph3D from '3d-force-graph';
import * as d3 from 'd3';

const Graph = ForceGraph3D()(document.getElementById('graph-container'))
    .graphData(graphData)
    
    // CONSTRAIN Y-AXIS TO TIME (strong force)
    .d3Force('y', d3.forceY(node => timeScale(node.createdAt)).strength(1.0))
    
    // X-AXIS: SEMANTIC SIMILARITY (moderate force, allow clustering)
    .d3Force('x', d3.forceX(node => node.semanticX).strength(0.3))
    
    // Z-AXIS: CLUSTER DEPTH (moderate force)
    .d3Force('z', d3.forceZ(node => node.clusterDepth * 50).strength(0.3))
    
    // EDGE FORCES: Similar documents attract
    .d3Force('link', d3.forceLink()
        .id(d => d.id)
        .distance(link => (1 - link.value) * 100)  // Higher similarity = shorter edge
        .strength(link => link.value * 0.5))
    
    // NODE STYLING BY EDGE TYPE
    .nodeColor(node => clusterColorScale(node.group))
    .nodeVal(node => Math.sqrt(Graph.graph.degree(node.id)))
    
    // EDGE STYLING BY RELATIONSHIP TYPE
    .linkColor(link => edgeTypeColors[link.type])
    .linkWidth(link => link.value * 3)
    .linkCurvature(0.25);  // Curved edges improve readability
```

**Performance optimization for large file collections:**

```javascript
// Use InstancedMesh for >1000 nodes
const geometry = new THREE.SphereGeometry(1, 8, 8);
const material = new THREE.MeshLambertMaterial();
const instancedMesh = new THREE.InstancedMesh(geometry, material, nodeCount);

Graph.nodeThreeObject(node => {
    const dummy = new THREE.Object3D();
    dummy.scale.setScalar(node.size);
    return dummy;
});

// BufferGeometry for edge rendering
Graph.linkThreeObjectExtend(true)
    .linkThreeObject(link => {
        // Use pre-allocated buffer geometry
        return edgePool.get(link.type);
    });
```

| Node Count | Recommended Approach |
|------------|---------------------|
| <1,000 | Default 3d-force-graph |
| 1,000-10,000 | InstancedMesh + BufferGeometry |
| 10,000-100,000 | LOD + reduce edge density |
| >100,000 | Cosmos.gl (GPU-accelerated) |

## Complete implementation pipeline

**Step 1: Initial graph construction**
1. Scroll all documents from Qdrant
2. Batch compute edges using recommend API with threshold 0.45
3. Build NetworkX graph with edge type classification
4. Run HDBSCAN for cluster assignments
5. Compute UMAP 1D projection for X positions
6. Store cluster/position metadata back to Qdrant payloads

**Step 2: Export for visualization**
```python
def prepare_threejs_data(graph, positions, clusters):
    return {
        'nodes': [{
            'id': n,
            'x': positions[i, 0] * 100,  # Scale to scene
            'y': positions[i, 1] * 200,  # Time axis stretched
            'z': positions[i, 2] * 50,   # Depth compressed
            'cluster': clusters[i],
            **graph.nodes[n]
        } for i, n in enumerate(graph.nodes())],
        'links': [{
            'source': u,
            'target': v,
            'value': d['weight'],
            'type': d['type']
        } for u, v, d in graph.edges(data=True)]
    }
```

**Step 3: Real-time updates**
1. On new file: embed with Gemma, upsert to Qdrant
2. Use Parametric UMAP for instant X position
3. Use `approximate_predict` for cluster assignment
4. Find edges via recommend API
5. Push incremental update to Three.js via WebSocket

## Key parameter reference

| Component | Parameter | Value | Rationale |
|-----------|-----------|-------|-----------|
| **Similarity** | near_duplicate | >0.92 | Z-axis compression |
| | similar_to | 0.75-0.92 | Primary edges |
| | depends_on | 0.45-0.75 | Secondary edges |
| **UMAP** | n_neighbors | 15 | Balance local/global |
| | min_dist | 0.1 | Cluster separation |
| | metric | cosine | Text embeddings |
| **HDBSCAN** | min_cluster_size | 10 | Meaningful groups |
| | min_samples | 5 | Noise reduction |
| | method | eom | Stable clusters |
| **Three.js** | forceY strength | 1.0 | Fixed time axis |
| | forceX/Z strength | 0.3 | Allow clustering |
| | linkCurvature | 0.25 | Edge readability |

This specification provides VETKA with a complete, production-ready architecture for transforming file embeddings into an interactive 3D knowledge graph with semantic relationships, temporal organization, and hierarchical depth visualization.