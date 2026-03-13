"""py2app build script for PDF Watermark Tool.

Usage:
    python setup.py py2app
"""

import os
import customtkinter

from setuptools import setup

CTK_DIR = os.path.dirname(customtkinter.__file__)

APP = ["app.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "packages": [
        "customtkinter",
        "PIL",
        "fitz",
        "PyPDF2",
        "reportlab",
        "tkinter",
    ],
    "includes": ["ui", "generator", "preview", "config"],
    "frameworks": [],
    "resources": [CTK_DIR],
    "plist": {
        "CFBundleName": "PDF Watermark Tool",
        "CFBundleDisplayName": "PDF Watermark Tool",
        "CFBundleIdentifier": "com.devansh.pdfwatermark",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    name="PDF Watermark Tool",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
