"""
ui/calendar_view.py
Interactive Monthly Calendar View for Prior.
Allows users to visualize, schedule, and manage tasks across days of the month with quadrant color indicators.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from ui import theme
from ui.task_card import TaskCard


class CalendarView(ctk.CTkFrame):
    """
    Interactive Calendar View with month navigation, day grid, and selected day schedule.
    """

    def __init__(
        self,
        master: Any,
        tasks: List[Dict[str, Any]],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_move: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        on_quick_add: Callable[[str, Optional[str]], None],
        on_pomodoro: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.all_tasks = tasks
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_quick_add = on_quick_add
        self.on_pomodoro = on_pomodoro

        # Calendar state
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today

        self._build_ui()

    def _build_ui(self) -> None:
        # Top Control Bar (Month Navigation & Today button)
        self._build_header_bar()

        # Main Body: Split into Calendar Grid (Left) & Day Schedule (Right)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 1. Left: Calendar Grid Frame
        self.grid_container = ctk.CTkFrame(
            body,
            fg_color=theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        self.grid_container.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 2. Right: Selected Day Schedule Panel
        self.schedule_container = ctk.CTkFrame(
            body,
            fg_color=theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            width=340,
        )
        self.schedule_container.pack(side="right", fill="both", padx=(0, 0))
        self.schedule_container.pack_propagate(False)

        self._render_calendar_grid()
        self._render_day_schedule()

    def _build_header_bar(self) -> None:
        header_bar = ctk.CTkFrame(
            self,
            fg_color=theme.BG_CARD,
            corner_radius=10,
            height=52,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        header_bar.pack(fill="x", padx=8, pady=(8, 8))
        header_bar.pack_propagate(False)

        inner = ctk.CTkFrame(header_bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=8)

        # Left: Month & Year Title
        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year = ctk.CTkLabel(
            inner,
            text=f"📅 {month_name} {self.current_year}",
            font=(theme.FONT_DISPLAY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.lbl_month_year.pack(side="left")

        # Right: Navigation Controls
        nav_box = ctk.CTkFrame(inner, fg_color="transparent")
        nav_box.pack(side="right")

        btn_prev = ctk.CTkButton(
            nav_box,
            text="◀ Prev",
            width=64,
            height=32,
            corner_radius=6,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._prev_month,
        )
        btn_prev.pack(side="left", padx=(0, 6))

        btn_today = ctk.CTkButton(
            nav_box,
            text="Today",
            width=60,
            height=32,
            corner_radius=6,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._go_today,
        )
        btn_today.pack(side="left", padx=(0, 6))

        btn_next = ctk.CTkButton(
            nav_box,
            text="Next ▶",
            width=64,
            height=32,
            corner_radius=6,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._next_month,
        )
        btn_next.pack(side="left")

    def _render_calendar_grid(self) -> None:
        """Renders the 7-day header and 6-week monthly grid."""
        for child in self.grid_container.winfo_children():
            child.destroy()

        # Grid header: Days of Week (Mon - Sun)
        days_header = ctk.CTkFrame(self.grid_container, fg_color="transparent", height=28)
        days_header.pack(fill="x", padx=10, pady=(10, 4))

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for idx, d_name in enumerate(day_names):
            lbl_d = ctk.CTkLabel(
                days_header,
                text=d_name,
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=theme.TEXT_SECONDARY,
                width=60,
            )
            lbl_d.pack(side="left", fill="x", expand=True)

        # Build Month Matrix
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = date.today()

        # Map tasks by due_date string (YYYY-MM-DD)
        tasks_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for t in self.all_tasks:
            d_str = t.get("due_date")
            if d_str:
                tasks_by_date.setdefault(d_str, []).append(t)

        # Weeks Container
        weeks_frame = ctk.CTkFrame(self.grid_container, fg_color="transparent")
        weeks_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for week in cal:
            row_frame = ctk.CTkFrame(weeks_frame, fg_color="transparent")
            row_frame.pack(fill="both", expand=True, pady=2)

            for day_num in week:
                if day_num == 0:
                    # Empty cell outside of month
                    empty_cell = ctk.CTkFrame(row_frame, fg_color="transparent", corner_radius=6)
                    empty_cell.pack(side="left", fill="both", expand=True, padx=2)
                else:
                    cell_date = date(self.current_year, self.current_month, day_num)
                    date_str = cell_date.strftime("%Y-%m-%d")
                    day_tasks = tasks_by_date.get(date_str, [])

                    is_today = (cell_date == today)
                    is_selected = (cell_date == self.selected_date)

                    def _make_click_handler(d: date):
                        return lambda _: self._select_date(d)

                    handler = _make_click_handler(cell_date)

                    # Determine cell background & border
                    if is_selected:
                        cell_bg = theme.BG_INPUT
                        border_color = theme.ACCENT_PRIMARY
                        border_w = 2
                    elif is_today:
                        cell_bg = ("#EEF2FF", "#1E1B4B")
                        border_color = theme.ACCENT_PRIMARY
                        border_w = 1
                    else:
                        cell_bg = theme.BG_INPUT
                        border_color = theme.BORDER_COLOR
                        border_w = 1

                    cell = ctk.CTkFrame(
                        row_frame,
                        fg_color=cell_bg,
                        corner_radius=8,
                        border_width=border_w,
                        border_color=border_color,
                        cursor="hand2",
                    )
                    cell.pack(side="left", fill="both", expand=True, padx=2)

                    # Top row inside cell: Day number + Today indicator
                    cell_top = ctk.CTkFrame(cell, fg_color="transparent")
                    cell_top.pack(fill="x", padx=6, pady=(4, 2))

                    day_color = theme.ACCENT_PRIMARY if is_today else theme.TEXT_PRIMARY
                    lbl_num = ctk.CTkLabel(
                        cell_top,
                        text=str(day_num),
                        font=(theme.FONT_FAMILY, 12, "bold" if (is_today or is_selected) else "normal"),
                        text_color=day_color,
                    )
                    lbl_num.pack(side="left")

                    if day_tasks:
                        lbl_badge = ctk.CTkLabel(
                            cell_top,
                            text=str(len(day_tasks)),
                            font=(theme.FONT_FAMILY, 9, "bold"),
                            fg_color=theme.ACCENT_PRIMARY,
                            text_color="#FFFFFF",
                            corner_radius=6,
                            width=16,
                            height=16,
                        )
                        lbl_badge.pack(side="right")
                        lbl_badge.bind("<Button-1>", handler)

                    # Indicator dots for tasks
                    dots_frame = ctk.CTkFrame(cell, fg_color="transparent", height=12)
                    dots_frame.pack(fill="x", padx=6, pady=(2, 4))
                    dots_frame.pack_propagate(False)

                    # Show up to 4 quadrant colored dots
                    for t in day_tasks[:4]:
                        q = t.get("quadrant", "Q1_DO")
                        q_color = theme.QUADRANTS.get(q, theme.QUADRANTS["Q1_DO"])["color"]
                        dot = ctk.CTkFrame(dots_frame, width=6, height=6, corner_radius=3, fg_color=q_color)
                        dot.pack(side="left", padx=1)
                        dot.bind("<Button-1>", handler)

                    # Click event on cell to select date
                    cell.bind("<Button-1>", handler)
                    cell_top.bind("<Button-1>", handler)
                    lbl_num.bind("<Button-1>", handler)
                    dots_frame.bind("<Button-1>", handler)

    def _render_day_schedule(self) -> None:
        """Renders the task list and schedule details for the selected date."""
        for child in self.schedule_container.winfo_children():
            child.destroy()

        date_str = self.selected_date.strftime("%Y-%m-%d")
        formatted_heading = self.selected_date.strftime("%A, %b %d")

        # Top Section: Selected Date Heading & + Add Task button
        top_box = ctk.CTkFrame(self.schedule_container, fg_color="transparent")
        top_box.pack(fill="x", padx=14, pady=12)

        lbl_date_title = ctk.CTkLabel(
            top_box,
            text=formatted_heading,
            font=(theme.FONT_DISPLAY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_date_title.pack(fill="x")

        # + Add Task for this Date
        btn_add_day = ctk.CTkButton(
            top_box,
            text="+ Add Task for this Day",
            font=(theme.FONT_FAMILY, 11, "bold"),
            height=30,
            corner_radius=6,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=lambda: self.on_quick_add("Q1_DO", date_str),
        )
        btn_add_day.pack(fill="x", pady=(8, 0))

        # Scrollable Task List for selected day
        scroll_frame = ctk.CTkScrollableFrame(
            self.schedule_container,
            fg_color="transparent",
        )
        scroll_frame.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        # Filter tasks for selected date
        day_tasks = [t for t in self.all_tasks if t.get("due_date") == date_str]

        if not day_tasks:
            empty_box = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            empty_box.pack(fill="both", expand=True, pady=40)

            lbl_empty = ctk.CTkLabel(
                empty_box,
                text="No tasks scheduled for this day.\nClick above to add one!",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_MUTED,
                justify="center",
            )
            lbl_empty.pack()
        else:
            for task in day_tasks:
                card = TaskCard(
                    scroll_frame,
                    task=task,
                    on_toggle=self.on_toggle,
                    on_edit=self.on_edit,
                    on_move=self.on_move,
                    on_delete=self.on_delete,
                    on_pomodoro=self.on_pomodoro,
                )
                card.pack(fill="x", pady=4, padx=2)

    def _select_date(self, selected: date) -> None:
        self.selected_date = selected
        self._render_calendar_grid()
        self._render_day_schedule()

    def _prev_month(self) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1

        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year.configure(text=f"📅 {month_name} {self.current_year}")
        self._render_calendar_grid()

    def _next_month(self) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1

        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year.configure(text=f"📅 {month_name} {self.current_year}")
        self._render_calendar_grid()

    def _go_today(self) -> None:
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today

        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year.configure(text=f"📅 {month_name} {self.current_year}")
        self._render_calendar_grid()
        self._render_day_schedule()

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Refreshes calendar and day schedule with updated task list."""
        self.all_tasks = tasks
        self._render_calendar_grid()
        self._render_day_schedule()
