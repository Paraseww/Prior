"""
ui/list_view.py
Chronological and filterable List View for Prior tasks.
"""

from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from project import filter_tasks
from ui import theme
from ui.dot_pattern import DottedScrollableFrame
from ui.scrollable_dropdown import ScrollableOptionMenu
from ui.task_card import TaskCard


class ListView(ctk.CTkFrame):
    """
    List View displaying all tasks in a single scrollable container with dot-matrix canvas.
    """

    def __init__(
        self,
        master: Any,
        tasks: List[Dict[str, Any]],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        on_clear_completed: Callable[[], None],
        on_pomodoro: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_schedule: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.all_tasks = tasks
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_clear_completed = on_clear_completed
        self.on_pomodoro = on_pomodoro
        self.on_schedule = on_schedule

        self.filter_quadrant = "ALL"
        self.filter_status = "ALL"

        self._build_ui()

    def _build_ui(self) -> None:
        # Top Control Bar (Filter Dropdowns & Clear Completed)
        control_bar = ctk.CTkFrame(self, fg_color=theme.BG_CARD, corner_radius=10, height=52)
        control_bar.pack(fill="x", padx=10, pady=(10, 8))
        control_bar.pack_propagate(False)

        inner_controls = ctk.CTkFrame(control_bar, fg_color="transparent")
        inner_controls.pack(fill="both", expand=True, padx=12, pady=8)

        # Quadrant Filter
        lbl_q = ctk.CTkLabel(inner_controls, text="Quadrant:", font=(theme.FONT_FAMILY, 12, "bold"), text_color=theme.TEXT_PRIMARY)
        lbl_q.pack(side="left", padx=(0, 6))

        self.opt_quadrant = ScrollableOptionMenu(
            inner_controls,
            values=["All Quadrants", "Q1: Do First", "Q2: Schedule", "Q3: Delegate", "Q4: Eliminate"],
            width=145,
            height=30,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_width=160,
            dropdown_height=175,
            command=self._on_filter_changed,
        )
        self.opt_quadrant.pack(side="left", padx=(0, 15))

        # Status Filter
        lbl_s = ctk.CTkLabel(inner_controls, text="Status:", font=(theme.FONT_FAMILY, 12, "bold"), text_color=theme.TEXT_PRIMARY)
        lbl_s.pack(side="left", padx=(0, 6))

        self.opt_status = ScrollableOptionMenu(
            inner_controls,
            values=["All Tasks", "Active Only", "Completed Only"],
            width=135,
            height=30,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_width=145,
            dropdown_height=125,
            command=self._on_filter_changed,
        )
        self.opt_status.pack(side="left", padx=(0, 15))

        # Hide Completed Button
        btn_clear = ctk.CTkButton(
            inner_controls,
            text="Hide Completed",
            font=(theme.FONT_FAMILY, 11, "bold"),
            height=30,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            hover_color=("#FEE2E2", "#2A0A0A"),
            text_color=("#EF4444", "#F87171"),
            border_width=1,
            border_color=theme.BORDER_COLOR,
            command=self.on_clear_completed,
        )
        btn_clear.pack(side="right")

        # Scrollable Task Container with dot-grid canvas
        self.scroll_frame = DottedScrollableFrame(
            self,
            corner_radius=10,
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._render_tasks()

    def _on_filter_changed(self, _: str) -> None:
        q_val = self.opt_quadrant.get()
        mapping = {
            "All Quadrants": "ALL",
            "Q1: Do First": "Q1_DO",
            "Q2: Schedule": "Q2_SCHEDULE",
            "Q3: Delegate": "Q3_DELEGATE",
            "Q4: Eliminate": "Q4_ELIMINATE",
        }
        self.filter_quadrant = mapping.get(q_val, "ALL")

        s_val = self.opt_status.get()
        self.filter_status = s_val

        self._render_tasks()

    def _render_tasks(self) -> None:
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        # Apply filtering
        show_completed = self.filter_status != "Active Only"
        filtered = filter_tasks(
            self.all_tasks,
            quadrant_filter=self.filter_quadrant,
            show_completed=show_completed,
        )

        if self.filter_status == "Completed Only":
            filtered = [t for t in filtered if bool(t.get("is_completed", 0))]

        if not filtered:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="No matching tasks found.",
                font=(theme.FONT_FAMILY, 13),
                text_color=theme.TEXT_MUTED,
            )
            empty_lbl.pack(pady=50)
            return

        for task in filtered:
            card = TaskCard(
                self.scroll_frame,
                task=task,
                on_toggle=self.on_toggle,
                on_edit=self.on_edit,
                on_move=self.on_move,
                on_delete=self.on_delete,
                on_pomodoro=self.on_pomodoro,
                on_schedule=self.on_schedule,
                show_quadrant_indicator=True,
            )
            card.pack(fill="x", pady=4, padx=4)

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        self.all_tasks = tasks
        self._render_tasks()
