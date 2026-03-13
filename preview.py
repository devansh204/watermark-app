"""Pillow-based watermark preview renderer.

Composites a semi-transparent, rotated text watermark onto a page image
for real-time display in the UI.
"""

from PIL import Image, ImageDraw

from config import WatermarkSettings, compute_fit_scale, get_font


def render(page_image, settings):
    """Return a new RGB image with the watermark composited on top.

    Parameters
    ----------
    page_image : PIL.Image.Image
        The base page (any mode; will be converted to RGBA internally).
    settings : WatermarkSettings
        Text, font size, opacity, rotation and colour for the watermark.
    """
    text = settings.text
    if not text or not text.strip():
        return page_image.copy()

    base = page_image.convert("RGBA")
    font_size = max(int(settings.font_size), 8)
    font = get_font(font_size)
    stroke = max(1, font_size // 30)

    alpha = int(max(0.0, min(1.0, settings.opacity)) * 255)
    r, g, b = settings.color_rgb
    fill = (r, g, b, alpha)

    # ── Measure & scale ──────────────────────────────────────────────
    draw = ImageDraw.Draw(base)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if tw <= 0 or th <= 0:
        return page_image.copy()

    scale = compute_fit_scale(tw, th, base.width, base.height, settings.rotation)
    if scale < 1.0:
        font_size = max(8, int(font_size * scale))
        font = get_font(font_size)
        stroke = max(1, font_size // 30)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # ── Draw rotated stamp ───────────────────────────────────────────
    pad = 20 + stroke * 2
    stamp = Image.new("RGBA", (tw + pad, th + pad), (0, 0, 0, 0))
    ImageDraw.Draw(stamp).text(
        (pad // 2, pad // 2), text, font=font, fill=fill,
        stroke_width=stroke, stroke_fill=fill,
    )
    rotated = stamp.rotate(settings.rotation, expand=True, resample=Image.BICUBIC)

    # ── Composite centered ───────────────────────────────────────────
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    cx = (base.width - rotated.width) // 2
    cy = (base.height - rotated.height) // 2
    layer.paste(rotated, (cx, cy), rotated)

    return Image.alpha_composite(base, layer).convert("RGB")
