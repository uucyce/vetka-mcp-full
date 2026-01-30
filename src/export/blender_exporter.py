# src/export/blender_exporter.py
"""
Phase 17.3: Blender Export

Export VETKA tree structure to 3D formats:
- JSON (for import to Blender via Python script)
- GLB (binary glTF, if trimesh available)

Style: Minimalist monochrome (Nolan Batman aesthetic)
- White spheres for nodes
- Gray lines for edges
- No color coding

@status: active
@phase: 96
@depends: json, struct, base64, dataclasses, logging, trimesh (optional)
@used_by: src.export.__init__, tree_renderer
"""

import json
import struct
import base64
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class BlenderNode:
    """Node data for Blender export"""
    id: str
    position: Tuple[float, float, float]
    size: float
    node_type: str  # 'file', 'concept', 'folder', 'root'
    label: str = ""
    knowledge_level: float = 0.5


@dataclass
class BlenderEdge:
    """Edge data for Blender export"""
    from_id: str
    to_id: str
    edge_type: str  # 'contains', 'prerequisite', 'similarity', 'directory'


class BlenderExporter:
    """Export VETKA tree structure to 3D format"""

    def __init__(self, output_format: str = 'json'):
        """
        Args:
            output_format: 'json' or 'glb'
        """
        self.output_format = output_format
        self.nodes: List[BlenderNode] = []
        self.edges: List[BlenderEdge] = []
        self._node_id_map: Dict[str, int] = {}

    def add_node(
        self,
        node_id: str,
        pos: Dict[str, float],
        node_type: str,
        label: str = "",
        size: Optional[float] = None,
        knowledge_level: float = 0.5
    ):
        """Add node to export"""
        # Default sizes by type
        if size is None:
            size = {
                'root': 20,
                'concept': 15,
                'folder': 12,
                'file': 8,
                'leaf': 8
            }.get(node_type, 10)

        self._node_id_map[node_id] = len(self.nodes)

        self.nodes.append(BlenderNode(
            id=node_id,
            position=(
                float(pos.get('x', 0)),
                float(pos.get('y', 0)),
                float(pos.get('z', 0))
            ),
            size=size,
            node_type=node_type,
            label=label,
            knowledge_level=knowledge_level
        ))

    def add_edge(self, from_id: str, to_id: str, edge_type: str = 'contains'):
        """Add edge to export"""
        self.edges.append(BlenderEdge(
            from_id=from_id,
            to_id=to_id,
            edge_type=edge_type
        ))

    def export_json(self, filepath: str) -> Dict:
        """
        Export as plain JSON (for import to Blender via Python script)

        Returns the exported data dict as well as writing to file
        """
        data = {
            "format": "VETKA-Blender-Export-v1",
            "style": "minimalist-monochrome",
            "nodes": [
                {
                    "id": n.id,
                    "position": list(n.position),
                    "type": n.node_type,
                    "size": n.size,
                    "label": n.label,
                    "knowledge_level": n.knowledge_level
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "from": e.from_id,
                    "to": e.to_id,
                    "type": e.edge_type
                }
                for e in self.edges
            ],
            "metadata": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "node_types": list(set(n.node_type for n in self.nodes)),
                "edge_types": list(set(e.edge_type for e in self.edges))
            },
            "blender_script": self._generate_blender_script()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"[BlenderExport] Saved JSON to {filepath}")
        return data

    def _generate_blender_script(self) -> str:
        """Generate Python script for Blender import"""
        return '''
# VETKA Blender Import Script
# Run in Blender's Python console or as script

import bpy
import json
import mathutils

def import_vetka(filepath):
    """Import VETKA export JSON into Blender scene"""

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Clear existing VETKA objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.name.startswith('VETKA_'):
            obj.select_set(True)
    bpy.ops.object.delete()

    # Create material (white, minimal)
    mat = bpy.data.materials.new(name="VETKA_Material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)  # White
    bsdf.inputs['Roughness'].default_value = 0.8

    # Create nodes
    node_objects = {}
    for node in data['nodes']:
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=node['size'] * 0.01,  # Scale down
            location=(node['position'][0] * 0.01,
                     node['position'][1] * 0.01,
                     node['position'][2] * 0.01)
        )
        obj = bpy.context.active_object
        obj.name = f"VETKA_{node['type']}_{node['id'][:8]}"
        obj.data.materials.append(mat)
        node_objects[node['id']] = obj

    # Create edges as curves
    for edge in data['edges']:
        if edge['from'] in node_objects and edge['to'] in node_objects:
            start = node_objects[edge['from']].location
            end = node_objects[edge['to']].location

            # Create curve
            curve = bpy.data.curves.new('VETKA_Edge', type='CURVE')
            curve.dimensions = '3D'

            spline = curve.splines.new('BEZIER')
            spline.bezier_points.add(1)
            spline.bezier_points[0].co = start
            spline.bezier_points[1].co = end

            obj = bpy.data.objects.new('VETKA_Edge', curve)
            bpy.context.collection.objects.link(obj)

    print(f"Imported {len(data['nodes'])} nodes, {len(data['edges'])} edges")

# Usage: import_vetka('/path/to/vetka-tree.json')
'''

    def export_glb(self, filepath: str) -> bool:
        """
        Export as GLB (binary glTF)
        Requires trimesh library

        Returns True on success, False on failure
        """
        try:
            import trimesh
            import numpy as np

            # Create scene
            scene = trimesh.Scene()

            # Add nodes as spheres
            for node in self.nodes:
                sphere = trimesh.creation.icosphere(
                    subdivisions=2,
                    radius=node.size * 0.5
                )
                sphere.apply_translation(node.position)
                # White color
                sphere.visual.vertex_colors = np.array([[255, 255, 255, 255]] * len(sphere.vertices))
                scene.add_geometry(sphere, node_name=f"node_{node.id[:8]}")

            # Add edges as cylinders
            for edge in self.edges:
                from_idx = self._node_id_map.get(edge.from_id)
                to_idx = self._node_id_map.get(edge.to_id)

                if from_idx is not None and to_idx is not None:
                    start = np.array(self.nodes[from_idx].position)
                    end = np.array(self.nodes[to_idx].position)

                    # Create cylinder between points
                    length = np.linalg.norm(end - start)
                    if length > 0.1:
                        cylinder = trimesh.creation.cylinder(
                            radius=0.5,
                            height=length,
                            sections=6
                        )

                        # Orient cylinder
                        direction = (end - start) / length
                        midpoint = (start + end) / 2

                        # Rotation to align with direction
                        z_axis = np.array([0, 0, 1])
                        rotation_axis = np.cross(z_axis, direction)
                        if np.linalg.norm(rotation_axis) > 0.001:
                            rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
                            angle = np.arccos(np.clip(np.dot(z_axis, direction), -1, 1))
                            rotation = trimesh.transformations.rotation_matrix(
                                angle, rotation_axis
                            )
                            cylinder.apply_transform(rotation)

                        cylinder.apply_translation(midpoint)
                        # Gray color for edges
                        cylinder.visual.vertex_colors = np.array([[180, 180, 180, 255]] * len(cylinder.vertices))
                        scene.add_geometry(cylinder, node_name=f"edge_{edge.from_id[:4]}_{edge.to_id[:4]}")

            # Export
            scene.export(filepath)
            logger.info(f"[BlenderExport] Saved GLB to {filepath}")
            return True

        except ImportError:
            logger.warning("[BlenderExport] trimesh not installed, cannot export GLB")
            # Fallback to JSON
            json_path = filepath.replace('.glb', '.json')
            self.export_json(json_path)
            return False

        except Exception as e:
            logger.error(f"[BlenderExport] GLB export error: {e}")
            return False

    def export_obj(self, filepath: str) -> bool:
        """
        Export as OBJ (simple, widely supported)
        No external dependencies
        """
        try:
            vertices = []
            faces = []
            vertex_offset = 1  # OBJ is 1-indexed

            # Generate sphere vertices for each node
            for node in self.nodes:
                # Simple octahedron (6 vertices, 8 faces)
                r = node.size * 0.5
                cx, cy, cz = node.position

                # 6 vertices of octahedron
                v_start = len(vertices)
                vertices.extend([
                    (cx, cy + r, cz),  # top
                    (cx, cy - r, cz),  # bottom
                    (cx + r, cy, cz),  # +x
                    (cx - r, cy, cz),  # -x
                    (cx, cy, cz + r),  # +z
                    (cx, cy, cz - r),  # -z
                ])

                # 8 faces
                base = vertex_offset + v_start
                faces.extend([
                    (base, base + 2, base + 4),  # top +x +z
                    (base, base + 4, base + 3),  # top +z -x
                    (base, base + 3, base + 5),  # top -x -z
                    (base, base + 5, base + 2),  # top -z +x
                    (base + 1, base + 4, base + 2),  # bot +z +x
                    (base + 1, base + 3, base + 4),  # bot -x +z
                    (base + 1, base + 5, base + 3),  # bot -z -x
                    (base + 1, base + 2, base + 5),  # bot +x -z
                ])

            # Write OBJ file
            with open(filepath, 'w') as f:
                f.write("# VETKA Tree Export\n")
                f.write(f"# Nodes: {len(self.nodes)}, Edges: {len(self.edges)}\n\n")

                # Vertices
                for v in vertices:
                    f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")

                f.write("\n")

                # Faces
                for face in faces:
                    f.write(f"f {face[0]} {face[1]} {face[2]}\n")

                # Edges as lines
                f.write("\n# Edges\n")
                for edge in self.edges:
                    from_idx = self._node_id_map.get(edge.from_id)
                    to_idx = self._node_id_map.get(edge.to_id)
                    if from_idx is not None and to_idx is not None:
                        # Reference first vertex of each node's octahedron
                        f.write(f"l {from_idx * 6 + 1} {to_idx * 6 + 1}\n")

            logger.info(f"[BlenderExport] Saved OBJ to {filepath}")
            return True

        except Exception as e:
            logger.error(f"[BlenderExport] OBJ export error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get export statistics"""
        return {
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'node_types': dict(
                (t, sum(1 for n in self.nodes if n.node_type == t))
                for t in set(n.node_type for n in self.nodes)
            ),
            'edge_types': dict(
                (t, sum(1 for e in self.edges if e.edge_type == t))
                for t in set(e.edge_type for e in self.edges)
            )
        }


def export_tree_to_blender(
    tree_data: Dict,
    positions: Dict[str, Dict],
    output_path: str,
    output_format: str = 'json'
) -> Dict:
    """
    Convenience function to export tree data directly

    Args:
        tree_data: Tree dict with 'nodes' and 'edges'
        positions: Dict mapping node_id -> {x, y, z}
        output_path: Output file path
        output_format: 'json', 'glb', or 'obj'

    Returns:
        Export statistics
    """
    exporter = BlenderExporter(output_format=output_format)

    # Add nodes
    nodes = tree_data.get('nodes', [])
    if isinstance(nodes, dict):
        nodes = list(nodes.values())

    for node in nodes:
        node_id = node.get('id', '')
        pos = positions.get(node_id, node.get('visual_hints', {}).get('layout_hint', {'x': 0, 'y': 0, 'z': 0}))

        exporter.add_node(
            node_id=node_id,
            pos=pos,
            node_type=node.get('type', 'file'),
            label=node.get('name', ''),
            knowledge_level=node.get('cam', {}).get('surprise_metric', 0.5)
        )

    # Add edges
    for edge in tree_data.get('edges', []):
        exporter.add_edge(
            from_id=edge.get('from', ''),
            to_id=edge.get('to', ''),
            edge_type=edge.get('semantics', edge.get('type', 'contains'))
        )

    # Export
    if output_format == 'glb':
        exporter.export_glb(output_path)
    elif output_format == 'obj':
        exporter.export_obj(output_path)
    else:
        exporter.export_json(output_path)

    return exporter.get_stats()
