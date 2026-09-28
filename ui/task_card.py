"""
ui/task_card.py
Interactive Task Card widget for Eisenhower Matrix and List Views.
Features completion toggle, color-coded due date badges, edit, move, and delete actions.
"""

from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import format_due_status
from ui import theme


class TaskCard(ctk.CTkFrame):
    """
    Component representing a single task card.
    Supports hover state transitions and quadrant-specific quick actions
    such as 'Focus with Pomodoro' for Urgent & Important tasks.
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

        # Determine Quadrant Theme Color
        q_key = self.task.get("quadrant", "Q1_DO")
        self.q_info = theme.QUADRANTS.get(q_key, theme.QUADRANTS["Q1_DO"])
        self.q_color = self.q_info["color"]
        self.q_border = self.q_info["border"]

        self._build_ui()
        self._setup_hover_effects()

    def _build_ui(self) -> None:
        is_completed = bool(self.task.get("is_completed", 0))
        q_key = self.task.get("quadrant", "Q1_DO")

        # Main inner container
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Top row: Checkbox + Title + Move/Edit/Delete actions
        self.top_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        self.top_row.pack(fill="x")

        # Checkbox
        self.check_var = ctk.BooleanVar(value=is_completed)
        self.cb = ctk.CTkCheckBox(
            self.top_row,
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
        title_color = theme.TEXT_MUTED if is_completed else theme.TEXT_PRIMARY

        self.lbl_title = ctk.CTkLabel(
            self.top_row,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
            wraplength=190,
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        # Action Buttons on Right: Edit & Delete
        self.btn_del = ctk.CTkButton(
            self.top_row,
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
        self.btn_del.pack(side="right", padx=(4, 0))

        self.btn_edit = ctk.CTkButton(
            self.top_row,
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
        self.btn_edit.pack(side="right", padx=(2, 0))

        # Description row (if present)
        description = self.task.get("description", "").strip()
        if description:
            self.lbl_desc = ctk.CTkLabel(
                self.inner,
                text=description,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_MUTED if is_completed else theme.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=260,
            )
            self.lbl_desc.pack(fill="x", pady=(4, 6), padx=(30, 0))

        # Quadrant-Specific Focus / Action Banner (Wireframe interaction)
        if not is_completed:
            if q_key == "Q1_DO":
                self.action_default_bg = ("#ECFDF5", "#064E3B")
                self.action_default_text = ("#065F46", "#34D399")
                self.btn_action = ctk.CTkButton(
                    self.inner,
                    text="🍅 Focus with Pomodoro",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    height=26,
                    corner_radius=6,
                    fg_color=self.action_default_bg,
                    hover_color=self.q_color,
                    text_color=self.action_default_text,
                    border_width=1,
                    border_color=self.q_border,
                    command=self._on_action_click,
                )
                self.btn_action.pack(fill="x", pady=(6, 2), padx=(30, 0))
            elif q_key == "Q2_SCHEDULE":
                self.action_default_bg = ("#EFF6FF", "#1E3A8A")
                self.action_default_text = ("#1E40AF", "#60A5FA")
                self.btn_action = ctk.CTkButton(
                    self.inner,
                    text="📅 Schedule Due Date",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    height=26,
                    corner_radius=6,
                    fg_color=self.action_default_bg,
                    hover_color=self.q_color,
                    text_color=self.action_default_text,
                    border_width=1,
                    border_color=self.q_border,
                    command=lambda: self.on_edit(self.task),
                )
                self.btn_action.pack(fill="x", pady=(6, 2), padx=(30, 0))
            else:
                self.btn_action = None
        else:
            self.btn_action = None

        # Bottom row: Due Date Badge & Move Quadrant Dropdown
        self.bottom_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        self.bottom_row.pack(fill="x", pady=(6, 0), padx=(30, 0))

        # Due Date Badge
        due_info = format_due_status(self.task.get("due_date"))
        badge_colors = theme.DUE_BADGE_COLORS.get(due_info["color_tag"], theme.DUE_BADGE_COLORS["gray"])

        self.badge_frame = ctk.CTkFrame(
            self.bottom_row,
            fg_color=(badge_colors[0], badge_colors[1]),
            corner_radius=6,
            height=20,
        )
        self.badge_frame.pack(side="left")

        self.lbl_due = ctk.CTkLabel(
            self.badge_frame,
            text=f"📅 {due_info['label']}",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=(badge_colors[2], badge_colors[3]),
        )
        self.lbl_due.pack(padx=6, pady=1)

        # Move to Quadrant Menu
        quadrant_options = {
            "Q1_DO": "Move: Q1 Do",
            "Q2_SCHEDULE": "Move: Q2 Schedule",
            "Q3_DELEGATE": "Move: Q3 Delegate",
            "Q4_ELIMINATE": "Move: Q4 Eliminate",
        }

        # Menu options exclude current quadrant
        move_menu_options = [label for k, label in quadrant_options.items() if k != q_key]

        def _on_move_select(choice: str) -> None:
            for k, v in quadrant_options.items():
                if v == choice:
                    self.on_move(self.task["id"], k)
                    break

        self.opt_move = ctk.CTkOptionMenu(
            self.bottom_row,
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
        self.opt_move.set("Move ▾")
        self.opt_move.pack(side="right")

    def _on_action_click(self) -> None:
        if self.on_pomodoro:
            self.on_pomodoro(self.task)
        else:
            self.on_edit(self.task)

    def _setup_hover_effects(self) -> None:
        """Binds mouse hover events to create an interactive wireframe highlight."""
        self._bind_hover_recursive(self)

    def _bind_hover_recursive(self, widget: Any) -> None:
        widget.bind("<Enter>", self._on_mouse_enter, add="+")
        widget.bind("<Leave>", self._on_mouse_leave, add="+")
        for child in widget.winfo_children():
            # Skip interactive controls that have their own event handling
            if not isinstance(child, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                self._bind_hover_recursive(child)

    def _on_mouse_enter(self, event: Any = None) -> None:
        self.configure(border_color=self.q_border, border_width=2)
        if hasattr(self, "btn_action") and self.btn_action:
            self.btn_action.configure(fg_color=self.q_color, text_color="#FFFFFF")

    def _on_mouse_leave(self, event: Any = None) -> None:
        # Prevent jitter when cursor moves across child widgets inside the card
        try:
            x, y = self.winfo_pointerx(), self.winfo_pointery()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            rw, rh = self.winfo_width(), self.winfo_height()
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return
        except Exception:
            pass

        self.configure(border_color=theme.BORDER_COLOR, border_width=1)
        if hasattr(self, "btn_action") and self.btn_action:
            self.btn_action.configure(
                fg_color=self.action_default_bg,
                text_color=self.action_default_text,
            )
