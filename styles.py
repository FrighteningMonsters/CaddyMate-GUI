import tkinter as tk
from tkinter import font

BG_COLOR = "#ffffff"
PRIMARY = "#2563eb"
PRIMARY_DARK = "#1e40af"
SECONDARY = "#e5e7eb"
TEXT = "#111827"

def load_fonts(root):
    """Creates and returns a dictionary of standard fonts used in the application."""
    return {
        "title": font.Font(root=root, size=34, weight="bold"),
        "button": font.Font(root=root, size=26, weight="bold"),
        "small": font.Font(root=root, size=20),
        "result": font.Font(root=root, size=30),
    }
