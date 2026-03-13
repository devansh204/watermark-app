# PDF Watermark Tool

A desktop application for macOS that adds customizable text watermarks to PDF documents. Built with Python and CustomTkinter.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

- **Live Preview** — See your watermark overlaid on the actual PDF page in real time as you adjust settings.
- **Customizable Text** — Set any watermark text (e.g. CONFIDENTIAL, DRAFT, DO NOT COPY).
- **Font Size Control** — Slider from 12pt to 120pt.
- **Opacity** — Adjust transparency from 5% to 100%.
- **Rotation** — Rotate the watermark from -180° to +180°.
- **Color Presets** — Choose from Red, Gray, Blue, Green, Black, or Orange.
- **Multi-Page Support** — Navigate through pages and apply the watermark to every page on export.
- **One-Click Export** — Generates a new watermarked PDF without modifying the original.

---

## Screenshots

| Main Interface |
|:-:|
| *Open a PDF, adjust watermark settings on the left, see a live preview on the right.* |

---

## Installation

### Prerequisites

- Python 3.9 or later
- macOS (primary target; may work on Linux/Windows with minor font path adjustments)

### Setup

```bash
git clone https://github.com/devansh204/watermark-app.git
cd watermark-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

---

## Building a Standalone macOS App

You can bundle the tool into a native `.app` you can launch from Spotlight or the Dock:

```bash
pip install py2app
python setup.py py2app
```

The built app will be at `dist/PDF Watermark Tool.app`. Copy it to `/Applications`:

```bash
cp -R "dist/PDF Watermark Tool.app" /Applications/
```

---

## Project Structure

```
watermark-app/
├── app.py             # Entry point
├── ui.py              # CustomTkinter GUI (controls, preview, navigation)
├── generator.py       # PDF watermark stamping (reportlab + PyPDF2)
├── preview.py         # Pillow-based live preview renderer
├── config.py          # Shared settings, color presets, font resolution
├── setup.py           # py2app build configuration
└── requirements.txt   # Python dependencies
```

---

## Dependencies

| Package | Purpose |
|---|---|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Modern themed Tkinter UI |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | PDF page rendering for preview |
| [Pillow](https://python-pillow.org/) | Image compositing and watermark preview |
| [PyPDF2](https://pypdf2.readthedocs.io/) | PDF reading/writing and page merging |
| [reportlab](https://www.reportlab.com/) | Generating the watermark overlay PDF |

---

## How It Works

1. **Open a PDF** — PyMuPDF renders each page to a bitmap for the live preview.
2. **Adjust settings** — Sliders and controls update a `WatermarkSettings` dataclass; changes trigger a debounced re-render.
3. **Preview** — Pillow composites a semi-transparent, rotated text stamp onto the page image.
4. **Export** — reportlab creates a single-page PDF containing just the watermark text, then PyPDF2 merges it onto every page of the original document.

---

## License

MIT
