"""CustomTkinter UI for the PDF Watermark tool."""

import os
import platform
import subprocess
import threading

import customtkinter as ctk
import fitz  # PyMuPDF
from PIL import Image
from tkinter import filedialog, messagebox

from config import COLOR_PRESETS, WatermarkSettings
from generator import apply_watermark
from preview import render as render_preview

_DEBOUNCE_MS = 60
_PREVIEW_ZOOM = 2.0


class WatermarkApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("PDF Watermark Tool")
        self.geometry("1100x720")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State
        self._pdf_path = None
        self._pdf_doc = None
        self._page_cache = {}
        self._current_page = 0
        self._total_pages = 0
        self._preview_job = None
        self._ctk_image_ref = None  # prevent garbage collection

        self._build_controls()
        self._build_preview_panel()
        self.bind("<Configure>", lambda _: self._schedule_preview_if_loaded())

    # ══════════════════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════════════════

    def _build_controls(self):
        """Left sidebar with file picker, watermark knobs and generate button."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkScrollableFrame(self, width=260, corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        row = 0

        # Header
        row = self._add_label(panel, row, "PDF Watermark", size=20, bold=True, top=20)
        row = self._add_label(panel, row, "Add text watermarks to your PDFs",
                              size=12, color="gray", bottom=12)

        # File picker
        self._open_btn = ctk.CTkButton(panel, text="Open PDF…", command=self._open_pdf)
        self._open_btn.grid(row=row, column=0, padx=16, pady=(4, 4), sticky="ew")
        row += 1
        self._file_label = ctk.CTkLabel(
            panel, text="No file selected", font=ctk.CTkFont(size=11), text_color="gray")
        self._file_label.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w")
        row += 1

        row = self._add_separator(panel, row)

        # Watermark text
        row = self._add_label(panel, row, "Watermark Text")
        self._text_var = ctk.StringVar(value="CONFIDENTIAL")
        ctk.CTkEntry(panel, textvariable=self._text_var).grid(
            row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        self._text_var.trace_add("write", lambda *_: self._schedule_preview())
        row += 1

        # Sliders
        self._size_var, self._size_lbl, row = self._add_slider(
            panel, row, "Font Size", 12, 120, 54, self._fmt_int)
        self._opacity_var, self._opacity_lbl, row = self._add_slider(
            panel, row, "Opacity", 0.05, 1.0, 0.3, self._fmt_pct)
        self._rotation_var, self._rotation_lbl, row = self._add_slider(
            panel, row, "Rotation", -180, 180, -45, self._fmt_deg)

        # Color picker
        row = self._add_label(panel, row, "Color")
        self._color_var = ctk.StringVar(value="Red")
        ctk.CTkOptionMenu(
            panel, values=list(COLOR_PRESETS.keys()),
            variable=self._color_var, command=lambda _: self._schedule_preview()
        ).grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        row += 1

        row = self._add_separator(panel, row)

        # Page navigation
        nav = ctk.CTkFrame(panel, fg_color="transparent")
        nav.grid(row=row, column=0, padx=16, pady=(4, 4), sticky="ew")
        nav.grid_columnconfigure(1, weight=1)
        self._prev_btn = ctk.CTkButton(nav, text="◀", width=36,
                                        command=self._prev_page, state="disabled")
        self._prev_btn.grid(row=0, column=0, padx=(0, 4))
        self._page_label = ctk.CTkLabel(nav, text="Page – / –", font=ctk.CTkFont(size=13))
        self._page_label.grid(row=0, column=1)
        self._next_btn = ctk.CTkButton(nav, text="▶", width=36,
                                        command=self._next_page, state="disabled")
        self._next_btn.grid(row=0, column=2, padx=(4, 0))
        row += 1

        row = self._add_separator(panel, row)

        # Generate
        self._gen_btn = ctk.CTkButton(
            panel, text="Generate Watermarked PDF", height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._generate, state="disabled")
        self._gen_btn.grid(row=row, column=0, padx=16, pady=(4, 20), sticky="ew")

    def _build_preview_panel(self):
        """Right panel showing the live watermark preview."""
        self._preview_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="gray14")
        self._preview_frame.grid(row=0, column=1, sticky="nsew")
        self._preview_frame.grid_rowconfigure(0, weight=1)
        self._preview_frame.grid_columnconfigure(0, weight=1)

        self._preview_label = ctk.CTkLabel(
            self._preview_frame, text="Open a PDF to begin",
            font=ctk.CTkFont(size=16), text_color="gray")
        self._preview_label.grid(row=0, column=0, sticky="nsew")

    # ── Widget helpers ────────────────────────────────────────────────

    @staticmethod
    def _add_label(parent, row, text, size=13, bold=False, color=None, top=8, bottom=2):
        font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
        kw = {"text_color": color} if color else {}
        ctk.CTkLabel(parent, text=text, font=font, **kw).grid(
            row=row, column=0, padx=16, pady=(top, bottom), sticky="w")
        return row + 1

    @staticmethod
    def _add_separator(parent, row):
        ctk.CTkFrame(parent, height=2, fg_color="gray25").grid(
            row=row, column=0, padx=16, pady=8, sticky="ew")
        return row + 1

    def _add_slider(self, parent, row, label, lo, hi, default, formatter):
        """Add a labelled slider and return (variable, value_label, next_row)."""
        row = self._add_label(parent, row, label)
        val_label = ctk.CTkLabel(parent, text=formatter(default),
                                 font=ctk.CTkFont(size=11), text_color="gray")
        val_label.grid(row=row, column=0, padx=16, sticky="e")
        var = ctk.DoubleVar(value=default)

        def on_change(v):
            val_label.configure(text=formatter(float(v)))
            self._schedule_preview()

        ctk.CTkSlider(parent, from_=lo, to=hi, variable=var,
                       command=on_change).grid(
            row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        return var, val_label, row + 1

    @staticmethod
    def _fmt_int(v):
        return str(int(v))

    @staticmethod
    def _fmt_pct(v):
        return "{}%".format(int(v * 100))

    @staticmethod
    def _fmt_deg(v):
        return "{}°".format(int(v))

    # ══════════════════════════════════════════════════════════════════
    #  Settings snapshot
    # ══════════════════════════════════════════════════════════════════

    def _current_settings(self, font_size_override=None):
        """Build a WatermarkSettings from the current control values."""
        return WatermarkSettings(
            text=self._text_var.get(),
            font_size=font_size_override or self._size_var.get(),
            opacity=self._opacity_var.get(),
            rotation=self._rotation_var.get(),
            color_rgb=COLOR_PRESETS.get(self._color_var.get(), (255, 0, 0)),
        )

    # ══════════════════════════════════════════════════════════════════
    #  File open
    # ══════════════════════════════════════════════════════════════════

    def _open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        self._pdf_path = path
        if self._pdf_doc:
            self._pdf_doc.close()
        self._pdf_doc = fitz.open(path)
        self._total_pages = len(self._pdf_doc)
        self._current_page = 0
        self._page_cache.clear()

        self._file_label.configure(text=os.path.basename(path))
        self._sync_page_nav()
        self._gen_btn.configure(state="normal")

        self.update_idletasks()
        self._render_preview()

    # ══════════════════════════════════════════════════════════════════
    #  Page navigation
    # ══════════════════════════════════════════════════════════════════

    def _sync_page_nav(self):
        self._page_label.configure(
            text="Page {} / {}".format(self._current_page + 1, self._total_pages))
        self._prev_btn.configure(
            state="normal" if self._current_page > 0 else "disabled")
        self._next_btn.configure(
            state="normal" if self._current_page < self._total_pages - 1 else "disabled")

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._sync_page_nav()
            self._schedule_preview()

    def _next_page(self):
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._sync_page_nav()
            self._schedule_preview()

    # ══════════════════════════════════════════════════════════════════
    #  Preview rendering (debounced)
    # ══════════════════════════════════════════════════════════════════

    def _schedule_preview_if_loaded(self):
        if self._pdf_doc is not None:
            self._schedule_preview()

    def _schedule_preview(self):
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(_DEBOUNCE_MS, self._render_preview)

    def _get_page_image(self, page_num):
        """Render a PDF page to a PIL Image, caching the result."""
        if page_num in self._page_cache:
            return self._page_cache[page_num]
        page = self._pdf_doc[page_num]
        mat = fitz.Matrix(_PREVIEW_ZOOM, _PREVIEW_ZOOM)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self._page_cache[page_num] = img
        return img

    def _render_preview(self):
        self._preview_job = None
        if self._pdf_doc is None:
            return

        page_img = self._get_page_image(self._current_page)
        display_w, display_h, scale = self._fit_to_preview(page_img.size)
        scaled = page_img.resize((display_w, display_h), Image.LANCZOS)

        settings = self._current_settings(font_size_override=max(8, int(self._size_var.get() * scale)))
        composited = render_preview(scaled, settings)

        ctk_img = ctk.CTkImage(light_image=composited, dark_image=composited,
                                size=(display_w, display_h))
        self._preview_label.configure(image=ctk_img, text="")
        self._ctk_image_ref = ctk_img

    def _fit_to_preview(self, image_size):
        """Return (display_w, display_h, scale) to fit *image_size* in the preview area."""
        pw = self._preview_frame.winfo_width()
        ph = self._preview_frame.winfo_height()
        if pw < 50:
            pw = 700
        if ph < 50:
            ph = 600
        margin = 40
        max_w, max_h = pw - margin, ph - margin

        img_w, img_h = image_size
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        return max(int(img_w * scale), 1), max(int(img_h * scale), 1), scale

    # ══════════════════════════════════════════════════════════════════
    #  Generate watermarked PDF
    # ══════════════════════════════════════════════════════════════════

    def _generate(self):
        if not self._pdf_path:
            return

        base_name = os.path.splitext(os.path.basename(self._pdf_path))[0]
        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile="{}_watermarked.pdf".format(base_name),
        )
        if not output_path:
            return

        self._gen_btn.configure(state="disabled", text="Generating…")
        self.update_idletasks()

        settings = self._current_settings()
        input_path = self._pdf_path

        def _worker():
            try:
                apply_watermark(input_path, output_path, settings)
                self.after(0, lambda: self._on_generate_done(output_path))
            except Exception as e:
                self.after(0, lambda: self._on_generate_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_generate_done(self, output_path):
        self._gen_btn.configure(state="normal", text="Generate Watermarked PDF")
        if messagebox.askyesno(
            "Success",
            "Watermarked PDF saved!\n\n{}\n\nReveal in Finder?".format(output_path),
        ) and platform.system() == "Darwin":
            subprocess.run(["open", "-R", output_path])

    def _on_generate_error(self, error_msg):
        self._gen_btn.configure(state="normal", text="Generate Watermarked PDF")
        messagebox.showerror("Error", "Failed to generate PDF:\n\n{}".format(error_msg))
