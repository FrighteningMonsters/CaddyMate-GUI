import tkinter as tk
from tkinter import font

# Modern color palette
BG_COLOR = "#f8fafc"  # Light gray background
CARD_BG = "#ffffff"   # White cards
PRIMARY = "#3b82f6"   # Modern blue
PRIMARY_HOVER = "#2563eb"  # Darker blue on hover
PRIMARY_DARK = "#1e40af"   # Even darker blue
SECONDARY = "#e5e7eb"      # Light gray
ACCENT = "#8b5cf6"         # Purple accent
ACCENT_HOVER = "#7c3aed"   # Darker purple
TEXT = "#111827"           # Dark text
TEXT_LIGHT = "#6b7280"     # Gray text
SHADOW = "#00000015"       # Subtle shadow
BORDER = "#e2e8f0"         # Light border

def load_fonts(root):
    """Creates and returns a dictionary of standard fonts used in the application."""
    return {
        "title": font.Font(root=root, size=28, weight="bold"),
        "subtitle": font.Font(root=root, size=13),
        "button": font.Font(root=root, size=20, weight="bold"),
        "small": font.Font(root=root, size=18),
        "result": font.Font(root=root, size=26),
    }
