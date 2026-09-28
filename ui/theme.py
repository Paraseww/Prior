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
BG_MAIN: Tuple[str, str] = ("#F8FAFC", "#0F172A")       # Slate 50 / Slate 900
BG_SIDEBAR: Tuple[str, str] = ("#FFFFFF", "#1E293B")    # White / Slate 800
BG_CARD: Tuple[str, str] = ("#FFFFFF", "#1E293B")       # White / Slate 800
BG_CARD_HOVER: Tuple[str, str] = ("#F1F5F9", "#334155") # Slate 100 / Slate 700
BG_INPUT: Tuple[str, str] = ("#F1F5F9", "#0F172A")      # Slate 100 / Slate 900
BORDER_COLOR: Tuple[str, str] = ("#E2E8F0", "#334155")  # Slate 200 / Slate 700

# Text colors
TEXT_PRIMARY: Tuple[str, str] = ("#0F172A", "#F8FAFC")    # Slate 900 / Slate 50
TEXT_SECONDARY: Tuple[str, str] = ("#64748B", "#94A3B8")  # Slate 500 / Slate 400
TEXT_MUTED: Tuple[str, str] = ("#94A3B8", "#64748B")      # Slate 400 / Slate 500

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
        "color": "#10B981",          # Emerald 500
        "color_dark": "#059669",     # Emerald 600
        "bg_header": ("#ECFDF5", "#064E3B"),  # Emerald 50 / Emerald 900
        "border": ("#A7F3D0", "#047857"),     # Emerald 200 / Emerald 700
        "text": ("#065F46", "#34D399"),       # Emerald 800 / Emerald 400
    },
    "Q2_SCHEDULE": {
        "title": "Not Urgent & Important",
        "subtitle": "Schedule — Long-term growth, planning & deep work",
        "badge": "SCHEDULE",
        "color": "#3B82F6",          # Blue 500
        "color_dark": "#2563EB",     # Blue 600
        "bg_header": ("#EFF6FF", "#1E3A8A"),  # Blue 50 / Blue 900
        "border": ("#BFDBFE", "#1D4ED8"),     # Blue 200 / Blue 700
        "text": ("#1E40AF", "#60A5FA"),       # Blue 800 / Blue 400
    },
    "Q3_DELEGATE": {
        "title": "Urgent & Not Important",
        "subtitle": "Delegate — Interruptions, quick requests & busywork",
        "badge": "DELEGATE",
        "color": "#F59E0B",          # Amber 500
        "color_dark": "#D97706",     # Amber 600
        "bg_header": ("#FFFBEB", "#78350F"),  # Amber 50 / Amber 900
        "border": ("#FDE68A", "#B45309"),     # Amber 200 / Amber 700
        "text": ("#92400E", "#FBBF24"),       # Amber 800 / Amber 400
    },
    "Q4_ELIMINATE": {
        "title": "Not Urgent & Not Important",
        "subtitle": "Eliminate — Distractions, time wasters & clutter",
        "badge": "ELIMINATE",
        "color": "#EF4444",          # Red 500
        "color_dark": "#DC2626",     # Red 600
        "bg_header": ("#FEF2F2", "#7F1D1D"),  # Red 50 / Red 900
        "border": ("#FECACA", "#B91C1C"),     # Red 200 / Red 700
        "text": ("#991B1B", "#F87171"),       # Red 800 / Red 400
    },
}

# Due date badge colors
DUE_BADGE_COLORS = {
    "red": ("#FEE2E2", "#7F1D1D", "#B91C1C", "#F87171"),      # Overdue (bg_l, bg_d, text_l, text_d)
    "amber": ("#FEF3C7", "#78350F", "#B45309", "#FBBF24"),    # Due Today
    "blue": ("#DBEAFE", "#1E3A8A", "#1D4ED8", "#60A5FA"),     # Upcoming
    "gray": ("#F1F5F9", "#334155", "#64748B", "#94A3B8"),     # No Date
}

# ============================================================================
# Typography
# ============================================================================
FONT_FAMILY = "Segoe UI"
FONT_DISPLAY = "Segoe UI Variable Display"

def get_font(size: int = 14, weight: str = "normal") -> tuple:
    """Returns a standardized font tuple for CustomTkinter widgets."""
    return (FONT_FAMILY, size, weight)
