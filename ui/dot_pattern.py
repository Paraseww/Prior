"""
ui/dot_pattern.py
Dynamic, high-performance dot-grid matrix texture generator for Prior.
Provides DottedFrame and DottedScrollableFrame with seamless repeating dot paper
patterns for both Creamy Soft Paper (Light Mode) and OLED True Black (Dark Mode).
"""

from typing import Optional, Tuple
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


class DotGridHelper:
    """
    Cached texture generator for dot-matrix paper backgrounds.
    """
    _cache: dict = {}

    @classmethod
    def get_pattern_image(
        cls,
        width: int,
        height: int,
        is_dark: bool,
        spacing: int = 22,
    ) -> ImageTk.PhotoImage:
        """
        Returns a cached ImageTk.PhotoImage filled with the dot-grid matrix pattern.
        Buckets dimensions by 100px increments to maximize cache hit rate during window resize.
        """
        w_bucket = max(100, ((width + 99) // 100) * 100)
        h_bucket = max(100, ((height + 99) // 100) * 100)
        key = (w_bucket, h_bucket, is_dark, spacing)

        if key in cls._cache:
            return cls._cache[key]

        if is_dark:
            bg_color = (0, 0, 0, 255)         # OLED True Black
            dot_color = (68, 68, 68, 255)     # Subtle Silver Gray dots
        else:
            bg_color = (247, 245, 240, 255)   # Creamy Soft Paper
            dot_color = (212, 206, 190, 255)  # Subtle Warm Sand dots

        img = Image.new("RGB", (w_bucket, h_bucket), bg_color)
        draw = ImageDraw.Draw(img)
        dot_r = 1

        for x in range(spacing // 2, w_bucket, spacing):
            for y in range(spacing // 2, h_bucket, spacing):
                draw.ellipse(
                    [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                    fill=dot_color,
                )

        photo = ImageTk.PhotoImage(img)
        cls._cache[key] = photo
        return photo


class DottedFrame(ctk.CTkFrame):
    """
    A CustomTkinter Frame with an active dot-grid paper background.
    Automatically responds to window resize and theme changes.
    """

    def __init__(self, master: any, spacing: int = 22, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
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
        self._bg_photo = DotGridHelper.get_pattern_image(w, h, is_dark, self.spacing)

        self._canvas.delete("bg_dot_image")
        self._canvas.create_image(
            0, 0,
            image=self._bg_photo,
            anchor="nw",
            tags="bg_dot_image",
        )
        self._canvas.tag_lower("bg_dot_image")
        self._canvas.itemconfig("inner_parts", fill="", outline="")

    def redraw_pattern(self) -> None:
        """Forces immediate recalculation and redraw of the dot matrix pattern."""
        self._on_canvas_resize()


class DottedScrollableFrame(ctk.CTkScrollableFrame):
    """
    A CustomTkinter Scrollable Frame with an active dot-grid paper background.
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
        self._bg_photo = DotGridHelper.get_pattern_image(w, h, is_dark, self.spacing)

        self._parent_canvas.delete("bg_dot_image")
        self._parent_canvas.create_image(
            0, 0,
            image=self._bg_photo,
            anchor="nw",
            tags="bg_dot_image",
        )
        self._parent_canvas.tag_lower("bg_dot_image")

    def redraw_pattern(self) -> None:
        """Forces immediate recalculation and redraw of the dot matrix pattern."""
        self._on_parent_canvas_resize()
