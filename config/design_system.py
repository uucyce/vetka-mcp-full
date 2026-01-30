# config/design_system.py
"""VETKA Design System - Constants per Theory + Grok research"""

# ═══════════════════════════════════════════════════════════════
# PHYLOTAXIS LAYOUT (Theory 3.2)
# ═══════════════════════════════════════════════════════════════
# Applies at TWO levels:
# 1. FOREST: Trees distributed around center (related themes = closer)
# 2. TREE: Children distributed around parent node
# Y = depth (vertical, going down)
# X, Z = siblings spread by Golden Angle (horizontal plane)

GOLDEN_ANGLE = 137.5
LAYER_HEIGHT = 100
GRAVITY_PULL = 0.7
MAX_DEVIATION = 15

# ═══════════════════════════════════════════════════════════════
# FOCUS MODE (когда работаем с конкретной веткой)
# ═══════════════════════════════════════════════════════════════
FOCUS_MODE = {
    "active_opacity": 1.0,
    "background_opacity": 0.15,
    "fog_near": 200,
    "fog_far": 600,
    "fog_color": "#0A0A0A"
}

# ═══════════════════════════════════════════════════════════════
# PROMOTE THRESHOLDS (Theory Chapter V)
# ═══════════════════════════════════════════════════════════════
PROMOTE_THRESHOLDS = {
    "node_count": 50,
    "entropy": 0.8,
    "depth": 5,
}

# ═══════════════════════════════════════════════════════════════
# AGENT COLORS (Theory 4.3: warm=human, cool=AI)
# ═══════════════════════════════════════════════════════════════
AGENT_COLORS = {
    "PM": "#FFB347",      # Warm orange
    "Dev": "#6495ED",     # Cool blue
    "QA": "#9370DB",      # Purple
    "ARC": "#32CD32",     # Green
    "Human": "#FFD700",   # Gold
    "System": "#A9A9A9",  # Gray
}

# ═══════════════════════════════════════════════════════════════
# EDGE STYLES (Theory 2.1)
# ═══════════════════════════════════════════════════════════════
EDGE_STYLES = {
    "creates":    {"color": "#A9A9A9", "thickness": 2.0, "style": "solid"},
    "informs":    {"color": "#FFB347", "thickness": 1.0, "style": "dashed"},
    "influences": {"color": "#DC143C", "thickness": 2.0, "style": "solid"},
    "depends":    {"color": "#6495ED", "thickness": 1.5, "style": "solid", "arrow": "triangle"},
    "controls":   {"color": "#32CD32", "thickness": 1.0, "style": "dotted"},
}

# ═══════════════════════════════════════════════════════════════
# ANIMATION PARAMS
# ═══════════════════════════════════════════════════════════════
ANIMATION_PARAMS = {
    "static":  {"scale": [1.0, 1.0], "opacity": [1.0, 1.0], "period_ms": 0},
    "pulse":   {"scale": [1.0, 1.1], "opacity": [1.0, 1.0], "period_ms": 800},
    "glow":    {"scale": [1.0, 1.0], "opacity": [0.7, 1.0], "period_ms": 600},
    "flicker": {"scale": [1.0, 1.0], "opacity": [0.3, 1.0], "period_ms": 500},
}

# ═══════════════════════════════════════════════════════════════
# UI COLORS (Dark mode)
# ═══════════════════════════════════════════════════════════════
UI_COLORS = {
    "bg_base": "#0A0A0A",
    "bg_secondary": "#161616",
    "bg_tertiary": "#1F1F1F",
    "text_primary": "#F9FAFB",
    "text_secondary": "#E5E7EB",
    "text_muted": "#9CA3AF",
    "border": "rgba(55, 65, 81, 0.3)",
}

# ═══════════════════════════════════════════════════════════════
# THEORY CONSTANTS
# ═══════════════════════════════════════════════════════════════
TEMPORAL_DECAY_TAU_DAYS = 7
BRANCH_TYPES = ["memory", "task", "data", "control"]
EDGE_SEMANTICS = ["creates", "informs", "influences", "depends", "controls"]

# ═══════════════════════════════════════════════════════════════
# SCANNER LIMITS (защита от зависания)
# ═══════════════════════════════════════════════════════════════
SCANNER_LIMITS = {
    "max_depth": 5,
    "max_directories": 10000,
    "max_items_per_dir": 1000,
    "max_files": 100,  # В выходных данных
}
