"""PDF watermark generator.

Uses reportlab to stamp a text watermark onto an in-memory PDF page,
then PyPDF2 to merge it onto every page of the original document.
"""

import io

from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

from config import WatermarkSettings, compute_fit_scale

_FONT_NAME = "Helvetica-Bold"


def _create_watermark_page(settings, page_width, page_height):
    """Return a BytesIO containing a single-page PDF with the watermark."""
    packet = io.BytesIO()
    c = rl_canvas.Canvas(packet, pagesize=(page_width, page_height))

    r, g, b = [v / 255.0 for v in settings.color_rgb]
    font_size = settings.font_size

    # Measure and scale down to avoid clipping
    tw = stringWidth(settings.text, _FONT_NAME, font_size)
    scale = compute_fit_scale(tw, font_size, page_width, page_height, settings.rotation)
    font_size *= scale
    tw = stringWidth(settings.text, _FONT_NAME, font_size)

    stroke_w = max(0.5, font_size / 30.0)

    c.saveState()
    c.translate(page_width / 2, page_height / 2)
    c.rotate(settings.rotation)

    c.setFont(_FONT_NAME, font_size)
    c.setFillColor(Color(r, g, b, alpha=settings.opacity))
    c.setStrokeColor(Color(r, g, b, alpha=settings.opacity))
    c.setLineWidth(stroke_w)

    # Render mode 2 = fill + stroke for a bolder look
    text_obj = c.beginText()
    text_obj.setTextRenderMode(2)
    text_obj.setTextOrigin(-tw / 2, -font_size * 0.3)
    text_obj.textLine(settings.text)
    c.drawText(text_obj)

    c.restoreState()
    c.save()
    packet.seek(0)
    return packet


def apply_watermark(input_path, output_path, settings):
    """Read *input_path*, stamp every page, write to *output_path*.

    Parameters
    ----------
    input_path : str
        Path to the source PDF.
    output_path : str
        Destination path for the watermarked PDF.
    settings : WatermarkSettings
        Watermark configuration.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        wm_stream = _create_watermark_page(settings, w, h)
        wm_page = PdfReader(wm_stream).pages[0]
        page.merge_page(wm_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
