"""
ui/scrollable_dropdown.py
Custom scrollable dropdown widget for CustomTkinter with smooth scrolling,
keyboard dismiss, and auto-scroll to selected value.
"""

from typing import Any, Callable, List, Optional
import customtkinter as ctk
from ui import theme


class ScrollableOptionMenu(ctk.CTkFrame):
    """
    A CustomTkinter OptionMenu replacement featuring a scrollable dropdown menu
    with a scrollbar for lists with many items (e.g., 00-59 minutes).
    """

    def __init__(
        self,
        master: Any,
        values: List[str],
        width: int = 68,
        height: int = 28,
        corner_radius: int = 6,
        fg_color: Any = None,
        button_color: Any = None,
        button_hover_color: Any = None,
        text_color: Any = None,
        dropdown_height: int = 180,
        dropdown_width: Optional[int] = None,
        command: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=corner_radius,
            fg_color="transparent",
            **kwargs,
        )
        self.values = [str(v) for v in values]
        self._current_value = self.values[0] if self.values else ""
        self._command = command
        self._dropdown_height = dropdown_height
        self._dropdown_width = dropdown_width or width
        self._popup: Optional[ctk.CTkToplevel] = None
        self._dismiss_bind_id: Optional[str] = None

        # Colors
        self._btn_fg = fg_color or theme.BG_CARD
        self._btn_hover = button_hover_color or theme.BG_CARD_HOVER
        self._text_color = text_color or theme.TEXT_PRIMARY

        # Main Button
        self.btn = ctk.CTkButton(
            self,
            text=f"{self._current_value}  ▾",
            font=(theme.FONT_FAMILY, 11, "bold"),
            width=width,
            height=height,
            corner_radius=corner_radius,
            fg_color=self._btn_fg,
            hover_color=self._btn_hover,
            text_color=self._text_color,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            command=self._toggle_popup,
        )
        self.btn.pack(fill="both", expand=True)

    def get(self) -> str:
        """Returns the currently selected value."""
        return self._current_value

    def set(self, value: str) -> None:
        """Sets the selected value and updates button text."""
        val_str = str(value)
        self._current_value = val_str
        self.btn.configure(text=f"{val_str}  ▾")

    def configure_values(self, values: List[str]) -> None:
        """Updates the list of selectable values."""
        self.values = [str(v) for v in values]
        if self._current_value not in self.values and self.values:
            self.set(self.values[0])

    def _toggle_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self) -> None:
        self._close_popup()

        # Create TopLevel popup
        self._popup = ctk.CTkToplevel(self)
        self._popup.withdraw()
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)

        # Position below the button
        self.update_idletasks()
        btn_x = self.btn.winfo_rootx()
        btn_y = self.btn.winfo_rooty()
        btn_h = self.btn.winfo_height()
        btn_w = self.btn.winfo_width()

        pop_w = max(self._dropdown_width, btn_w)
        pop_h = min(self._dropdown_height, max(40, len(self.values) * 30 + 14))

        # Screen boundaries check
        screen_h = self.winfo_screenheight()
        if btn_y + btn_h + pop_h > screen_h - 40:
            pop_y = max(10, btn_y - pop_h - 2)
        else:
            pop_y = btn_y + btn_h + 2
        pop_x = btn_x

        self._popup.geometry(f"{pop_w}x{pop_h}+{pop_x}+{pop_y}")

        # Container Frame
        border_frame = ctk.CTkFrame(
            self._popup,
            fg_color=theme.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        border_frame.pack(fill="both", expand=True)

        scroll = ctk.CTkScrollableFrame(
            border_frame,
            fg_color="transparent",
            corner_radius=6,
            scrollbar_button_color=theme.BG_CARD_HOVER,
            scrollbar_button_hover_color=theme.ACCENT_PRIMARY,
        )
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        selected_idx = 0

        for idx, val in enumerate(self.values):
            is_selected = (val == self._current_value)
            if is_selected:
                selected_idx = idx

            btn_item = ctk.CTkButton(
                scroll,
                text=val,
                font=(theme.FONT_FAMILY, 11, "bold" if is_selected else "normal"),
                height=26,
                corner_radius=4,
                fg_color=theme.ACCENT_PRIMARY if is_selected else "transparent",
                hover_color=theme.ACCENT_HOVER if is_selected else theme.BG_CARD_HOVER,
                text_color="#FFFFFF" if is_selected else theme.TEXT_PRIMARY,
                command=lambda v=val: self._on_item_click(v),
            )
            btn_item.pack(fill="x", pady=1, padx=2)

        self._popup.deiconify()

        # Auto-scroll to selected item
        if self.values:
            fraction = max(0.0, min(1.0, selected_idx / len(self.values)))
            self._popup.after(30, lambda: self._scroll_to_fraction(scroll, fraction))

        # Close on click outside or escape
        top_window = self.winfo_toplevel()
        self._dismiss_bind_id = top_window.bind("<ButtonPress-1>", self._on_global_click, add="+")
        self._popup.bind("<Escape>", lambda e: self._close_popup())
        self._popup.focus_set()

    def _scroll_to_fraction(self, scroll: ctk.CTkScrollableFrame, fraction: float) -> None:
        try:
            if hasattr(scroll, "_parent_canvas"):
                scroll._parent_canvas.yview_moveto(fraction)
        except Exception:
            pass

    def _on_global_click(self, event: Any = None) -> None:
        if not self._popup or not self._popup.winfo_exists():
            return
        try:
            x, y = event.x_root, event.y_root
            pop_x = self._popup.winfo_rootx()
            pop_y = self._popup.winfo_rooty()
            pop_w = self._popup.winfo_width()
            pop_h = self._popup.winfo_height()

            btn_x = self.btn.winfo_rootx()
            btn_y = self.btn.winfo_rooty()
            btn_w = self.btn.winfo_width()
            btn_h = self.btn.winfo_height()

            # Ignore clicks inside popup or on the trigger button itself
            in_popup = (pop_x <= x <= pop_x + pop_w and pop_y <= y <= pop_y + pop_h)
            in_btn = (btn_x <= x <= btn_x + btn_w and btn_y <= y <= btn_y + btn_h)

            if not in_popup and not in_btn:
                self._close_popup()
        except Exception:
            self._close_popup()

    def _on_item_click(self, value: str) -> None:
        self.set(value)
        self._close_popup()
        if self._command:
            self._command(value)

    def _close_popup(self) -> None:
        if self._popup:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except Exception:
                pass
            self._popup = None
        if self._dismiss_bind_id:
            try:
                top_window = self.winfo_toplevel()
                top_window.unbind("<ButtonPress-1>", self._dismiss_bind_id)
            except Exception:
                pass
            self._dismiss_bind_id = None
