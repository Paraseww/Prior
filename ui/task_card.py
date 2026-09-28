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

        # Hover state flag
        self.is_hovered = False
        self.is_completed = bool(self.task.get("is_completed", 0))

        # Quadrant Theme Details
        self.q_key = self.task.get("quadrant", "Q1_DO")
        self.q_info = theme.QUADRANTS.get(self.q_key, theme.QUADRANTS["Q1_DO"])
        self.q_color = self.q_info["color"]
        self.q_border = self.q_info["border"]

        self._build_normal_ui()

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

        lbl_title = ctk.CTkLabel(
            top_row,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
            wraplength=190,
        )
        lbl_title.pack(side="left", fill="x", expand=True)

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

        # Bottom row: Due Date Badge & Move Quadrant Dropdown
        bottom_row = ctk.CTkFrame(self.normal_frame, fg_color="transparent")
        bottom_row.pack(fill="x", pady=(6, 0), padx=(30, 0))

        # Due Date Badge
        due_info = format_due_status(self.task.get("due_date"))
        badge_colors = theme.DUE_BADGE_COLORS.get(due_info["color_tag"], theme.DUE_BADGE_COLORS["gray"])

        badge_frame = ctk.CTkFrame(
            bottom_row,
            fg_color=(badge_colors[0], badge_colors[1]),
            corner_radius=6,
            height=20,
        )
        badge_frame.pack(side="left")

        lbl_due = ctk.CTkLabel(
            badge_frame,
            text=f"📅 {due_info['label']}",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=(badge_colors[2], badge_colors[3]),
        )
        lbl_due.pack(padx=6, pady=1)

        # Move to Quadrant Menu
        quadrant_options = {
            "Q1_DO": "Move: Q1 Do",
            "Q2_SCHEDULE": "Move: Q2 Schedule",
            "Q3_DELEGATE": "Move: Q3 Delegate",
            "Q4_ELIMINATE": "Move: Q4 Eliminate",
        }

        # Menu options exclude current quadrant
        move_menu_options = [label for k, label in quadrant_options.items() if k != self.q_key]

        def _on_move_select(choice: str) -> None:
            for k, v in quadrant_options.items():
                if v == choice:
                    self.on_move(self.task["id"], k)
                    break

        opt_move = ctk.CTkOptionMenu(
            bottom_row,
            values=move_menu_options,
            command=_on_move_select,
            width=100,
            height=20,
            corner_radius=6,
            font=(theme.FONT_FAMILY, 10),
            fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_SECONDARY,
            button_color=theme.BG_INPUT,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_font=(theme.FONT_FAMILY, 11),
        )
        opt_move.set("Move ▾")
        opt_move.pack(side="right")

    def _build_hover_ui(self) -> None:
        """Builds the full-card hover transformation (solid colored action pill)."""
        self.hover_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            cursor="hand2",
        )

        inner_hover = ctk.CTkFrame(self.hover_frame, fg_color="transparent")
        inner_hover.pack(fill="both", expand=True, padx=12, pady=14)

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

        # Shuffle to hover action view
        self.normal_frame.pack_forget()
        self.hover_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.configure(
            fg_color=self.hover_bg,
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

        # Revert back to normal task view
        self.hover_frame.pack_forget()
        self.normal_frame.pack(fill="both", expand=True, padx=12, pady=10)
        self.configure(
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_COLOR,
            border_width=1,
        )
