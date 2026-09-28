"""
ui/task_card.py
Interactive Task Card widget for Eisenhower Matrix and List Views.
Supports wireframe shuffle-on-hover effect:
- Normal state: Standard task card with checkbox, title, tags, and action buttons.
- Hover state (Q1): Solid emerald card displaying "Focus with Pomodoro" + 🍅 icon.
- Hover state (Q2): Solid blue card displaying "Schedule tasks using calendar" + 📅 icon.
- Clicking the hover card triggers the respective focus timer or scheduling action.
"""

from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import format_due_status
from ui import theme


class TaskCard(ctk.CTkFrame):
    """
    Component representing a single task card with wireframe hover transformations.
    """

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        on_pomodoro: Optional[Callable[[Dict[str, Any]], None]] = None,
        find_target_quadrant: Optional[Callable[[int, int], Optional[str]]] = None,
        highlight_target_quadrant: Optional[Callable[[Optional[str]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            **kwargs,
        )
        self.task = task
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_pomodoro = on_pomodoro
        self.find_target_quadrant = find_target_quadrant
        self.highlight_target_quadrant = highlight_target_quadrant

        # Hover state flag
        self.is_hovered = False
        self.is_completed = bool(self.task.get("is_completed", 0))

        # Quadrant Theme Details
        self.q_key = self.task.get("quadrant", "Q1_DO")
        self.q_info = theme.QUADRANTS.get(self.q_key, theme.QUADRANTS["Q1_DO"])
        self.q_color = self.q_info["color"]
        self.q_border = self.q_info["border"]

        self._build_normal_ui()
        self._setup_drag_and_drop()

        # Hover shuffle is exclusively for Urgent & Important (Q1) tasks
        if self.q_key == "Q1_DO":
            self._setup_hover_config()
            self._build_hover_ui()
            self._bind_hover_events()

    def _setup_hover_config(self) -> None:
        """Sets up the hover text, icons, and colors specifically for Urgent & Important (Q1)."""
        self.hover_text = "Focus with Pomodoro"
        self.hover_icon = "🍅"
        self.hover_bg = ("#D1FAE5", "#064E3B")
        self.hover_text_color = ("#065F46", "#ECFDF5")
        self.hover_action = self._on_pomodoro_click

    def _build_normal_ui(self) -> None:
        """Builds the standard task card view (visible when not hovering)."""
        self.normal_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.normal_frame.pack(fill="both", expand=True, padx=12, pady=10)

        # Top row: Checkbox + Title + Edit/Delete
        top_row = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
        top_row.pack(fill="x")

        # Checkbox
        self.check_var = ctk.BooleanVar(value=self.is_completed)
        self.cb = ctk.CTkCheckBox(
            top_row,
            text="",
            variable=self.check_var,
            width=22,
            height=22,
            corner_radius=6,
            fg_color=self.q_color,
            hover_color=self.q_info["color_dark"],
            command=lambda: self.on_toggle(self.task["id"]),
        )
        self.cb.pack(side="left", padx=(0, 8))

        # Task Title
        title_text = self.task.get("title", "Untitled Task")
        title_color = theme.TEXT_MUTED if self.is_completed else theme.TEXT_PRIMARY

        self.lbl_title = ctk.CTkLabel(
            top_row,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
            wraplength=190,
            cursor="fleur" if not self.is_completed else "arrow",
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        # Action Buttons on Right: Edit & Delete
        btn_del = ctk.CTkButton(
            top_row,
            text="✕",
            width=24,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("#FEE2E2", "#7F1D1D"),
            text_color=("#EF4444", "#F87171"),
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda: self.on_delete(self.task["id"]),
        )
        btn_del.pack(side="right", padx=(4, 0))

        btn_edit = ctk.CTkButton(
            top_row,
            text="✎",
            width=24,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, 12),
            command=lambda: self.on_edit(self.task),
        )
        btn_edit.pack(side="right", padx=(2, 0))

        # Description row (if present)
        description = self.task.get("description", "").strip()
        if description:
            lbl_desc = ctk.CTkLabel(
                self.normal_frame,
                text=description,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_MUTED if self.is_completed else theme.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=260,
            )
            lbl_desc.pack(fill="x", pady=(4, 6), padx=(30, 0))

        # Bottom row: Due Date Badge (only rendered when a valid due date is present)
        due_date_str = self.task.get("due_date")
        if due_date_str:
            due_info = format_due_status(due_date_str)
            if due_info.get("status") not in ("NO_DUE_DATE", "INVALID_DATE"):
                bottom_row = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
                bottom_row.pack(fill="x", pady=(6, 0), padx=(30, 0))

                badge_frame = ctk.CTkFrame(
                    bottom_row,
                    fg_color=self.q_info["bg_header"],
                    corner_radius=6,
                    height=20,
                    border_width=1,
                    border_color=self.q_info["border"],
                )
                badge_frame.pack(side="left")

                lbl_due = ctk.CTkLabel(
                    badge_frame,
                    text=f"📅 {due_info['label']}",
                    font=(theme.FONT_FAMILY, 10, "bold"),
                    text_color=self.q_info["text"],
                )
                lbl_due.pack(padx=6, pady=1)

    def _setup_drag_and_drop(self) -> None:
        """Binds mouse dragging to move tasks across quadrants seamlessly."""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        self._drag_ghost: Optional[ctk.CTkToplevel] = None

        # Bind drag events to card container and title
        for widget in (self, self.normal_frame, self.lbl_title):
            widget.bind("<ButtonPress-1>", self._on_drag_start, add="+")
            widget.bind("<B1-Motion>", self._on_drag_motion, add="+")
            widget.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _on_drag_start(self, event: Any) -> None:
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._is_dragging = False

    def _on_drag_motion(self, event: Any) -> None:
        dx = abs(event.x_root - self._drag_start_x)
        dy = abs(event.y_root - self._drag_start_y)

        # Start drag after passing movement threshold
        if not self._is_dragging and (dx > 6 or dy > 6):
            self._is_dragging = True
            try:
                self._drag_ghost = ctk.CTkToplevel(self)
                self._drag_ghost.overrideredirect(True)
                self._drag_ghost.attributes("-topmost", True)
                self._drag_ghost.attributes("-alpha", 0.92)
                self._drag_ghost.configure(fg_color=self.q_color)

                ghost_inner = ctk.CTkFrame(self._drag_ghost, fg_color=self.q_color, corner_radius=8)
                ghost_inner.pack(padx=8, pady=4)

                short_title = self.task.get("title", "Task")
                if len(short_title) > 22:
                    short_title = short_title[:20] + "..."

                lbl = ctk.CTkLabel(
                    ghost_inner,
                    text=f"✋ Move: {short_title}",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    text_color="#FFFFFF",
                )
                lbl.pack()
            except Exception:
                self._drag_ghost = None

        if self._is_dragging and self._drag_ghost:
            try:
                self._drag_ghost.geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
            except Exception:
                pass

            if self.find_target_quadrant and self.highlight_target_quadrant:
                target_q = self.find_target_quadrant(event.x_root, event.y_root)
                self.highlight_target_quadrant(target_q)

    def _on_drag_release(self, event: Any) -> None:
        if self._is_dragging:
            self._is_dragging = False

            if self._drag_ghost:
                try:
                    self._drag_ghost.destroy()
                except Exception:
                    pass
                self._drag_ghost = None

            if self.highlight_target_quadrant:
                self.highlight_target_quadrant(None)

            if self.find_target_quadrant and self.on_move:
                target_q = self.find_target_quadrant(event.x_root, event.y_root)
                if target_q and target_q != self.q_key:
                    self.on_move(self.task["id"], target_q)

    def _build_hover_ui(self) -> None:
        """Builds the full-card hover transformation as an overlay."""
        self.hover_frame = ctk.CTkFrame(
            self,
            fg_color=self.hover_bg,
            corner_radius=9,
            cursor="hand2",
        )

        inner_hover = ctk.CTkFrame(self.hover_frame, fg_color="transparent")
        inner_hover.pack(fill="both", expand=True, padx=14, pady=10)

        lbl_action = ctk.CTkLabel(
            inner_hover,
            text=self.hover_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=self.hover_text_color,
            anchor="w",
            cursor="hand2",
        )
        lbl_action.pack(side="left", fill="x", expand=True)

        lbl_icon = ctk.CTkLabel(
            inner_hover,
            text=self.hover_icon,
            font=(theme.FONT_FAMILY, 18),
            cursor="hand2",
        )
        lbl_icon.pack(side="right", padx=(4, 0))

        # Bind click event on hover frame and its children
        self.hover_frame.bind("<Button-1>", lambda _: self._on_hover_click())
        inner_hover.bind("<Button-1>", lambda _: self._on_hover_click())
        lbl_action.bind("<Button-1>", lambda _: self._on_hover_click())
        lbl_icon.bind("<Button-1>", lambda _: self._on_hover_click())

    def _on_pomodoro_click(self) -> None:
        if self.on_pomodoro:
            self.on_pomodoro(self.task)
        else:
            self.on_edit(self.task)

    def _on_hover_click(self) -> None:
        if self.hover_action:
            self.hover_action()

    def _bind_hover_events(self) -> None:
        """Recursively binds hover triggers for seamless, flicker-free shuffle for Q1."""
        if self.q_key != "Q1_DO":
            return
        self._bind_to_widget(self)
        if hasattr(self, "hover_frame"):
            self._bind_to_widget(self.hover_frame)

    def _bind_to_widget(self, widget: Any) -> None:
        widget.bind("<Enter>", self._on_mouse_enter, add="+")
        widget.bind("<Leave>", self._on_mouse_leave, add="+")
        for child in widget.winfo_children():
            # Exclude interactive controls that have native click handling
            if not isinstance(child, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                self._bind_to_widget(child)

    def _on_mouse_enter(self, event: Any = None) -> None:
        # Only Urgent & Important (Q1_DO) active tasks perform the hover shuffle
        if self.q_key != "Q1_DO" or self.is_completed:
            return

        if self.is_hovered or not hasattr(self, "hover_frame"):
            return
        self.is_hovered = True

        # Use place() overlay to maintain exact dimensions without shifting adjacent cards
        self.hover_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.hover_frame.lift()
        self.configure(
            border_color=self.q_color,
            border_width=2,
        )

    def _on_mouse_leave(self, event: Any = None) -> None:
        if self.q_key != "Q1_DO":
            return

        # Check if cursor is still within the bounding box of TaskCard
        try:
            x, y = self.winfo_pointerx(), self.winfo_pointery()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            rw, rh = self.winfo_width(), self.winfo_height()
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return  # Still inside card boundary
        except Exception:
            pass

        if not self.is_hovered or not hasattr(self, "hover_frame"):
            return
        self.is_hovered = False

        # Hide overlay without altering parent container dimensions
        self.hover_frame.place_forget()
        self.configure(
            border_color=theme.BORDER_COLOR,
            border_width=1,
        )
