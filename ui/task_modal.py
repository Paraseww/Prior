"""
ui/task_modal.py
Modal dialog for creating and editing tasks with real-time Eisenhower quadrant evaluation.
"""

from datetime import date, timedelta
from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import determine_quadrant
from ui import theme


class TaskModal(ctk.CTkToplevel):
    """
    Modal window for Adding or Editing a task.
    """

    def __init__(
        self,
        master: Any,
        on_save: Callable[[Dict[str, Any]], None],
        task: Optional[Dict[str, Any]] = None,
        default_quadrant: str = "Q1_DO",
    ) -> None:
        super().__init__(master)
        self.on_save_callback = on_save
        self.task = task
        self.is_edit = task is not None
        self.current_quadrant = task.get("quadrant", default_quadrant) if task else default_quadrant

        self.title("Edit Task" if self.is_edit else "Create New Task")
        self.geometry("540x620")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Center modal relative to master window
        self._center_modal(master)

        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() - 540) // 2
            y = master.winfo_y() + (master.winfo_height() - 620) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=25)

        # Header Title
        title_text = "Edit Task" if self.is_edit else "Create New Priority Task"
        subtitle_text = "Adjust task parameters and classification" if self.is_edit else "Categorize and schedule your task on the Eisenhower Matrix"

        lbl_title = ctk.CTkLabel(
            container,
            text=title_text,
            font=(theme.FONT_DISPLAY, 20, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            container,
            text=subtitle_text,
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 20))

        # Task Title Field
        lbl_field_title = ctk.CTkLabel(
            container,
            text="Task Title *",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_field_title.pack(fill="x", pady=(0, 4))

        self.entry_title = ctk.CTkEntry(
            container,
            placeholder_text="What needs to get done?",
            font=(theme.FONT_FAMILY, 14),
            height=38,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
        )
        self.entry_title.pack(fill="x", pady=(0, 15))
        if self.task and self.task.get("title"):
            self.entry_title.insert(0, self.task["title"])

        # Description Field
        lbl_desc = ctk.CTkLabel(
            container,
            text="Description / Notes (Optional)",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_desc.pack(fill="x", pady=(0, 4))

        self.txt_desc = ctk.CTkTextbox(
            container,
            font=(theme.FONT_FAMILY, 13),
            height=70,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            border_width=1,
        )
        self.txt_desc.pack(fill="x", pady=(0, 15))
        if self.task and self.task.get("description"):
            self.txt_desc.insert("1.0", self.task["description"])

        # Urgency & Importance Switches (Live determination)
        matrix_box = ctk.CTkFrame(container, fg_color=theme.BG_INPUT, corner_radius=10, border_width=1, border_color=theme.BORDER_COLOR)
        matrix_box.pack(fill="x", pady=(0, 15), padx=0)

        inner_box = ctk.CTkFrame(matrix_box, fg_color="transparent")
        inner_box.pack(fill="x", padx=16, pady=12)

        # Pre-populate switches from current quadrant
        initial_urgent = self.current_quadrant in ("Q1_DO", "Q3_DELEGATE")
        initial_important = self.current_quadrant in ("Q1_DO", "Q2_SCHEDULE")

        self.switch_urgent = ctk.CTkSwitch(
            inner_box,
            text="🚨 Urgent (Immediate Deadline)",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            command=self._on_switch_toggle,
        )
        self.switch_urgent.pack(side="left", fill="x", expand=True)
        if initial_urgent:
            self.switch_urgent.select()

        self.switch_important = ctk.CTkSwitch(
            inner_box,
            text="⭐ Important (High Value)",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            command=self._on_switch_toggle,
        )
        self.switch_important.pack(side="right", fill="x", expand=True)
        if initial_important:
            self.switch_important.select()

        # Quadrant Preview Banner
        self.lbl_quadrant_badge = ctk.CTkLabel(
            container,
            text="",
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=28,
            corner_radius=6,
        )
        self.lbl_quadrant_badge.pack(fill="x", pady=(0, 15))
        self._update_quadrant_badge()

        # Due Date Field & Quick Presets
        lbl_due = ctk.CTkLabel(
            container,
            text="Due Date (YYYY-MM-DD)",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_due.pack(fill="x", pady=(0, 4))

        due_row = ctk.CTkFrame(container, fg_color="transparent")
        due_row.pack(fill="x", pady=(0, 20))

        self.entry_due = ctk.CTkEntry(
            due_row,
            placeholder_text="YYYY-MM-DD",
            font=(theme.FONT_FAMILY, 13),
            height=34,
            corner_radius=6,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            width=150,
        )
        self.entry_due.pack(side="left", padx=(0, 10))
        if self.task and self.task.get("due_date"):
            self.entry_due.insert(0, self.task["due_date"])

        # Presets: Today, Tomorrow, +1 Wk, Clear
        btn_today = ctk.CTkButton(due_row, text="Today", width=60, height=34, corner_radius=6, fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_CARD_HOVER, command=lambda: self._set_due_preset(0))
        btn_today.pack(side="left", padx=2)

        btn_tmr = ctk.CTkButton(due_row, text="Tmrw", width=60, height=34, corner_radius=6, fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_CARD_HOVER, command=lambda: self._set_due_preset(1))
        btn_tmr.pack(side="left", padx=2)

        btn_week = ctk.CTkButton(due_row, text="+7 Days", width=65, height=34, corner_radius=6, fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_CARD_HOVER, command=lambda: self._set_due_preset(7))
        btn_week.pack(side="left", padx=2)

        btn_clear = ctk.CTkButton(due_row, text="Clear", width=55, height=34, corner_radius=6, fg_color=theme.BG_INPUT, text_color=theme.TEXT_SECONDARY, hover_color=theme.BG_CARD_HOVER, command=lambda: self._set_due_preset(None))
        btn_clear.pack(side="left", padx=2)

        # Action Buttons: Cancel / Save
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=(theme.FONT_FAMILY, 14),
            height=40,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_CARD_HOVER,
            command=self.destroy,
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_save = ctk.CTkButton(
            btn_row,
            text="Save Task" if self.is_edit else "Add to Board",
            font=(theme.FONT_FAMILY, 14, "bold"),
            height=40,
            corner_radius=8,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._on_save_clicked,
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _on_switch_toggle(self) -> None:
        urgent = bool(self.switch_urgent.get())
        important = bool(self.switch_important.get())
        self.current_quadrant = determine_quadrant(urgent, important)
        self._update_quadrant_badge()

    def _update_quadrant_badge(self) -> None:
        info = theme.QUADRANTS.get(self.current_quadrant, theme.QUADRANTS["Q1_DO"])
        self.lbl_quadrant_badge.configure(
            text=f"Classified into: {info['title'].upper()} ({info['badge']})",
            fg_color=info["color"],
            text_color="#FFFFFF",
        )

    def _set_due_preset(self, days_offset: Optional[int]) -> None:
        self.entry_due.delete(0, "end")
        if days_offset is not None:
            target_date = date.today() + timedelta(days=days_offset)
            self.entry_due.insert(0, target_date.strftime("%Y-%m-%d"))

    def _on_save_clicked(self) -> None:
        title = self.entry_title.get().strip()
        if not title:
            self.entry_title.configure(border_color="#EF4444")
            return

        description = self.txt_desc.get("1.0", "end-1c").strip()
        due_date = self.entry_due.get().strip() or None

        data = {
            "title": title,
            "description": description,
            "quadrant": self.current_quadrant,
            "due_date": due_date,
        }

        self.on_save_callback(data)
        self.destroy()
