"""
MARKER_SPLIT_FORMATS — CUT Export Presets + Resolution Map.

Extracted from cut_render_engine.py (MARKER_B5 split).
Delivery presets (social + production) and resolution definitions.

@status: active
@phase: B5
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Resolution presets
# ---------------------------------------------------------------------------

RESOLUTION_MAP: dict[str, tuple[int, int] | None] = {
    "8k": (7680, 4320),
    "4k": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "source": None,
}


# ---------------------------------------------------------------------------
# MARKER_B2.3: Export presets — social + production
# ---------------------------------------------------------------------------

EXPORT_PRESETS: dict[str, dict[str, Any]] = {
    # === Social / Delivery ===
    "youtube_1080": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 85,
                     "label": "YouTube 1080p"},
    "youtube_4k": {"codec": "h264", "resolution": "4k", "fps": 30, "quality": 90,
                   "label": "YouTube 4K"},
    "instagram_reels": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
                        "aspect": "9:16", "label": "Instagram Reels (9:16)"},
    "instagram_story": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 75,
                        "aspect": "9:16", "label": "Instagram Story (9:16)"},
    "tiktok": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
               "aspect": "9:16", "label": "TikTok (9:16)"},
    "telegram": {"codec": "h264", "resolution": "720p", "fps": 30, "quality": 70,
                 "label": "Telegram (720p)"},
    "twitter": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
                "label": "Twitter/X"},
    "vimeo": {"codec": "h264", "resolution": "1080p", "fps": 25, "quality": 90,
              "label": "Vimeo (high quality)"},
    # === Production / Archive ===
    # MARKER_B6.1: Full ProRes family
    "prores_proxy": {"codec": "prores_proxy", "resolution": "source", "fps": 25, "quality": 100,
                     "label": "ProRes Proxy (Offline)"},
    "prores_lt": {"codec": "prores_lt", "resolution": "source", "fps": 25, "quality": 100,
                  "label": "ProRes LT (Lightweight)"},
    "prores_422_standard": {"codec": "prores_422", "resolution": "source", "fps": 25, "quality": 100,
                            "label": "ProRes 422 (Standard)"},
    "prores_master": {"codec": "prores_422hq", "resolution": "source", "fps": 25, "quality": 100,
                      "label": "ProRes 422 HQ (Master)"},
    "prores_4444": {"codec": "prores_4444", "resolution": "4k", "fps": 25, "quality": 100,
                    "label": "ProRes 4444 (Archive)"},
    "prores_4444xq": {"codec": "prores_4444xq", "resolution": "4k", "fps": 25, "quality": 100,
                      "label": "ProRes 4444 XQ (Maximum)"},
    "dnxhr_hq": {"codec": "dnxhr_hq", "resolution": "1080p", "fps": 25, "quality": 100,
                 "label": "DNxHR HQ (Avid)"},
    "review_h264": {"codec": "h264", "resolution": "720p", "fps": 25, "quality": 60,
                    "label": "Review Copy (720p, fast)"},
    # === Web / Modern ===
    "av1_web": {"codec": "av1", "resolution": "1080p", "fps": 30, "quality": 80,
                "label": "AV1 Web (small file)"},
    "vp9_webm": {"codec": "vp9", "resolution": "1080p", "fps": 30, "quality": 80,
                 "label": "VP9 WebM"},
}

# Backward compat aliases
EXPORT_PRESETS["youtube"] = EXPORT_PRESETS["youtube_1080"]
SOCIAL_PRESETS = EXPORT_PRESETS
