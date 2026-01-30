# src/export/__init__.py
"""
VETKA Export module - Blender and other 3D format exports.

Provides export functionality for VETKA tree structures to various
3D formats including JSON, GLB, and OBJ for visualization in
external tools like Blender.

@status: active
@phase: 96
@depends: blender_exporter
@used_by: visualizer, api/routes
"""

from .blender_exporter import BlenderExporter

__all__ = ['BlenderExporter']
