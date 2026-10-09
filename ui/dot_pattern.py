"""
ui/dot_pattern.py
Dynamic, high-performance dot-grid matrix texture generator for Prior.
Provides DottedCardFrame and DottedScrollableFrame with seamless repeating dot paper
patterns for quadrant cards and task panes in both Creamy Soft Paper (Light Mode)
and OLED True Black (Dark Mode), with perfect rounded-corner antialiasing.
"""

from typing import Optional
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


class DotGridHelper:
    """
    Cached texture generator for dot-matrix paper backgrounds on card surfaces.
    """
    _cache: dict = {}

    @classmethod
    def get_pattern_image(
        cls,
        width: int,
        height: int,
        corner_radius: int,
        is_dark: bool,
        spacing: int = 22,
    ) -> ImageTk.PhotoImage:
        """
        Returns a cached ImageTk.PhotoImage with rounded corner transparency and dot grid.
        """
        key = (width, height, corner_radius, is_dark, spacing)
        if key in cls._cache:
            return cls._cache[key]

        if is_dark:
            card_bg = (18, 18, 18, 255)       # Card background in Dark Mode (#121212)
            dot_color = (68, 68, 68, 255)     # Subtle Silver Gray dots (#444444)
        else:
            card_bg = (253, 251, 247, 255)   # Creamy Card background in Light Mode (#FDFBF7)
            dot_color = (214, 208, 194, 255)  # Subtle Warm Sand dots (#D6D0C2)

        # Transparent RGBA canvas so corners outside the card radius are 100% transparent
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw rounded card background
        if corner_radius > 0:
            draw.rounded_rectangle(
                [0, 0, width - 1, height - 1],
                radius=corner_radius,
                fill=card_bg,
            )
        else:
            draw.rectangle([0, 0, width - 1, height - 1], fill=card_bg)

        # Draw subtle grid dots
        dot_r = 1
        for x in range(spacing // 2, width, spacing):
            for y in range(spacing // 2, height, spacing):
                if corner_radius > 0:
                    if (x < corner_radius and y < corner_radius) or \
                       (x > width - corner_radius and y < corner_radius) or \
                       (x < corner_radius and y > height - corner_radius) or \
                       (x > width - corner_radius and y > height - corner_radius):
                        continue
                draw.ellipse(
                    [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                    fill=dot_color,
                )

        photo = ImageTk.PhotoImage(img)
        cls._cache[key] = photo
        return photo


class DottedCardFrame(ctk.CTkFrame):
    """
    A CustomTkinter Frame with an active dot-grid paper background on card surfaces.
    Preserves rounded border outlines cleanly.
    """

    def __init__(self, master: any, spacing: int = 22, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.spacing = spacing
        self._bg_photo: Optional[ImageTk.PhotoImage] = None

        if hasattr(self, "_canvas") and self._canvas:
            self._canvas.bind("<Configure>", self._on_canvas_resize, add="+")

    def _on_canvas_resize(self, event=None) -> None:
        if not self._canvas.winfo_exists():
            return
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        is_dark = (ctk.get_appearance_mode() == "Dark")
        cr = int(self._apply_widget_scaling(self._corner_radius)) if hasattr(self, "_corner_radius") else 0
        scaled_spacing = max(12, int(round(self._apply_widget_scaling(self.spacing))))
        self._bg_photo = DotGridHelper.get_pattern_image(w, h, cr, is_dark, scaled_spacing)

        self._canvas.delete("bg_dot_image")
        self._canvas.create_image(
            0, 0,
            image=self._bg_photo,
            anchor="nw",
            tags="bg_dot_image",
        )
        self._canvas.tag_lower("bg_dot_image")
        self._canvas.itemconfig("inner_parts", fill="", outline="")

    def _draw(self, no_color_updates: bool = False) -> None:
        super()._draw(no_color_updates)
        if hasattr(self, "_canvas") and self._canvas.winfo_exists():
            self._canvas.itemconfig("inner_parts", fill="", outline="")
            self._canvas.tag_lower("bg_dot_image")

    def _set_scaling(self, new_widget_scaling: float, new_window_scaling: float) -> None:
        super()._set_scaling(new_widget_scaling, new_window_scaling)
        if hasattr(self, "_canvas") and self._canvas.winfo_exists():
            self._canvas.itemconfig("inner_parts", fill="", outline="")
            self._canvas.tag_lower("bg_dot_image")
        self.after_idle(self.redraw_pattern)

    def redraw_pattern(self) -> None:
        """Forces immediate recalculation and redraw of the dot matrix pattern."""
        self._on_canvas_resize()

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "_canvas") and self._canvas.winfo_exists():
            self._canvas.itemconfig("inner_parts", fill="", outline="")
            self._canvas.tag_lower("bg_dot_image")
        self.redraw_pattern()


DottedFrame = DottedCardFrame


from ui.smooth_scroll import SmoothScrollableFrame


class DottedScrollableFrame(SmoothScrollableFrame):
    """
    A CustomTkinter Scrollable Frame with smooth scrolling and dot-grid background.
    """

    def __init__(self, master: any, spacing: int = 22, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.spacing = spacing
        self._bg_photo: Optional[ImageTk.PhotoImage] = None

        if hasattr(self, "_parent_canvas") and self._parent_canvas:
            self._parent_canvas.bind("<Configure>", self._on_parent_canvas_resize, add="+")

    def _on_parent_canvas_resize(self, event=None) -> None:
        if not self._parent_canvas.winfo_exists():
            return
        w = self._parent_canvas.winfo_width()
        h = self._parent_canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        is_dark = (ctk.get_appearance_mode() == "Dark")
        cr = int(self._apply_widget_scaling(self._corner_radius)) if hasattr(self, "_corner_radius") else 0
        scaled_spacing = max(12, int(round(self._apply_widget_scaling(self.spacing))))
        self._bg_photo = DotGridHelper.get_pattern_image(w, h, cr, is_dark, scaled_spacing)

        self._parent_canvas.delete("bg_dot_image")
        self._parent_canvas.create_image(
            0, 0,
            image=self._bg_photo,
            anchor="nw",
            tags="bg_dot_image",
        )
        self._parent_canvas.tag_lower("bg_dot_image")

    def _set_scaling(self, new_widget_scaling: float, new_window_scaling: float) -> None:
        super()._set_scaling(new_widget_scaling, new_window_scaling)
        self.after_idle(self.redraw_pattern)

    def redraw_pattern(self) -> None:
        """Forces immediate recalculation and redraw of the dot matrix pattern."""
        self._on_parent_canvas_resize()

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        self.redraw_pattern()
