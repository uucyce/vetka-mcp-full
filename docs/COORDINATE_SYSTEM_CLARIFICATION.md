# VETKA Coordinate System - Clarification & Correction

## IMPORTANT CORRECTION

Previous commits contained inaccurate descriptions of the Z-axis usage. This document clarifies the CORRECT spatial model.

## Correct 3D Coordinate System

### Y-Axis (Vertical - PRIMARY)
Purpose: Directory hierarchy depth + Knowledge progression

Inside single tree: All files at Z approximately 0 (in tree plane)

### X-Axis (Horizontal - PRIMARY)
Purpose: Sibling ordering within same directory level

Formula: X = barycenter(parent_children) + semantic_offset

- Each folder gets its children distributed horizontally
- Angular distribution (2D spinning) around Y-axis handles radial spreading
- Siblings spread out to minimize visual overlap

### Z-Axis (Depth - SECONDARY - LIMITED USE)

INSIDE SINGLE TREE:
- Magnification effect (future): File preview enlargement on hover
- Layering for UI elements (current): Buttons, labels above tree
- NOT used for folder positioning

FOR MULTIPLE TREES (Forest - Future Phase 16):
- Z = Tree offset in forest space
- Each semantic tree gets X, Z offset
- Y remains global (knowledge progression across all trees)
- Trees distributed via MDS on X-Z plane

## What Was Incorrect

Previous descriptions that were WRONG:

1. "Z-depth for folder ordering" - WRONG
   CORRECT: Folders ordered by barycenter on X-axis
   
2. "Z-order optimization (Phase 15.5)" - WRONG
   CORRECT: Better X-distribution optimization (crossing reduction)
   
3. "Z-front/middle/back (single tree)" - WRONG
   CORRECT: This applies to MULTIPLE TREES, not single tree
   Inside single tree: all files at Z ≈ 0 (in tree plane)

## Terminology Correction

OLD (Wrong) → NEW (Correct)
- Z-depth for positioning → X-axis distribution
- Z-order optimization → Crossing reduction
- Z-front/middle/back (single tree) → All at Z≈0 plane
- Angular distribution → Rotation around vertical Y-axis
- Z-axis depth (inside tree) → Magnification effect (future)

## Summary

CORRECT (Current & Future):
- Y-axis: Vertical hierarchy (directory depth, knowledge level)
- X-axis: Horizontal distribution (siblings, alternatives)
- Angular: Rotation around Y-axis (2D effect on X-Y plane)
- Z-axis: Between-tree positioning (future Phase 16+)
- Magnification: On-hover file preview (future)

INCORRECT (in previous commits):
- Z-axis: For folder ordering within single tree
- Z-order: For crossing reduction
- Z-depth: For in-plane positioning

Date: December 20, 2025
Status: Terminology corrected for future documentation
