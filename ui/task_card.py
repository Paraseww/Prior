"""
ui/task_card.py
Interactive Task Card widget for Eisenhower Matrix and List Views.
Features completion toggle, color-coded due date badges, edit, move, and delete actions.
"""

from typing import Any, Callable, Dict
import customtkinter as ctk

from project import format_due_status
from ui import theme


class TaskCard(ctk.CTkFrame):
    """
    Component representing a single task card.
    """

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
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

        self._build_ui()

    def _build_ui(self) -> None:
        is_completed = bool(self.task.get("is_completed", 0))

        # Main inner container
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Top row: Checkbox + Title + Move/Edit/Delete actions
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        # Checkbox
        self.check_var = ctk.BooleanVar(value=is_completed)
        self.cb = ctk.CTkCheckBox(
            top_row,
            text="",
            variable=self.check_var,
            width=22,
            height=22,
            corner_radius=6,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            command=lambda: self.on_toggle(self.task["id"]),
        )
        self.cb.pack(side="left", padx=(0, 8))

        # Task Title
        title_text = self.task.get("title", "Untitled Task")
        title_color = theme.TEXT_MUTED if is_completed else theme.TEXT_PRIMARY

        lbl_title = ctk.CTkLabel(
            top_row,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
            wraplength=200,
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
                inner,
                text=description,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_MUTED if is_completed else theme.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=260,
            )
            lbl_desc.pack(fill="x", pady=(4, 6), padx=(30, 0))

        # Bottom row: Due Date Badge & Move Quadrant Dropdown
        bottom_row = ctk.CTkFrame(inner, fg_color="transparent")
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
        current_q = self.task.get("quadrant", "Q1_DO")
        quadrant_options = {
            "Q1_DO": "Move: Q1 Do",
            "Q2_SCHEDULE": "Move: Q2 Schedule",
            "Q3_DELEGATE": "Move: Q3 Delegate",
            "Q4_ELIMINATE": "Move: Q4 Eliminate",
        }

        # Menu options exclude current quadrant
        move_menu_options = [label for q_key, label in quadrant_options.items() if q_key != current_q]

        def _on_move_select(choice: str) -> None:
            # Map choice back to key
            for k, v in quadrant_options.items():
                if v == choice:
                    self.on_move(self.task["id"], k)
                    break

        opt_move = ctk.CTkOptionMenu(
            bottom_row,
            values=move_menu_options,
            command=_on_move_select,
            width=110,
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
