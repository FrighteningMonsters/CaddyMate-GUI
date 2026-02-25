"""
Provides consistent button creation and styling across multiple modules.
"""
import tkinter as tk
from styles import PRIMARY, PRIMARY_HOVER, SECONDARY, ACCENT, ACCENT_HOVER, TEXT


def make_button(parent, text, command, fonts, large=True, primary=True, width=None, accent=False):
    """
    Creates a standardized button widget with hover effects.
    
    Args:
        parent: The parent widget/frame
        text: Button label text
        command: Callback function when clicked
        fonts: Dictionary of fonts (from styles.load_fonts)
        large: Whether to use large button size (default: True)
        primary: Whether to use primary color scheme (default: True)
        width: Button width in characters (auto-sized if None)
        accent: Whether to use accent color (overrides primary)
    
    Returns:
        tk.Button: The configured button widget
    """
    if width is None:
        width = 18 if large else 16

    # Determine colors based on button type
    if accent:
        bg_color = ACCENT
        active_bg = ACCENT_HOVER
    elif primary:
        bg_color = PRIMARY
        active_bg = PRIMARY_HOVER
    else:
        bg_color = SECONDARY
        active_bg = "#d1d5db"

    btn = tk.Button(
        parent,
        text=text,
        font=fonts["button"] if large else fonts["small"],
        width=width,
        height=2 if large else 1,
        bg=bg_color,
        fg="white" if (primary or accent) else TEXT,
        activebackground=active_bg,
        activeforeground="white" if (primary or accent) else TEXT,
        bd=0,
        relief="flat",
        command=command,
        cursor="hand2"
    )
    
    # Add hover effects
    def on_enter(e):
        btn.config(bg=active_bg)
    
    def on_leave(e):
        btn.config(bg=bg_color)
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn


def make_back_button(parent, callback, fonts, padx=0):
    """
    Creates a standardized back button widget.
    
    Args:
        parent: The parent frame for the button
        callback: Function to call when back button is clicked
        fonts: Dictionary of fonts (from styles.load_fonts)
        padx: Horizontal padding when packing (default: 0)
    
    Returns:
        tk.Button: The configured back button widget
    """
    btn = make_button(
        parent,
        "← Back",
        callback,
        fonts,
        large=False,
        primary=False,
        width=8
    )
    btn.pack(side="right", padx=padx)
    return btn
