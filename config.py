"""Shared constants, font resolution, watermark settings, and geometry utilities."""

import math
import os
from dataclasses import dataclass

from PIL import ImageFont

# ── Color presets ─────────────────────────────────────────────────────────

COLOR_PRESETS = {
    "Red": (255, 0, 0),
    "Gray": (128, 128, 128),
    "Blue": (0, 0, 200),
    "Green": (0, 128, 0),
    "Black": (0, 0, 0),
    "Orange": (255, 140, 0),
}

# ── Watermark settings bundle ────────────────────────────────────────────

@dataclass
class WatermarkSettings:
    text: str = "CONFIDENTIAL"
    font_size: float = 54
    opacity: float = 0.3
    rotation: float = -45
    color_rgb: tuple = (255, 0, 0)


# ── Font resolution ──────────────────────────────────────────────────────
# Walks a priority list of bold system fonts on macOS and picks the first
# one that Pillow can actually load.  Falls back gracefully on other OSes.

_BOLD_CANDIDATES = [
    ("/System/Library/Fonts/Helvetica.ttc", 1),        # Helvetica Bold
    ("/Library/Fonts/Arial Bold.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/System/Library/Fonts/Helvetica.ttc", 0),         # regular Helvetica
    ("/Library/Fonts/Arial.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
]

_font_path = None
_font_index = 0

for _candidate, _idx in _BOLD_CANDIDATES:
    if os.path.isfile(_candidate):
        try:
            ImageFont.truetype(_candidate, 40, index=_idx)
            _font_path = _candidate
            _font_index = _idx
            break
        except (OSError, IOError):
            continue


def get_font(size):
    """Return a Pillow TrueType font at the requested *size*."""
    if _font_path:
        return ImageFont.truetype(_font_path, size, index=_font_index)
    for name in ("Helvetica-Bold", "Helvetica"):
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── Geometry helpers ─────────────────────────────────────────────────────

OVERFLOW_MARGIN = 0.85


def compute_fit_scale(text_w, text_h, container_w, container_h, rotation_deg):
    """Return a scale factor (<=1) that keeps rotated text inside the container.

    Both the preview renderer and the PDF generator call this so their
    overflow behaviour is identical.
    """
    rad = math.radians(rotation_deg)
    cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
    rotated_w = text_w * cos_a + text_h * sin_a
    rotated_h = text_w * sin_a + text_h * cos_a

    scale_x = (container_w * OVERFLOW_MARGIN) / rotated_w if rotated_w > 0 else 1.0
    scale_y = (container_h * OVERFLOW_MARGIN) / rotated_h if rotated_h > 0 else 1.0
    return min(scale_x, scale_y, 1.0)
