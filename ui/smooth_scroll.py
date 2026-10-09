"""
ui/smooth_scroll.py
High-performance, buttery-smooth scrollable frame for Prior.
Eliminates text overlapping / ghosting artifacts during mousewheel scrolling
by decoupling wheel input from rendering using 60fps LERP physics animation
and synchronous dirty-region redraw flushing.
"""

import sys
from typing import Any, Optional
import customtkinter as ctk


class SmoothScrollableFrame(ctk.CTkScrollableFrame):
    """
    A drop-in replacement for CTkScrollableFrame featuring:
    1. Smooth physics-based LERP animated scrolling (top-to-bottom and bottom-to-top).
    2. Zero text ghosting / overlapping: flushes drawing queues per frame.
    3. Multi-pane cursor awareness: only scrolls the container currently under the cursor.
    4. Scrollbar drag synchronization: keeps target and current position unified.
    """

    def __init__(
        self,
        master: Any,
        step_size: int = 65,
        anim_factor: float = 0.28,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.step_size = step_size
        self.anim_factor = anim_factor

        self._target_pixel_y: float = 0.0
        self._current_pixel_y: float = 0.0
        self._scroll_anim_id: Optional[str] = None

        # Hook scrollbar command to keep position in sync when dragging slider
        self._hook_scrollbar_command()

    def _hook_scrollbar_command(self) -> None:
        """Hooks vertical scrollbar slider dragging to stay in sync with smooth scroll."""
        if hasattr(self, "_scrollbar") and self._scrollbar:
            orig_yview = self._parent_canvas.yview

            def _scrollbar_drag_cmd(*args) -> Any:
                self._cancel_scroll_anim()
                res = orig_yview(*args)
                self._sync_scroll_target()
                try:
                    self._parent_canvas.update_idletasks()
                except Exception:
                    pass
                return res

            self._scrollbar.configure(command=_scrollbar_drag_cmd)

    def _cancel_scroll_anim(self) -> None:
        """Cancels any ongoing smooth scrolling animation frame."""
        if self._scroll_anim_id:
            try:
                self.after_cancel(self._scroll_anim_id)
            except Exception:
                pass
            self._scroll_anim_id = None

    def _sync_scroll_target(self) -> None:
        """Synchronizes internal pixel positions with canvas current view."""
        try:
            bbox = self._parent_canvas.bbox("all")
            if not bbox:
                return
            total_h = max(1, bbox[3] - bbox[1])
            yview = self._parent_canvas.yview()
            self._current_pixel_y = yview[0] * total_h
            self._target_pixel_y = self._current_pixel_y
        except Exception:
            pass

    def _is_pointer_over_frame(self) -> bool:
        """Checks if the mouse cursor is physically over this scrollable container."""
        try:
            if not self._parent_canvas.winfo_exists():
                return False
            x, y = self._parent_canvas.winfo_pointerx(), self._parent_canvas.winfo_pointery()
            rx, ry = self._parent_canvas.winfo_rootx(), self._parent_canvas.winfo_rooty()
            rw, rh = self._parent_canvas.winfo_width(), self._parent_canvas.winfo_height()
            return (rx <= x < rx + rw) and (ry <= y < ry + rh)
        except Exception:
            return False

    def _mouse_wheel_all(self, event: Any) -> None:
        """
        Intercepts global mousewheel events and applies smooth LERP animation
        exclusively when this frame is the active target.
        """
        # Only process if cursor is physically over this scrollable frame
        if not self._is_pointer_over_frame():
            return

        if not self._check_if_valid_scroll(event.widget) and not self._is_pointer_over_frame():
            return

        if self._orientation == "vertical":
            delta = 0
            if sys.platform.startswith("win"):
                delta = getattr(event, "delta", 0)
            elif sys.platform == "darwin":
                delta = getattr(event, "delta", 0) * 12
            else:
                # Linux Button-4 (up) and Button-5 (down)
                if getattr(event, "num", None) == 4:
                    delta = 120
                elif getattr(event, "num", None) == 5:
                    delta = -120

            if delta == 0:
                return

            bbox = self._parent_canvas.bbox("all")
            if not bbox:
                return
            total_h = max(1, bbox[3] - bbox[1])
            visible_h = self._parent_canvas.winfo_height()
            max_y = max(0, total_h - visible_h)
            if max_y <= 0:
                return

            # If user dragged scrollbar or scrolled externally, sync current position
            cur_from_yview = self._parent_canvas.yview()[0] * total_h
            if abs(cur_from_yview - self._current_pixel_y) > 2.0 and not self._scroll_anim_id:
                self._current_pixel_y = cur_from_yview
                self._target_pixel_y = cur_from_yview

            # delta > 0 is scroll UP (decrease y), delta < 0 is scroll DOWN (increase y)
            delta_px = -(delta / 120.0) * self.step_size
            self._target_pixel_y = max(0.0, min(float(max_y), self._target_pixel_y + delta_px))

            if not self._scroll_anim_id:
                self._run_scroll_anim()

        elif self._orientation == "horizontal":
            super()._mouse_wheel_all(event)

    def _run_scroll_anim(self) -> None:
        """Performs one frame of LERP animated scrolling at ~60fps."""
        if not self._parent_canvas.winfo_exists():
            self._scroll_anim_id = None
            return

        bbox = self._parent_canvas.bbox("all")
        if not bbox:
            self._scroll_anim_id = None
            return

        total_h = max(1, bbox[3] - bbox[1])
        visible_h = self._parent_canvas.winfo_height()
        max_y = max(0, total_h - visible_h)

        # Clamp target in case total content height changed during scrolling
        self._target_pixel_y = max(0.0, min(float(max_y), self._target_pixel_y))

        diff = self._target_pixel_y - self._current_pixel_y

        # If sufficiently close to target, snap to target and finish animation
        if abs(diff) < 0.6:
            self._current_pixel_y = self._target_pixel_y
            if total_h > 0:
                self._parent_canvas.yview_moveto(self._current_pixel_y / total_h)
            try:
                self._parent_canvas.update_idletasks()
            except Exception:
                pass
            self._scroll_anim_id = None
            return

        # LERP step with minimum velocity to avoid sluggish tail
        step = diff * self.anim_factor
        if abs(step) < 1.0:
            step = 1.0 if diff > 0 else -1.0

        self._current_pixel_y += step
        if total_h > 0:
            self._parent_canvas.yview_moveto(self._current_pixel_y / total_h)

        # Flush dirty window drawing pipeline immediately to eliminate overlapping text
        try:
            self._parent_canvas.update_idletasks()
        except Exception:
            pass

        # Schedule next animation frame (~60 FPS = 16ms)
        self._scroll_anim_id = self.after(16, self._run_scroll_anim)

    def scroll_to_top(self, smooth: bool = True) -> None:
        """Scrolls the container to the very top."""
        if smooth:
            self._target_pixel_y = 0.0
            if not self._scroll_anim_id:
                self._run_scroll_anim()
        else:
            self._cancel_scroll_anim()
            self._current_pixel_y = 0.0
            self._target_pixel_y = 0.0
            self._parent_canvas.yview_moveto(0.0)
            try:
                self._parent_canvas.update_idletasks()
            except Exception:
                pass

    def scroll_to_bottom(self, smooth: bool = True) -> None:
        """Scrolls the container to the very bottom."""
        bbox = self._parent_canvas.bbox("all") or (0, 0, 1, 1)
        total_h = max(1, bbox[3] - bbox[1])
        visible_h = self._parent_canvas.winfo_height()
        max_y = max(0.0, float(total_h - visible_h))

        if smooth:
            self._target_pixel_y = max_y
            if not self._scroll_anim_id:
                self._run_scroll_anim()
        else:
            self._cancel_scroll_anim()
            self._current_pixel_y = max_y
            self._target_pixel_y = max_y
            if total_h > 0:
                self._parent_canvas.yview_moveto(max_y / total_h)
            try:
                self._parent_canvas.update_idletasks()
            except Exception:
                pass
