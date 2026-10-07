"""
ui/list_view.py
Chronological and filterable List View for Prior tasks.
"""

from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from project import filter_tasks, is_task_delayed
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
        on_archive: Optional[Callable[[int], None]] = None,
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
        self.on_archive = on_archive or on_delete
        self.on_clear_completed = on_clear_completed
        self.on_pomodoro = on_pomodoro
        self.on_schedule = on_schedule

        self.filter_quadrant = "ALL"
        self.filter_status = "ALL"

        # Card reconciliation cache to avoid recreating untouched cards
        self.cards: Dict[int, TaskCard] = {}
        self.card_signatures: Dict[int, Any] = {}
        self.card_order: List[int] = []
        self.empty_lbl: Optional[ctk.CTkLabel] = None

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
        # Preserve scroll position if already scrolled
        yview_pos = 0.0
        try:
            if hasattr(self.scroll_frame, "_parent_canvas"):
                yview_pos = self.scroll_frame._parent_canvas.yview()[0]
        except Exception:
            pass

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
            # Clear any existing task cards
            for card in self.cards.values():
                try:
                    card.destroy()
                except Exception:
                    pass
            self.cards.clear()
            self.card_signatures.clear()
            self.card_order.clear()

            if not self.empty_lbl or not self.empty_lbl.winfo_exists():
                self.empty_lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text="No matching tasks found.",
                    font=(theme.FONT_FAMILY, 13),
                    text_color=theme.TEXT_MUTED,
                )
                self.empty_lbl.pack(pady=50)
            return

        # If there are tasks, remove empty label if present
        if self.empty_lbl and self.empty_lbl.winfo_exists():
            self.empty_lbl.destroy()
            self.empty_lbl = None

        current_task_ids = [t["id"] for t in filtered]

        # 1. Remove deleted or filtered-out cards
        for t_id in list(self.cards.keys()):
            if t_id not in current_task_ids:
                try:
                    self.cards[t_id].destroy()
                except Exception:
                    pass
                del self.cards[t_id]
                self.card_signatures.pop(t_id, None)

        # 2. Check each task: if modified, destroy only that card so it gets recreated
        for task in filtered:
            t_id = task["id"]
            sig = (dict(task), is_task_delayed(task))
            if t_id in self.cards:
                if self.card_signatures.get(t_id) != sig:
                    try:
                        self.cards[t_id].destroy()
                    except Exception:
                        pass
                    del self.cards[t_id]
                    self.card_signatures.pop(t_id, None)

        # 3. Create any missing / updated cards
        cards_changed = False
        for task in filtered:
            t_id = task["id"]
            if t_id not in self.cards:
                sig = (dict(task), is_task_delayed(task))
                card = TaskCard(
                    self.scroll_frame,
                    task=task,
                    on_toggle=self.on_toggle,
                    on_edit=self.on_edit,
                    on_move=self.on_move,
                    on_delete=self.on_delete,
                    on_archive=self.on_archive,
                    on_pomodoro=self.on_pomodoro,
                    on_schedule=self.on_schedule,
                    show_quadrant_indicator=True,
                )
                self.cards[t_id] = card
                self.card_signatures[t_id] = sig
                cards_changed = True

        # 4. If cards were added/updated or order changed, pack them in exact sequence
        if cards_changed or self.card_order != current_task_ids:
            for t_id in current_task_ids:
                if t_id in self.cards:
                    self.cards[t_id].pack_forget()
                    self.cards[t_id].pack(fill="x", pady=4, padx=4)
            self.card_order = list(current_task_ids)

        # 5. Restore scroll position
        if yview_pos > 0.0:
            try:
                self.scroll_frame._parent_canvas.yview_moveto(yview_pos)
            except Exception:
                pass

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        self.all_tasks = tasks
        self._render_tasks()
