"""FCP7 Auto-Compliance Scanner — generates compliance matrix from source code.

Instead of manually maintaining markdown tables, this test parses:
  1. CutHotkeyAction type (all defined actions)
  2. FCP7_PRESET (all key bindings)
  3. ACTION_SCOPE (scope per action)
  4. hotkeyHandlers in CutEditorLayoutV2.tsx (handler implementations)
  5. FCP7 reference table (expected actions)

Output: auto-generated compliance matrix + regression guard.

Task: tb_1774424854_1 (EPSILON-IDEA: Auto-compliance scanner)
Author: Epsilon (QA-2)
"""
import re
import json
import pytest
from pathlib import Path

# Worktree-safe root resolution
_THIS = Path(__file__).resolve()
_ROOT = _THIS
while _ROOT.name != 'vetka_live_03' and _ROOT != _ROOT.parent:
    _ROOT = _ROOT.parent
    if (_ROOT / '.claude').exists():
        break

CLIENT_SRC = _ROOT / 'client' / 'src'
HOTKEYS_FILE = CLIENT_SRC / 'hooks' / 'useCutHotkeys.ts'
LAYOUT_FILE = CLIENT_SRC / 'components' / 'cut' / 'CutEditorLayoutV2.tsx'


def _read(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except (FileNotFoundError, IsADirectoryError):
        return ''


def parse_hotkey_actions(source: str) -> list[str]:
    """Extract all CutHotkeyAction union members from TypeScript source."""
    # Match the type definition block
    match = re.search(
        r'export\s+type\s+CutHotkeyAction\s*=\s*([\s\S]*?);',
        source
    )
    if not match:
        return []
    block = match.group(1)
    # Extract quoted string literals
    actions = re.findall(r"'(\w+)'", block)
    return actions


def parse_fcp7_preset(source: str) -> dict[str, str]:
    """Extract FCP7_PRESET key bindings."""
    match = re.search(
        r'export\s+const\s+FCP7_PRESET\s*:\s*HotkeyMap\s*=\s*\{([\s\S]*?)\};',
        source
    )
    if not match:
        return {}
    block = match.group(1)
    bindings = {}
    for m in re.finditer(r"(\w+)\s*:\s*'([^']+)'", block):
        bindings[m.group(1)] = m.group(2)
    return bindings


def parse_action_scope(source: str) -> dict[str, str]:
    """Extract ACTION_SCOPE record."""
    match = re.search(
        r'export\s+const\s+ACTION_SCOPE\s*:\s*Record<CutHotkeyAction,\s*ActionScope>\s*=\s*\{([\s\S]*?)\};',
        source
    )
    if not match:
        return {}
    block = match.group(1)
    scopes = {}
    for m in re.finditer(r"(\w+)\s*:\s*'([^']+)'", block):
        scopes[m.group(1)] = m.group(2)
    return scopes


def parse_handler_keys(source: str) -> set[str]:
    """Extract all action keys from hotkeyHandlers object in CutEditorLayoutV2."""
    # Find handler assignments like: actionName: () => { or actionName() {
    # In the hotkeyHandlers Record
    handlers = set()
    # Pattern 1: key: () => ... or key: function
    for m in re.finditer(r'^\s+(\w+)\s*:\s*(?:\(\)|async\s*\(\)|\(\s*\))\s*=>', source, re.MULTILINE):
        handlers.add(m.group(1))
    # Pattern 2: key() { — method shorthand
    for m in re.finditer(r'^\s+(\w+)\s*\(\s*\)\s*\{', source, re.MULTILINE):
        handlers.add(m.group(1))
    return handlers


# FCP7 reference: actions that MUST exist for FCP7 compliance
# Each tuple: (action_name, fcp7_chapter, description)
FCP7_REQUIRED_ACTIONS = [
    # Playback (Ch.13)
    ('playPause', 'Ch.13', 'Play/Pause toggle'),
    ('stop', 'Ch.13', 'Stop playback'),
    ('shuttleBack', 'Ch.13', 'Shuttle backward (J)'),
    ('shuttleForward', 'Ch.13', 'Shuttle forward (L)'),
    ('frameStepBack', 'Ch.13', 'One frame backward'),
    ('frameStepForward', 'Ch.13', 'One frame forward'),
    ('fiveFrameStepBack', 'Ch.13', 'Five frames backward'),
    ('fiveFrameStepForward', 'Ch.13', 'Five frames forward'),
    ('goToStart', 'Ch.13', 'Go to start'),
    ('goToEnd', 'Ch.13', 'Go to end'),
    # Marking (Ch.18-19)
    ('markIn', 'Ch.18', 'Set In point'),
    ('markOut', 'Ch.18', 'Set Out point'),
    ('clearIn', 'Ch.18', 'Clear In point'),
    ('clearOut', 'Ch.18', 'Clear Out point'),
    ('clearInOut', 'Ch.18', 'Clear In and Out'),
    ('goToIn', 'Ch.19', 'Go to In point'),
    ('goToOut', 'Ch.19', 'Go to Out point'),
    ('markClip', 'Ch.18', 'Mark clip boundaries'),
    ('playInToOut', 'Ch.19', 'Play In to Out range'),
    # Editing (Ch.28-32)
    ('undo', 'Ch.15', 'Undo'),
    ('redo', 'Ch.15', 'Redo'),
    ('deleteClip', 'Ch.28', 'Delete clip (leave gap)'),
    ('splitClip', 'Ch.28', 'Add edit / blade'),
    ('rippleDelete', 'Ch.28', 'Ripple delete'),
    ('selectAll', 'Ch.28', 'Select all clips'),
    ('copy', 'Ch.28', 'Copy'),
    ('cut', 'Ch.28', 'Cut'),
    ('paste', 'Ch.28', 'Paste'),
    ('pasteInsert', 'Ch.28', 'Paste insert'),
    ('nudgeLeft', 'Ch.28', 'Nudge clip left'),
    ('nudgeRight', 'Ch.28', 'Nudge clip right'),
    # Tools (Ch.44, App.A)
    ('razorTool', 'Ch.44', 'Blade/Razor tool'),
    ('selectTool', 'Ch.44', 'Selection/Arrow tool'),
    ('insertEdit', 'Ch.28', 'Insert edit (3-point)'),
    ('overwriteEdit', 'Ch.28', 'Overwrite edit (3-point)'),
    ('replaceEdit', 'Ch.28', 'Replace edit'),
    ('fitToFill', 'Ch.28', 'Fit to fill'),
    ('superimpose', 'Ch.28', 'Superimpose'),
    ('slipTool', 'Ch.44', 'Slip tool'),
    ('slideTool', 'Ch.44', 'Slide tool'),
    ('rippleTool', 'Ch.44', 'Ripple trim tool'),
    ('rollTool', 'Ch.44', 'Roll trim tool'),
    # Markers (Ch.20)
    ('addMarker', 'Ch.20', 'Add marker'),
    ('nextMarker', 'Ch.20', 'Next marker'),
    ('prevMarker', 'Ch.20', 'Previous marker'),
    # Keyframes (Ch.67)
    ('nextKeyframe', 'Ch.67', 'Next keyframe'),
    ('prevKeyframe', 'Ch.67', 'Previous keyframe'),
    ('addKeyframe', 'Ch.67', 'Add keyframe'),
    # Sequence (Ch.32)
    ('liftClip', 'Ch.32', 'Lift clip'),
    ('extractClip', 'Ch.32', 'Extract clip'),
    ('closeGap', 'Ch.32', 'Close gap'),
    ('extendEdit', 'Ch.41', 'Extend edit'),
    ('splitEditLCut', 'Ch.41', 'Split edit L-cut'),
    ('splitEditJCut', 'Ch.41', 'Split edit J-cut'),
    ('addDefaultTransition', 'Ch.46', 'Add default transition'),
    # Navigation (Ch.13)
    ('prevEditPoint', 'Ch.13', 'Previous edit point'),
    ('nextEditPoint', 'Ch.13', 'Next edit point'),
    ('matchFrame', 'Ch.50', 'Match frame'),
    # View (Ch.13)
    ('zoomIn', 'Ch.13', 'Zoom in timeline'),
    ('zoomOut', 'Ch.13', 'Zoom out timeline'),
    ('zoomToFit', 'Ch.13', 'Zoom to fit'),
    # Project (Ch.1)
    ('importMedia', 'Ch.1', 'Import media'),
    ('saveProject', 'Ch.1', 'Save project'),
    # Panel focus (Ch.1)
    ('focusSource', 'Ch.1', 'Focus source monitor'),
    ('focusProgram', 'Ch.1', 'Focus program monitor'),
    ('focusTimeline', 'Ch.1', 'Focus timeline'),
    ('focusProject', 'Ch.1', 'Focus project panel'),
    # Linked selection + Snap (App.A)
    ('toggleLinkedSelection', 'App.A', 'Toggle linked selection'),
    ('toggleSnap', 'App.A', 'Toggle snap'),
    ('makeSubclip', 'Ch.38', 'Make subclip'),
]


class TestFCP7ActionCoverage:
    """Verify all FCP7-required actions are defined in CutHotkeyAction."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.hotkeys_src = _read(HOTKEYS_FILE)
        self.layout_src = _read(LAYOUT_FILE)
        if not self.hotkeys_src:
            pytest.skip("useCutHotkeys.ts not found")
        if not self.layout_src:
            pytest.skip("CutEditorLayoutV2.tsx not found")

        self.actions = parse_hotkey_actions(self.hotkeys_src)
        self.fcp7_preset = parse_fcp7_preset(self.hotkeys_src)
        self.scopes = parse_action_scope(self.hotkeys_src)
        self.handlers = parse_handler_keys(self.layout_src)

    def test_all_fcp7_actions_defined(self):
        """Every FCP7-required action must be in CutHotkeyAction type."""
        missing = []
        for action, chapter, desc in FCP7_REQUIRED_ACTIONS:
            if action not in self.actions:
                missing.append(f"  {action} ({chapter}: {desc})")
        assert not missing, (
            f"FCP7-required actions missing from CutHotkeyAction:\n"
            + "\n".join(missing)
        )

    def test_all_fcp7_actions_have_bindings(self):
        """Every FCP7-required action must have a key binding in FCP7_PRESET."""
        missing = []
        for action, chapter, desc in FCP7_REQUIRED_ACTIONS:
            if action not in self.fcp7_preset:
                missing.append(f"  {action} ({chapter}: {desc})")
        assert not missing, (
            f"FCP7-required actions missing from FCP7_PRESET:\n"
            + "\n".join(missing)
        )

    def test_all_fcp7_actions_have_scope(self):
        """Every FCP7-required action must have a scope in ACTION_SCOPE."""
        missing = []
        for action, chapter, desc in FCP7_REQUIRED_ACTIONS:
            if action not in self.scopes:
                missing.append(f"  {action} ({chapter}: {desc})")
        assert not missing, (
            f"FCP7-required actions missing from ACTION_SCOPE:\n"
            + "\n".join(missing)
        )

    def test_all_actions_have_handlers(self):
        """Every action in CutHotkeyAction must have a handler in CutEditorLayoutV2."""
        # We check by looking for the action name as a key in the layout file
        missing = []
        for action in self.actions:
            # Check if action appears as an object key in the handler
            pattern = rf'\b{re.escape(action)}\s*:'
            if not re.search(pattern, self.layout_src):
                missing.append(f"  {action}")
        assert not missing, (
            f"Actions defined in CutHotkeyAction but missing handler in CutEditorLayoutV2:\n"
            + "\n".join(missing)
        )


class TestFCP7BindingConsistency:
    """Verify internal consistency of hotkey definitions."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.hotkeys_src = _read(HOTKEYS_FILE)
        if not self.hotkeys_src:
            pytest.skip("useCutHotkeys.ts not found")
        self.actions = parse_hotkey_actions(self.hotkeys_src)
        self.fcp7_preset = parse_fcp7_preset(self.hotkeys_src)
        self.scopes = parse_action_scope(self.hotkeys_src)

    def test_no_orphan_bindings(self):
        """FCP7_PRESET should not contain bindings for non-existent actions."""
        orphans = [k for k in self.fcp7_preset if k not in self.actions]
        assert not orphans, f"Orphan bindings in FCP7_PRESET (not in CutHotkeyAction): {orphans}"

    def test_no_orphan_scopes(self):
        """ACTION_SCOPE should not contain entries for non-existent actions."""
        orphans = [k for k in self.scopes if k not in self.actions]
        assert not orphans, f"Orphan scopes in ACTION_SCOPE (not in CutHotkeyAction): {orphans}"

    def test_all_actions_have_binding(self):
        """Every CutHotkeyAction should have a binding in FCP7_PRESET."""
        missing = [a for a in self.actions if a not in self.fcp7_preset]
        assert not missing, f"Actions without FCP7 binding: {missing}"

    def test_all_actions_have_scope(self):
        """Every CutHotkeyAction should have a scope in ACTION_SCOPE."""
        missing = [a for a in self.actions if a not in self.scopes]
        assert not missing, f"Actions without scope: {missing}"

    def test_no_duplicate_bindings_in_fcp7(self):
        """No two actions should share the same key binding in FCP7_PRESET."""
        seen: dict[str, list[str]] = {}
        for action, binding in self.fcp7_preset.items():
            norm = binding.lower()
            seen.setdefault(norm, []).append(action)
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        assert not dupes, f"Duplicate bindings in FCP7_PRESET: {dupes}"

    def test_action_count_regression(self):
        """Action count should not decrease (regression guard)."""
        assert len(self.actions) >= 82, (
            f"CutHotkeyAction has {len(self.actions)} actions, expected >= 82 "
            f"(regression: actions were removed)"
        )


class TestFCP7ComplianceMatrix:
    """Generate and validate the compliance matrix."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.hotkeys_src = _read(HOTKEYS_FILE)
        self.layout_src = _read(LAYOUT_FILE)
        if not self.hotkeys_src:
            pytest.skip("useCutHotkeys.ts not found")
        self.actions = parse_hotkey_actions(self.hotkeys_src)
        self.fcp7_preset = parse_fcp7_preset(self.hotkeys_src)
        self.scopes = parse_action_scope(self.hotkeys_src)

    def test_compliance_percentage(self):
        """FCP7 compliance must be >= 80%."""
        total = len(FCP7_REQUIRED_ACTIONS)
        covered = 0
        for action, chapter, desc in FCP7_REQUIRED_ACTIONS:
            if (action in self.actions and
                action in self.fcp7_preset and
                action in self.scopes):
                # Check handler exists in layout
                pattern = rf'\b{re.escape(action)}\s*:'
                if re.search(pattern, self.layout_src):
                    covered += 1

        pct = (covered / total * 100) if total > 0 else 0
        assert pct >= 80, (
            f"FCP7 compliance: {pct:.1f}% ({covered}/{total}) — "
            f"must be >= 80%"
        )

    def test_generate_matrix_json(self, tmp_path):
        """Generate compliance matrix as JSON for CI consumption."""
        matrix = []
        for action, chapter, desc in FCP7_REQUIRED_ACTIONS:
            entry = {
                'action': action,
                'fcp7_chapter': chapter,
                'description': desc,
                'defined': action in self.actions,
                'has_binding': action in self.fcp7_preset,
                'binding': self.fcp7_preset.get(action, ''),
                'has_scope': action in self.scopes,
                'scope': self.scopes.get(action, ''),
                'has_handler': bool(re.search(
                    rf'\b{re.escape(action)}\s*:', self.layout_src
                )),
            }
            entry['compliant'] = all([
                entry['defined'],
                entry['has_binding'],
                entry['has_scope'],
                entry['has_handler'],
            ])
            matrix.append(entry)

        total = len(matrix)
        compliant = sum(1 for e in matrix if e['compliant'])

        report = {
            'generated_at': __import__('time').strftime('%Y-%m-%dT%H:%M:%S'),
            'total_fcp7_required': total,
            'compliant': compliant,
            'compliance_pct': round(compliant / total * 100, 1) if total else 0,
            'missing': [e for e in matrix if not e['compliant']],
            'matrix': matrix,
        }

        out = tmp_path / 'fcp7_compliance_matrix.json'
        out.write_text(json.dumps(report, indent=2))

        # Also try to write to data/benchmarks for persistence
        bench_dir = _ROOT / 'data' / 'benchmarks'
        try:
            bench_dir.mkdir(parents=True, exist_ok=True)
            (bench_dir / 'fcp7_compliance_matrix.json').write_text(
                json.dumps(report, indent=2)
            )
        except OSError:
            pass  # CI may not have write access

        assert compliant >= 60, (
            f"Only {compliant}/{total} FCP7-required actions are compliant"
        )
