"""
Monochrome compliance helpers shared between enforcement, static, and
visual regression test suites.

Extracted from test_monochrome_enforcement.py, test_monochrome_static.py,
and test_gamma_polish_visual_regression.py where identical logic was
independently maintained.

Usage:
    from tests.fixtures.cut_monochrome import is_grey, is_allowed_red, parse_rgb
"""

import re
from typing import Optional, Tuple


HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def normalise_hex(raw: str) -> str:
    """
    Expand shorthand hex to 6 lowercase digits (no #).

    #abc     → aabbcc
    #abcd    → aabbcc  (strip alpha)
    #aabbcc  → aabbcc
    #aabbccdd → aabbcc (strip alpha)
    """
    h = raw.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        h = h[:6]
    return h


def parse_rgb(raw: str) -> Optional[Tuple[int, int, int]]:
    """Return (R, G, B) tuple or None if the hex string is invalid."""
    h = normalise_hex(raw)
    if len(h) != 6:
        return None
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return r, g, b
    except ValueError:
        return None


def is_grey(r: int, g: int, b: int, tolerance: int = 8) -> bool:
    """
    True if the colour is achromatic within the given tolerance.

    Default tolerance ±8 matches the CUT monochrome design rule.
    """
    return max(abs(r - g), abs(r - b), abs(g - b)) <= tolerance


def is_allowed_red(r: int, g: int, b: int) -> bool:
    """
    Playhead / error red exemption.

    Dominant red channel, low green and blue.
    Covers #cc3333, #c44, #ef4444 family.
    """
    return r >= 150 and g <= 100 and b <= 100


def is_chromatic(hex_color: str) -> bool:
    """
    Convenience: True if a hex colour string is NOT grey and NOT allowed red.

    Used by test_gamma_polish_visual_regression.py variant.
    """
    rgb = parse_rgb(hex_color)
    if rgb is None:
        return False
    r, g, b = rgb
    if is_grey(r, g, b):
        return False
    if is_allowed_red(r, g, b):
        return False
    return True
