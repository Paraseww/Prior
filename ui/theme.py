"""
ui/theme.py
Design tokens, color schemes, typography, and quadrant styling for Prior.
Supports seamless Dark Mode and Light Mode with CustomTkinter.
"""

from typing import Any, Dict, Tuple

# ============================================================================
# Core Color Tokens (Light, Dark)
# ============================================================================

# Application background & surfaces
BG_MAIN: Tuple[str, str] = ("#F7F5F0", "#000000")       # Creamy Soft Paper / Pure Black
BG_SIDEBAR: Tuple[str, str] = ("#EFEAE1", "#0A0A0A")    # Warm Soft Cream / Rich Black
BG_CARD: Tuple[str, str] = ("#FDFBF7", "#121212")       # Warm Soft Cream Card / Elevate Dark Card
BG_CARD_HOVER: Tuple[str, str] = ("#F4EFE6", "#1E1E1E") # Soft Cream Hover / Subtle Hover Black
BG_INPUT: Tuple[str, str] = ("#EFEAE1", "#0A0A0A")      # Recessed Cream Input / Recessed Black
BORDER_COLOR: Tuple[str, str] = ("#E2DDD5", "#262626")  # Warm Soft Border / Sleek Dark Border

# Text colors
TEXT_PRIMARY: Tuple[str, str] = ("#1C1917", "#FFFFFF")    # Deep Warm Stone / Crisp White
TEXT_SECONDARY: Tuple[str, str] = ("#6B6661", "#A3A3A3")  # Warm Charcoal Slate / Neutral Gray
TEXT_MUTED: Tuple[str, str] = ("#9E9891", "#737373")      # Warm Muted Gray / Dim Gray

# Brand accent
ACCENT_PRIMARY: Tuple[str, str] = ("#6366F1", "#818CF8")  # Indigo 500 / Indigo 400
ACCENT_HOVER: Tuple[str, str] = ("#4F46E5", "#6366F1")    # Indigo 600 / Indigo 500

# ============================================================================
# Eisenhower Quadrant Themes
# ============================================================================

QUADRANTS: Dict[str, Dict[str, Any]] = {
    "Q1_DO": {
        "title": "Urgent & Important",
        "subtitle": "Do First — Immediate crises & critical deadlines",
        "badge": "DO FIRST",
        "color": "#EF4444",          # Red 500 (Signals urgency / act now)
        "color_dark": "#DC2626",     # Red 600
        "bg_header": ("#FEF2F2", "#2A0A0A"),  # Red 50 / Deep Black-Red tint
        "border": ("#F87171", "#7F1D1D"),     # Red 400 / Red 900
        "text": ("#991B1B", "#F87171"),       # Red 800 / Red 400
    },
    "Q2_SCHEDULE": {
        "title": "Not Urgent & Important",
        "subtitle": "Schedule — Long-term growth, planning & deep work",
        "badge": "SCHEDULE",
        "color": "#10B981",          # Emerald 500 / Green (Growth & long-term value)
        "color_dark": "#059669",     # Emerald 600
        "bg_header": ("#ECFDF5", "#042218"),  # Emerald 50 / Deep Black-Green tint
        "border": ("#34D399", "#064E3B"),     # Emerald 400 / Emerald 900
        "text": ("#065F46", "#34D399"),       # Emerald 800 / Emerald 400
    },
    "Q3_DELEGATE": {
        "title": "Urgent & Not Important",
        "subtitle": "Delegate — Interruptions, quick requests & busywork",
        "badge": "DELEGATE",
        "color": "#F59E0B",          # Amber 500 / Yellow (Caution - needs attention)
        "color_dark": "#D97706",     # Amber 600
        "bg_header": ("#FFFBEB", "#261603"),  # Amber 50 / Deep Black-Amber tint
        "border": ("#FBBF24", "#78350F"),     # Amber 400 / Amber 900
        "text": ("#92400E", "#FBBF24"),       # Amber 800 / Amber 400
    },
    "Q4_ELIMINATE": {
        "title": "Not Urgent & Not Important",
        "subtitle": "Eliminate — Distractions, time wasters & clutter",
        "badge": "DELETE",
        "color": "#3B82F6",          # Blue 500 (Calm, low energy - safe to drop)
        "color_dark": "#2563EB",     # Blue 600
        "bg_header": ("#EFF6FF", "#0A192F"),  # Blue 50 / Deep Black-Blue tint
        "border": ("#60A5FA", "#1E3A8A"),     # Blue 400 / Blue 900
        "text": ("#1E40AF", "#60A5FA"),       # Blue 800 / Blue 400
    },
}

# Due date badge colors
DUE_BADGE_COLORS = {
    "red": ("#FEE2E2", "#2A0A0A", "#B91C1C", "#F87171"),      # Overdue (bg_l, bg_d, text_l, text_d)
    "amber": ("#FEF3C7", "#261603", "#B45309", "#FBBF24"),    # Due Today
    "blue": ("#DBEAFE", "#0A192F", "#1D4ED8", "#60A5FA"),     # Upcoming
    "gray": ("#EFEAE1", "#1E1E1E", "#6B6661", "#A3A3A3"),     # No Date
}

# ============================================================================
# Typography & Custom Wireframe Fonts
# ============================================================================

import ctypes
import os
from pathlib import Path
import sys

_FONTS_LOADED = False

def load_custom_fonts() -> None:
    """Loads bundled TrueType wireframe fonts (Comic Neue) into Windows process memory."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return

    if sys.platform == "win32":
        try:
            gdi32 = ctypes.windll.gdi32
            fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
            if fonts_dir.exists():
                for font_file in fonts_dir.glob("*.ttf"):
                    gdi32.AddFontResourceExW(str(font_file), 0x10, 0)
        except Exception:
            pass
    _FONTS_LOADED = True

# Call font loader immediately upon module import
load_custom_fonts()

FONT_FAMILY = "Comic Neue"
FONT_DISPLAY = "Comic Neue"

def get_font(size: int = 14, weight: str = "normal") -> tuple:
    """Returns a standardized font tuple for CustomTkinter widgets."""
    return (FONT_FAMILY, size, weight)


from ui.windows_integration import apply_prior_icon


# Global hook for CustomTkinter Windows titlebar icon and smooth color switching
try:
    import customtkinter as _ctk

    def _custom_windows_set_titlebar_icon(self: Any) -> None:
        apply_prior_icon(self)

    def _smooth_windows_set_titlebar_color(self: Any, color_mode: str) -> None:
        """Sets Windows titlebar dark/light mode in-place without blinking, withdraw(), or unmapping."""
        def _apply() -> None:
            try:
                val = ctypes.c_int(1 if color_mode.lower() == "dark" else 0)
                wid = self.winfo_id()
                if wid:
                    hwnd = ctypes.windll.user32.GetParent(wid) or wid
                    if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)) != 0:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
            except Exception:
                pass

        _apply()
        try:
            self.after(50, _apply)
        except Exception:
            pass

    _ctk.CTk._windows_set_titlebar_icon = _custom_windows_set_titlebar_icon
    _ctk.CTkToplevel._windows_set_titlebar_icon = _custom_windows_set_titlebar_icon
    _ctk.CTk._windows_set_titlebar_color = _smooth_windows_set_titlebar_color
    _ctk.CTkToplevel._windows_set_titlebar_color = _smooth_windows_set_titlebar_color
except Exception:
    pass

