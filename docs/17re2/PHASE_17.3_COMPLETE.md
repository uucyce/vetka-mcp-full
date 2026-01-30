# PHASE 17.3: Semantic Tree Structure + Blender Export - COMPLETE

**Date:** 2025-12-24
**Status:** IMPLEMENTED - Concept nodes, Edge bundling, Blender export

---

## Executive Summary

Implemented **Semantic Tree Visualization** with Blender export capability:
- White sphere concept nodes (minimalist monochrome style)
- Edge bundling algorithm for visual clutter reduction
- Blender export in JSON/GLB/OBJ formats
- Export UI buttons in frontend

---

## 1. Concept Node Rendering

**Style:** Minimalist monochrome (Nolan Batman aesthetic)

### Features:
- White spheres (`0xFFFFFF`) for semantic cluster concepts
- Dark emissive (`0x222222`) for depth contrast
- Subtle gray outline for visibility
- Fade-in during semantic blend (40-80% range)

### Code: `tree_renderer.py` (lines 6425-6513)

```javascript
function createConceptNode(concept, position) {
    const geometry = new THREE.SphereGeometry(15, 12, 12);
    const material = new THREE.MeshPhongMaterial({
        color: 0xFFFFFF,        // White only
        emissive: 0x222222,     // Dark emissive for contrast
        shininess: 30,
        transparent: true,
        opacity: 0.9
    });
    // ... outline for visibility
}

function renderConceptNodes(semanticData, positions) {
    // Creates concept group, hidden by default
    // Called when semantic_data available
}

function updateConceptNodesVisibility(blendProgress) {
    // < 0.4: hidden
    // 0.4-0.8: fade in
    // > 0.8: fully visible
}
```

---

## 2. Edge Bundling Algorithm

**Purpose:** Reduce visual clutter by grouping parallel/nearby edges

### Algorithm:
1. Group edges by direction (12 buckets of 30 degrees each)
2. Group by Y-level (200-unit vertical bands)
3. Single edges: straight lines
4. Bundled edges: quadratic Bezier curves through shared control point

### Code: `tree_renderer.py` (lines 6548-6722)

```javascript
function bundleParallelEdges(edges, nodePositions, bundleStrength = 0.6) {
    // Group edges by direction bucket
    const directionBuckets = new Map();
    const ANGLE_BUCKETS = 12;  // 30-degree buckets

    // Calculate bundle center for each group
    // Create Bezier curves through shared control point
    // bundleStrength controls how much edges are pulled toward center
}

function updateBundledEdgesVisibility(blendProgress) {
    // Show bundled edges when semantic mode active (> 50%)
}

function clearBundledEdges() {
    // Clean up all bundled edge meshes
}
```

---

## 3. Blender Exporter Module

### File: `src/export/blender_exporter.py`

**Formats Supported:**
| Format | Description | Dependencies |
|--------|-------------|--------------|
| JSON | Plain JSON with Blender Python script | None |
| GLB | Binary glTF (3D model) | trimesh (optional) |
| OBJ | Wavefront OBJ (simple, universal) | None |

### Classes:

```python
@dataclass
class BlenderNode:
    id: str
    position: Tuple[float, float, float]
    size: float
    node_type: str  # 'file', 'concept', 'folder', 'root'
    label: str = ""
    knowledge_level: float = 0.5

@dataclass
class BlenderEdge:
    from_id: str
    to_id: str
    edge_type: str  # 'contains', 'prerequisite', 'similarity', 'directory'

class BlenderExporter:
    def add_node(node_id, pos, node_type, label="", size=None, knowledge_level=0.5)
    def add_edge(from_id, to_id, edge_type='contains')
    def export_json(filepath) -> Dict
    def export_glb(filepath) -> bool
    def export_obj(filepath) -> bool
    def get_stats() -> Dict
```

### JSON Export Includes:
- Nodes with positions, types, sizes
- Edges with source/target/type
- Metadata (counts, types)
- Embedded Blender Python import script

---

## 4. Export API Endpoint

### Route: `GET /api/tree/export/blender`

**Query Parameters:**
| Param | Values | Default | Description |
|-------|--------|---------|-------------|
| format | json, glb, obj | json | Output format |
| mode | directory, semantic | directory | Position source |

### Response:
- File download with appropriate Content-Type
- Filename: `vetka-tree-{mode}.{format}`

### Code: `tree_routes.py`

```python
@bp.route('/api/tree/export/blender', methods=['GET'])
def export_blender():
    output_format = request.args.get('format', 'json')
    mode = request.args.get('mode', 'directory')

    # Build exporter from VETKA_DATA
    exporter = BlenderExporter(output_format=output_format)

    # Add nodes and edges
    for node in nodes:
        exporter.add_node(...)
    for edge in edges:
        exporter.add_edge(...)

    # Export to temp file and return
    return send_file(output_path, as_attachment=True)
```

---

## 5. Frontend Export UI

### CSS Panel: `#export-panel`
```css
#export-panel {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: rgba(22, 22, 22, 0.9);
    padding: 12px;
    border-radius: 8px;
}
```

### Export Buttons:
```html
<div id="export-panel">
    <div class="export-title">Export to Blender</div>
    <div class="export-buttons">
        <button onclick="exportToBlender('json')">JSON</button>
        <button onclick="exportToBlender('obj')">OBJ</button>
        <button onclick="exportToBlender('glb')">GLB</button>
    </div>
</div>
```

### JavaScript Function:
```javascript
function exportToBlender(format) {
    const blendValue = document.getElementById('semantic-blend-slider')?.value || 0;
    const mode = blendValue > 50 ? 'semantic' : 'directory';

    fetch(`/api/tree/export/blender?format=${format}&mode=${mode}`)
        .then(response => response.blob())
        .then(blob => {
            // Trigger download
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = `vetka-tree-${mode}.${format}`;
            link.click();
        });
}
```

---

## 6. Visual Integration with Semantic Blend

### Blend Slider Integration:

The semantic blend slider (0-100%) controls:

| Range | Directory Edges | Concept Nodes | Bundled Edges |
|-------|-----------------|---------------|---------------|
| 0-30% | Full opacity | Hidden | Hidden |
| 30-40% | Fading | Hidden | Hidden |
| 40-50% | 50% opacity | Fading in | Hidden |
| 50-70% | 30% opacity | Visible | Fading in |
| 70-80% | 30% opacity | Visible | Visible |
| 80-100% | 30% opacity | Full opacity | Full opacity |

---

## 7. Files Modified/Created

| File | Status | Changes |
|------|--------|---------|
| `src/export/__init__.py` | NEW | Package init |
| `src/export/blender_exporter.py` | NEW | Full exporter class (430 lines) |
| `src/server/routes/tree_routes.py` | MODIFIED | Added export endpoint |
| `src/visualizer/tree_renderer.py` | MODIFIED | Concept nodes, edge bundling, export UI |

---

## 8. Blender Import Workflow

1. Export from VETKA: Click "JSON" button
2. Open Blender
3. Switch to Scripting workspace
4. Open Text Editor
5. Run the embedded Python script:

```python
import bpy
import json

def import_vetka(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Create white material
    mat = bpy.data.materials.new(name="VETKA_Material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)  # White

    # Create spheres for nodes
    for node in data['nodes']:
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=node['size'] * 0.01,
            location=(node['position'][0] * 0.01,
                     node['position'][1] * 0.01,
                     node['position'][2] * 0.01)
        )
        obj = bpy.context.active_object
        obj.name = f"VETKA_{node['type']}_{node['id'][:8]}"
        obj.data.materials.append(mat)

    # Create edges as curves
    # ...

import_vetka('/path/to/vetka-tree.json')
```

---

## 9. Testing Verification

```bash
# Syntax checks
python3 -m py_compile src/export/blender_exporter.py  # OK
python3 -m py_compile src/server/routes/tree_routes.py  # OK
python3 -m py_compile src/visualizer/tree_renderer.py  # OK

# Import tests
python3 -c "from src.export.blender_exporter import BlenderExporter; print('OK')"
python3 -c "from src.orchestration.semantic_dag_builder import SemanticDAGBuilder; print('OK')"
python3 -c "from src.layout.semantic_sugiyama import calculate_semantic_sugiyama_layout; print('OK')"
```

---

## 10. Future Extensions

1. **GLB with Animations** - Export blend transition as animation
2. **Material Library** - Export with Blender material presets
3. **USD Export** - Universal Scene Description for professional pipelines
4. **FBX Export** - For game engines (Unity, Unreal)
5. **Edge Labels** - Include edge type labels in 3D export
6. **LOD Levels** - Export multiple detail levels

---

*Completed: 2025-12-24*
*Author: Claude Opus 4.5*
