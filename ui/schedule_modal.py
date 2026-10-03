"""
ui/schedule_modal.py
Interactive Scheduling and Reminder modal dialog for Prior.
Allows users to assign due dates, choose quick presets, select calendar days, and configure reminder times.
"""

import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from project import validate_schedule_time
from ui import theme
from ui.scrollable_dropdown import ScrollableOptionMenu


class MiniCalendarCanvas(tk.Canvas):
    """
    High-performance, zero-latency canvas-based monthly calendar grid.
    Renders date cells, selection pills, and today highlights with sub-millisecond redraws.
    """

    def __init__(self, master: Any, on_date_selected: Callable[[date], None], **kwargs) -> None:
        super().__init__(master, highlightthickness=0, **kwargs)
        self.on_date_selected = on_date_selected
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self.selected_date: Optional[date] = date.today()
        self.today = date.today()
        self.hover_idx: Optional[int] = None
        self.cells: List[tuple[int, int, date, bool]] = []
        self.num_rows = 5

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_month(self, year: int, month: int, selected_date: Optional[date]) -> None:
        self.cal_year = year
        self.cal_month = month
        self.selected_date = selected_date
        self.redraw()

    def set_selected_date(self, selected_date: Optional[date]) -> None:
        self.selected_date = selected_date
        if selected_date:
            self.cal_year = selected_date.year
            self.cal_month = selected_date.month
        self.redraw()

    def _on_leave(self, event: Any) -> None:
        if self.hover_idx is not None:
            self.hover_idx = None
            self.config(cursor="")
            self.redraw()

    def _on_motion(self, event: Any) -> None:
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 10 or h <= 10 or not self.cells:
            return

        header_h = 22
        if event.y < header_h:
            new_hover = None
        else:
            col_w = w / 7
            row_h = (h - header_h) / max(1, self.num_rows)
            c = int(event.x // col_w)
            r = int((event.y - header_h) // row_h)
            idx = r * 7 + c
            new_hover = idx if 0 <= idx < len(self.cells) and 0 <= c < 7 and 0 <= r < self.num_rows else None

        if new_hover != self.hover_idx:
            self.hover_idx = new_hover
            self.config(cursor="hand2" if new_hover is not None else "")
            self.redraw()

    def _on_click(self, event: Any) -> None:
        if self.hover_idx is not None and 0 <= self.hover_idx < len(self.cells):
            d = self.cells[self.hover_idx][2]
            self.selected_date = d
            self.on_date_selected(d)

    def redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 10 or h <= 10:
            return

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg = theme.BG_CARD[1] if is_dark else theme.BG_CARD[0]
        self.config(bg=bg)

        col_w = w / 7
        header_h = 22
        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        muted_col = theme.TEXT_MUTED[1] if is_dark else theme.TEXT_MUTED[0]
        prim_col = theme.TEXT_PRIMARY[1] if is_dark else theme.TEXT_PRIMARY[0]
        sec_col = theme.TEXT_SECONDARY[1] if is_dark else theme.TEXT_SECONDARY[0]

        # Draw Day Names Header
        for c, name in enumerate(day_names):
            cx = (c + 0.5) * col_w
            self.create_text(cx, header_h / 2, text=name, fill=sec_col, font=(theme.FONT_FAMILY, 9, "bold"))

        # Prepare calendar cells
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self.cal_year, self.cal_month)
        self.num_rows = len(weeks)
        self.cells = []
        for r, week in enumerate(weeks):
            for c, cell_date in enumerate(week):
                self.cells.append((r, c, cell_date, cell_date.month == self.cal_month))

        rem_h = h - header_h
        row_h = rem_h / max(1, self.num_rows)

        for idx, (r, c, cell_date, is_curr_month) in enumerate(self.cells):
            x1 = c * col_w + 3
            y1 = header_h + r * row_h + 2
            x2 = (c + 1) * col_w - 3
            y2 = header_h + (r + 1) * row_h - 2

            is_selected = (self.selected_date is not None and cell_date == self.selected_date)
            is_today = (cell_date == self.today)
            is_hover = (idx == self.hover_idx)

            rad = 5
            pts = [
                x1 + rad, y1, x2 - rad, y1, x2, y1, x2, y1 + rad,
                x2, y2 - rad, x2, y2, x2 - rad, y2, x1 + rad, y2,
                x1, y2, x1, y2 - rad, x1, y1 + rad, x1, y1,
            ]

            if is_selected:
                fill_col = "#059669" if is_hover else "#10B981"
                text_col = "#FFFFFF"
                font_weight = "bold"
                self.create_polygon(pts, smooth=True, fill=fill_col, outline="")
            elif is_today:
                fill_col = ("#083324" if is_dark else "#D1FAE5") if is_hover else ("#042218" if is_dark else "#ECFDF5")
                text_col = "#10B981"
                font_weight = "bold"
                self.create_polygon(pts, smooth=True, fill=fill_col, outline="#10B981", width=1)
            elif is_curr_month:
                fill_col = (theme.BG_CARD_HOVER[1] if is_dark else theme.BG_CARD_HOVER[0]) if is_hover else ""
                text_col = prim_col
                font_weight = "normal"
                if fill_col:
                    self.create_polygon(pts, smooth=True, fill=fill_col, outline="")
            else:
                fill_col = (theme.BG_CARD_HOVER[1] if is_dark else theme.BG_CARD_HOVER[0]) if is_hover else ""
                text_col = muted_col
                font_weight = "normal"
                if fill_col:
                    self.create_polygon(pts, smooth=True, fill=fill_col, outline="")

            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            self.create_text(cx, cy, text=str(cell_date.day), fill=text_col, font=(theme.FONT_FAMILY, 10, font_weight))


class ScheduleModal(ctk.CTkToplevel):
    """
    Dedicated Scheduling & Reminder modal for tasks.
    """

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_save_schedule: Callable[[int, Optional[str], Optional[str]], None],
        on_complete_task: Optional[Callable[[int], None]] = None,
        on_edit_task: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_delete_task: Optional[Callable[[int], None]] = None,
    ) -> None:
        super().__init__(master)
        self.task = task
        self.on_save_schedule = on_save_schedule
        self.on_complete_task = on_complete_task
        self.on_edit_task = on_edit_task
        self.on_delete_task = on_delete_task

        # Parse initial task schedule state
        today = date.today()
        self.selected_date: Optional[date] = None
        if self.task.get("due_date"):
            try:
                self.selected_date = datetime.strptime(self.task["due_date"].strip(), "%Y-%m-%d").date()
            except Exception:
                self.selected_date = today
        else:
            self.selected_date = today

        # Calendar Navigation state
        self.cal_year = self.selected_date.year if self.selected_date else today.year
        self.cal_month = self.selected_date.month if self.selected_date else today.month

        # Reminder Time state
        raw_reminder = self.task.get("reminder_time")
        self.reminder_enabled = bool(raw_reminder and str(raw_reminder).strip())
        self.selected_reminder: Optional[str] = str(raw_reminder).strip() if self.reminder_enabled else None
        if self.selected_reminder:
            default_time = self.selected_reminder
        else:
            now = datetime.now()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            default_time = next_hour.strftime("%I:%M %p")
        self.current_time_str = default_time

        # Estimated Time to Complete (Runway in minutes: 0, 30, 60, 90, 120, etc.)
        self.estimated_duration = int(self.task.get("estimated_duration", 0) or 0)
        standard_presets = {0, 30, 60, 90, 120, 180, 240}
        self.custom_dur_active = self.estimated_duration > 0 and (self.estimated_duration not in standard_presets)

        self.title("Prior - Schedule Task & Reminder")
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(540, max(460, screen_w - 40))
            h = min(680, max(460, screen_h - 90))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(min(480, w), min(440, h))
        except Exception:
            self.geometry("540x680")
            self.minsize(500, 600)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        self._build_ui()

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        # 1. Target Task Header Card (Fixed at top)
        header_container = ctk.CTkFrame(self, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=(16, 4))

        task_box = ctk.CTkFrame(
            header_container,
            fg_color=theme.BG_INPUT,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        task_box.pack(fill="x")

        inner_task = ctk.CTkFrame(task_box, fg_color="transparent")
        inner_task.pack(fill="x", padx=14, pady=10)

        header_row = ctk.CTkFrame(inner_task, fg_color="transparent")
        header_row.pack(fill="x")

        lbl_sched_tag = ctk.CTkLabel(
            header_row,
            text="📅 SCHEDULING TARGET",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color="#10B981",
        )
        lbl_sched_tag.pack(side="left")

        if self.on_delete_task:
            btn_del = ctk.CTkButton(
                header_row,
                text="🗑 Delete Task",
                font=(theme.FONT_FAMILY, 11, "bold"),
                height=24,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#FEE2E2", "#2A0A0A"),
                text_color=("#EF4444", "#F87171"),
                border_width=1,
                border_color=("#FCA5A5", "#7F1D1D"),
                command=self._on_delete_clicked,
            )
            btn_del.pack(side="right")

        if self.on_edit_task:
            btn_edit = ctk.CTkButton(
                header_row,
                text="✎ Edit Task",
                font=(theme.FONT_FAMILY, 11, "bold"),
                height=24,
                corner_radius=6,
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=self._on_edit_clicked,
            )
            btn_edit.pack(side="right", padx=(0, 6) if self.on_delete_task else 0)

        # Task Title
        lbl_task_title = ctk.CTkLabel(
            inner_task,
            text=self.task.get("title", "Untitled Task"),
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            wraplength=440,
            justify="left",
        )
        lbl_task_title.pack(fill="x", pady=(4, 0))

        # Description / Notes (if present)
        task_notes = (self.task.get("description") or self.task.get("notes") or "").strip()
        if task_notes:
            lbl_notes = ctk.CTkLabel(
                inner_task,
                text=task_notes,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_SECONDARY,
                anchor="w",
                wraplength=440,
                justify="left",
            )
            lbl_notes.pack(fill="x", pady=(3, 0))

        # 2. Main Scrollable Content Container
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(4, 4))

        # ====================================================================
        # Choose Due Date (Calendar) Section
        # ====================================================================
        sched_box = ctk.CTkFrame(
            scroll_frame,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        sched_box.pack(fill="x", pady=(0, 10))

        inner_sched = ctk.CTkFrame(sched_box, fg_color="transparent")
        inner_sched.pack(fill="x", padx=12, pady=10)

        lbl_sched_header = ctk.CTkLabel(
            inner_sched,
            text="📅 Choose Due Date (Calendar)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_sched_header.pack(fill="x", pady=(0, 6))

        # Date Presets Row (Uniform Grid)
        presets_row = ctk.CTkFrame(inner_sched, fg_color="transparent")
        presets_row.pack(fill="x", pady=(0, 8))

        presets = [
            ("No Date", "none", None),
            ("Today", "today", 0),
            ("Tomorrow", "tomorrow", 1),
            ("+7 Days", "+7", 7),
        ]

        self.preset_buttons: Dict[str, ctk.CTkButton] = {}
        for col, (label, key, offset) in enumerate(presets):
            presets_row.grid_columnconfigure(col, weight=1, uniform="sched_modal_date_col")
            btn_p = ctk.CTkButton(
                presets_row,
                text=label,
                font=(theme.FONT_FAMILY, 11),
                width=0,
                height=26,
                corner_radius=6,
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=lambda off=offset: self._apply_date_preset(off),
            )
            btn_p.grid(row=0, column=col, sticky="nsew", padx=2)
            self.preset_buttons[key] = btn_p

        # Embedded Calendar Box
        cal_box = ctk.CTkFrame(
            inner_sched,
            fg_color=theme.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        cal_box.pack(fill="x", pady=(0, 4))

        # Month Nav Header
        cal_header = ctk.CTkFrame(cal_box, fg_color="transparent", height=30)
        cal_header.pack(fill="x", padx=8, pady=(6, 2))

        btn_prev = ctk.CTkButton(
            cal_header,
            text="◀",
            width=26,
            height=22,
            corner_radius=4,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._prev_month,
        )
        btn_prev.pack(side="left")

        month_name = calendar.month_name[self.cal_month]
        self.lbl_cal_title = ctk.CTkLabel(
            cal_header,
            text=f"{month_name} {self.cal_year}",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.lbl_cal_title.pack(side="left", fill="x", expand=True)

        btn_next = ctk.CTkButton(
            cal_header,
            text="▶",
            width=26,
            height=22,
            corner_radius=4,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._next_month,
        )
        btn_next.pack(side="right")

        # Fast, responsive Canvas-based Mini Calendar
        self.cal_canvas = MiniCalendarCanvas(
            cal_box,
            on_date_selected=self._on_date_tile_clicked,
            height=172,
        )
        self.cal_canvas.pack(fill="x", padx=6, pady=(0, 6))
        self.cal_canvas.set_month(self.cal_year, self.cal_month, self.selected_date)

        # ====================================================================
        # Reminder Time Section: 1-12h, 00-59m, AM/PM
        # ====================================================================
        time_box = ctk.CTkFrame(
            scroll_frame,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        time_box.pack(fill="x", pady=(0, 10))

        inner_time = ctk.CTkFrame(time_box, fg_color="transparent")
        inner_time.pack(fill="x", padx=12, pady=10)

        header_time_row = ctk.CTkFrame(inner_time, fg_color="transparent")
        header_time_row.pack(fill="x", pady=(0, 6))

        lbl_time_header = ctk.CTkLabel(
            header_time_row,
            text="⏰ Reminder Time (1-12 Hours & 00-59 Minutes)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_time_header.pack(side="left")

        self.switch_reminder = ctk.CTkSwitch(
            header_time_row,
            text="Enable",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_SECONDARY,
            command=self._on_reminder_switch_toggle,
        )
        self.switch_reminder.pack(side="right")
        if self.reminder_enabled:
            self.switch_reminder.select()

        # Quick Time Presets
        time_presets_row = ctk.CTkFrame(inner_time, fg_color="transparent")
        time_presets_row.pack(fill="x", pady=(0, 8))

        quick_times = [
            ("🌅 06:00 AM", "06:00 AM"),
            ("☀️ 12:00 PM", "12:00 PM"),
            ("🌆 06:00 PM", "06:00 PM"),
        ]

        self.time_preset_buttons: Dict[str, ctk.CTkButton] = {}
        for col, (label, val) in enumerate(quick_times):
            time_presets_row.grid_columnconfigure(col, weight=1, uniform="sched_modal_time_col")
            btn_t = ctk.CTkButton(
                time_presets_row,
                text=label,
                font=(theme.FONT_FAMILY, 11),
                width=0,
                height=26,
                corner_radius=6,
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=lambda v=val: self._select_preset_time(v),
            )
            btn_t.grid(row=0, column=col, sticky="nsew", padx=2)
            self.time_preset_buttons[val] = btn_t

        # Precise Time Selectors: Hour (01-12) : Minute (00-59) AM/PM
        self.time_picker_frame = ctk.CTkFrame(inner_time, fg_color="transparent")
        self.time_picker_frame.pack(fill="x", pady=(0, 4))

        lbl_custom_time = ctk.CTkLabel(
            self.time_picker_frame,
            text="Set Time:",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
        )
        lbl_custom_time.pack(side="left", padx=(0, 8))

        init_hour, init_min, init_ampm = self._parse_time_parts(self.current_time_str)

        # 1-12 Hours
        hours = [f"{i:02d}" for i in range(1, 13)]
        self.opt_hour = ScrollableOptionMenu(
            self.time_picker_frame,
            values=hours,
            width=68,
            height=28,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_height=180,
            command=self._on_time_changed,
        )
        self.opt_hour.set(init_hour)
        self.opt_hour.pack(side="left", padx=2)

        lbl_colon = ctk.CTkLabel(self.time_picker_frame, text=":", font=(theme.FONT_FAMILY, 14, "bold"))
        lbl_colon.pack(side="left")

        # 00-59 Minutes (All 60 minutes with scrollbar)
        minutes = [f"{i:02d}" for i in range(0, 60)]
        self.opt_minute = ScrollableOptionMenu(
            self.time_picker_frame,
            values=minutes,
            width=68,
            height=28,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_height=180,
            command=self._on_time_changed,
        )
        self.opt_minute.set(init_min)
        self.opt_minute.pack(side="left", padx=2)

        # AM / PM
        ampm_list = ["AM", "PM"]
        self.opt_ampm = ScrollableOptionMenu(
            self.time_picker_frame,
            values=ampm_list,
            width=68,
            height=28,
            corner_radius=6,
            fg_color=theme.BG_CARD,
            button_hover_color=theme.BG_CARD_HOVER,
            dropdown_height=90,
            command=self._on_time_changed,
        )
        self.opt_ampm.set(init_ampm)
        self.opt_ampm.pack(side="left", padx=4)

        # ====================================================================
        # ====================================================================
        # Estimated Duration (Runway & Drop-Dead Calculator) - ONLY FOR Q1 (Red Box)
        # ====================================================================
        is_q1 = self.task.get("quadrant") == "Q1_DO"
        if is_q1:
            self.duration_box = ctk.CTkFrame(
                scroll_frame,
                fg_color=theme.BG_INPUT,
                corner_radius=10,
                border_width=1,
                border_color=("#FCA5A5", "#7F1D1D"),
            )
            self.duration_box.pack(fill="x", pady=(0, 10))

            inner_dur = ctk.CTkFrame(self.duration_box, fg_color="transparent")
            inner_dur.pack(fill="x", padx=12, pady=10)

            header_dur_row = ctk.CTkFrame(inner_dur, fg_color="transparent")
            header_dur_row.pack(fill="x", pady=(0, 4))

            self.lbl_dur_header = ctk.CTkLabel(
                header_dur_row,
                text="⏱️ Estimated Time to Complete",
                font=(theme.FONT_FAMILY, 12, "bold"),
                text_color=("#DC2626", "#F87171"),
                anchor="w",
            )
            self.lbl_dur_header.pack(side="left")

            self.lbl_dur_hint = ctk.CTkLabel(
                inner_dur,
                text="How long will this task take? Prior alerts you before your drop-dead start time.",
                font=(theme.FONT_FAMILY, 10),
                text_color=theme.TEXT_MUTED,
                anchor="w",
            )
            self.lbl_dur_hint.pack(fill="x", pady=(0, 6))

            dur_presets_row = ctk.CTkFrame(inner_dur, fg_color="transparent")
            dur_presets_row.pack(fill="x", pady=(0, 4))

            duration_presets = [
                ("None", 0),
                ("30m", 30),
                ("1 hr", 60),
                ("2 hrs", 120),
                ("3 hrs", 180),
                ("Custom ✎", -1),
            ]
            self.dur_preset_buttons: Dict[int, ctk.CTkButton] = {}
            for col, (label, mins) in enumerate(duration_presets):
                dur_presets_row.grid_columnconfigure(col, weight=1, uniform="sched_modal_dur_col")
                btn_d = ctk.CTkButton(
                    dur_presets_row,
                    text=label,
                    font=(theme.FONT_FAMILY, 11),
                    width=0,
                    height=26,
                    corner_radius=6,
                    fg_color=theme.BG_CARD,
                    hover_color=theme.BG_CARD_HOVER,
                    text_color=theme.TEXT_PRIMARY,
                    command=lambda m=mins: self._select_preset_duration(m),
                )
                btn_d.grid(row=0, column=col, sticky="nsew", padx=2)
                self.dur_preset_buttons[mins] = btn_d

            # Custom Runway Inline Input Frame (shown when Custom is selected or duration is custom)
            self.custom_dur_frame = ctk.CTkFrame(
                inner_dur,
                fg_color=theme.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=theme.BORDER_COLOR,
            )

            custom_dur_inner = ctk.CTkFrame(self.custom_dur_frame, fg_color="transparent")
            custom_dur_inner.pack(fill="x", padx=10, pady=6)

            lbl_custom_dur = ctk.CTkLabel(
                custom_dur_inner,
                text="⏱️ Custom Runway:",
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=theme.TEXT_PRIMARY,
            )
            lbl_custom_dur.pack(side="left", padx=(0, 10))

            init_h = self.estimated_duration // 60 if self.estimated_duration > 0 else 1
            init_m = self.estimated_duration % 60 if self.estimated_duration > 0 else 0

            self.entry_dur_hours = ctk.CTkEntry(
                custom_dur_inner,
                width=50,
                height=28,
                corner_radius=6,
                justify="center",
                font=(theme.FONT_FAMILY, 12, "bold"),
                placeholder_text="0",
            )
            if init_h > 0 or self.custom_dur_active:
                self.entry_dur_hours.insert(0, str(init_h))
            self.entry_dur_hours.pack(side="left", padx=(0, 4))
            self.entry_dur_hours.bind("<KeyRelease>", self._on_custom_duration_input)

            lbl_h = ctk.CTkLabel(
                custom_dur_inner,
                text="hrs",
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_SECONDARY,
            )
            lbl_h.pack(side="left", padx=(0, 10))

            self.entry_dur_mins = ctk.CTkEntry(
                custom_dur_inner,
                width=50,
                height=28,
                corner_radius=6,
                justify="center",
                font=(theme.FONT_FAMILY, 12, "bold"),
                placeholder_text="0",
            )
            if init_m > 0 or self.custom_dur_active:
                self.entry_dur_mins.insert(0, str(init_m))
            self.entry_dur_mins.pack(side="left", padx=(0, 4))
            self.entry_dur_mins.bind("<KeyRelease>", self._on_custom_duration_input)

            lbl_m = ctk.CTkLabel(
                custom_dur_inner,
                text="mins",
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_SECONDARY,
            )
            lbl_m.pack(side="left", padx=(0, 12))

            self.btn_apply_custom_dur = ctk.CTkButton(
                custom_dur_inner,
                text="Apply",
                width=64,
                height=28,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color="#EF4444",
                hover_color="#DC2626",
                command=self._apply_custom_duration,
            )
            self.btn_apply_custom_dur.pack(side="right")

            if self.custom_dur_active:
                self.custom_dur_frame.pack(fill="x", pady=(6, 2))

        # ====================================================================
        # Live Schedule Summary Banner
        # ====================================================================
        self.summary_card = ctk.CTkFrame(
            scroll_frame,
            fg_color=("#ECFDF5", "#042218"),
            corner_radius=8,
            border_width=1,
            border_color=("#A7F3D0", "#064E3B"),
        )
        self.summary_card.pack(fill="x", pady=(0, 4))

        self.lbl_sched_summary = ctk.CTkLabel(
            self.summary_card,
            text="",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=("#065F46", "#34D399"),
        )
        self.lbl_sched_summary.pack(padx=10, pady=6)

        self._update_date_preset_buttons()
        self._update_duration_buttons()
        self._update_schedule_summary()

        # ====================================================================
        # Bottom Action Bar (Fixed)
        # ====================================================================
        action_container = ctk.CTkFrame(self, fg_color="transparent")
        action_container.pack(fill="x", padx=20, pady=(4, 14))

        btn_row = ctk.CTkFrame(action_container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=(theme.FONT_FAMILY, 13),
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self.destroy,
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_save = ctk.CTkButton(
            btn_row,
            text="💾 Save Schedule",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=36,
            corner_radius=8,
            fg_color="#10B981",
            hover_color="#059669",
            text_color="#FFFFFF",
            command=self._on_save_clicked,
        )
        self.btn_save.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Mark Task Completed & Finish Button
        btn_complete = ctk.CTkButton(
            action_container,
            text="✓ Mark Task Completed & Finish",
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#ECFDF5", "#042218"),
            text_color=("#10B981", "#34D399"),
            border_width=1,
            border_color=("#10B981", "#059669"),
            command=self._on_mark_completed,
        )
        btn_complete.pack(fill="x")

    def _render_mini_calendar(self) -> None:
        """Renders compact calendar view inside the modal with zero latency."""
        if hasattr(self, "cal_canvas"):
            self.cal_canvas.set_month(self.cal_year, self.cal_month, self.selected_date)

    def _on_date_tile_clicked(self, selected: date) -> None:
        self.selected_date = selected
        if selected.year != self.cal_year or selected.month != self.cal_month:
            self.cal_year = selected.year
            self.cal_month = selected.month
            month_name = calendar.month_name[self.cal_month]
            self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")

        self._render_mini_calendar()
        self._update_date_preset_buttons()
        self._update_schedule_summary()

    def _prev_month(self) -> None:
        if self.cal_month == 1:
            self.cal_month = 12
            self.cal_year -= 1
        else:
            self.cal_month -= 1
        month_name = calendar.month_name[self.cal_month]
        self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")
        self._render_mini_calendar()

    def _next_month(self) -> None:
        if self.cal_month == 12:
            self.cal_month = 1
            self.cal_year += 1
        else:
            self.cal_month += 1
        month_name = calendar.month_name[self.cal_month]
        self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")
        self._render_mini_calendar()

    def _apply_date_preset(self, days_offset: Optional[int]) -> None:
        if days_offset is None:
            self.selected_date = None
        else:
            self.selected_date = date.today() + timedelta(days=days_offset)
            self.cal_year = self.selected_date.year
            self.cal_month = self.selected_date.month
            month_name = calendar.month_name[self.cal_month]
            self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")

        self._render_mini_calendar()
        self._update_date_preset_buttons()
        self._update_schedule_summary()

    def _update_date_preset_buttons(self) -> None:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        plus7 = today + timedelta(days=7)

        active_key = None
        if self.selected_date is None:
            active_key = "none"
        elif self.selected_date == today:
            active_key = "today"
        elif self.selected_date == tomorrow:
            active_key = "tomorrow"
        elif self.selected_date == plus7:
            active_key = "+7"

        for key, btn in self.preset_buttons.items():
            if key == active_key:
                btn.configure(
                    fg_color="#10B981",
                    hover_color="#059669",
                    text_color="#FFFFFF",
                )
            else:
                btn.configure(
                    fg_color=theme.BG_CARD,
                    hover_color=theme.BG_CARD_HOVER,
                    text_color=theme.TEXT_PRIMARY,
                )

    def _parse_time_parts(self, time_str: Optional[str]) -> tuple[str, str, str]:
        if not time_str:
            return "12", "00", "PM"
        try:
            parts = str(time_str).strip().split()
            ampm = parts[1].upper() if len(parts) > 1 else "PM"
            time_parts = parts[0].split(":")
            h = f"{int(time_parts[0]):02d}"
            m = f"{int(time_parts[1]):02d}"
            return h, m, ampm
        except Exception:
            return "12", "00", "PM"

    def _select_preset_time(self, time_val: str) -> None:
        self.switch_reminder.select()
        h, m, ampm = self._parse_time_parts(time_val)
        self.opt_hour.set(h)
        self.opt_minute.set(m)
        self.opt_ampm.set(ampm)
        self.current_time_str = time_val
        self.selected_reminder = time_val
        self._update_schedule_summary()

    def _select_preset_duration(self, minutes: int) -> None:
        if minutes == -1:
            self.custom_dur_active = True
            h = self.estimated_duration // 60 if self.estimated_duration > 0 else 1
            m = self.estimated_duration % 60 if self.estimated_duration > 0 else 0
            if self.estimated_duration == 0:
                self.estimated_duration = 60
            self.entry_dur_hours.delete(0, "end")
            self.entry_dur_hours.insert(0, str(h) if h > 0 else "")
            self.entry_dur_mins.delete(0, "end")
            self.entry_dur_mins.insert(0, str(m) if m > 0 else "")
            self._show_custom_dur_frame(True)
            self.entry_dur_hours.focus_set()
        else:
            self.custom_dur_active = False
            self.estimated_duration = minutes
            self._show_custom_dur_frame(False)

        self._update_duration_buttons()
        self._update_schedule_summary()

    def _show_custom_dur_frame(self, show: bool) -> None:
        if not hasattr(self, "custom_dur_frame"):
            return
        if show:
            if not self.custom_dur_frame.winfo_ismapped():
                self.custom_dur_frame.pack(fill="x", pady=(6, 2))
        else:
            if self.custom_dur_frame.winfo_ismapped():
                self.custom_dur_frame.pack_forget()

    def _on_custom_duration_input(self, _: Any = None) -> None:
        h_str = self.entry_dur_hours.get().strip()
        m_str = self.entry_dur_mins.get().strip()
        try:
            h = int(h_str) if h_str else 0
        except ValueError:
            h = 0
        try:
            m = int(m_str) if m_str else 0
        except ValueError:
            m = 0

        h = max(0, min(48, h))
        m = max(0, min(59, m)) if h > 0 else max(0, min(2880, m))

        self.estimated_duration = h * 60 + m
        self._update_duration_buttons()
        self._update_schedule_summary()

    def _apply_custom_duration(self) -> None:
        self._on_custom_duration_input()
        h = self.estimated_duration // 60
        m = self.estimated_duration % 60
        self.entry_dur_hours.delete(0, "end")
        if h > 0:
            self.entry_dur_hours.insert(0, str(h))
        self.entry_dur_mins.delete(0, "end")
        if m > 0 or (h == 0 and self.estimated_duration > 0):
            self.entry_dur_mins.insert(0, str(m))

    def _update_duration_buttons(self) -> None:
        if not hasattr(self, "dur_preset_buttons"):
            return
        is_q1 = self.task.get("quadrant") == "Q1_DO"
        active_color = "#EF4444" if is_q1 else theme.ACCENT_PRIMARY
        active_hover = "#DC2626" if is_q1 else theme.ACCENT_HOVER

        if hasattr(self, "btn_apply_custom_dur"):
            self.btn_apply_custom_dur.configure(fg_color=active_color, hover_color=active_hover)

        standard_presets = {0, 30, 60, 90, 120, 180, 240}
        is_custom = getattr(self, "custom_dur_active", False) or (self.estimated_duration > 0 and self.estimated_duration not in standard_presets)

        if is_custom:
            self._show_custom_dur_frame(True)

        for mins, btn in self.dur_preset_buttons.items():
            if (mins == -1 and is_custom) or (not is_custom and mins == self.estimated_duration):
                btn.configure(
                    fg_color=active_color,
                    hover_color=active_hover,
                    text_color="#FFFFFF",
                )
            else:
                btn.configure(
                    fg_color=theme.BG_CARD,
                    hover_color=theme.BG_CARD_HOVER,
                    text_color=theme.TEXT_PRIMARY,
                )

    def _on_time_changed(self, _: Any = None) -> None:
        h = self.opt_hour.get()
        m = self.opt_minute.get()
        ampm = self.opt_ampm.get()
        self.current_time_str = f"{h}:{m} {ampm}"
        if self.switch_reminder.get():
            self.selected_reminder = self.current_time_str
        else:
            self.selected_reminder = None
        self._update_schedule_summary()

    def _on_reminder_switch_toggle(self) -> None:
        if self.switch_reminder.get():
            h = self.opt_hour.get()
            m = self.opt_minute.get()
            ampm = self.opt_ampm.get()
            self.current_time_str = f"{h}:{m} {ampm}"
            self.selected_reminder = self.current_time_str
        else:
            self.selected_reminder = None
        self._update_schedule_summary()

    def _update_schedule_summary(self) -> None:
        if self.selected_date:
            d_str = self.selected_date.strftime("%a, %b %d, %Y")
            rem_str = self.selected_reminder if (self.switch_reminder.get() and self.selected_reminder) else None

            is_valid, err_msg = validate_schedule_time(self.selected_date, rem_str)
            if not is_valid:
                self.summary_card.configure(
                    fg_color=("#FEF2F2", "#3A0D0D"),
                    border_color=("#FCA5A5", "#7F1D1D"),
                )
                self.lbl_sched_summary.configure(
                    text=f"⚠️ {err_msg}",
                    text_color=("#DC2626", "#F87171"),
                )
                if hasattr(self, "btn_save"):
                    self.btn_save.configure(state="disabled", fg_color=("#9CA3AF", "#4B5563"))
                return

            if hasattr(self, "btn_save"):
                self.btn_save.configure(state="normal", fg_color="#10B981")

            # Drop-Dead Runway Calculation ONLY for Q1 (Red Box) when estimated duration is set
            is_q1 = self.task.get("quadrant") == "Q1_DO"
            if is_q1 and rem_str and self.estimated_duration > 0:
                try:
                    rem_dt = datetime.strptime(rem_str, "%I:%M %p").time()
                except ValueError:
                    try:
                        rem_dt = datetime.strptime(rem_str, "%H:%M").time()
                    except ValueError:
                        rem_dt = None

                if rem_dt:
                    deadline_dt = datetime.combine(self.selected_date, rem_dt)
                    drop_dead_dt = deadline_dt - timedelta(minutes=self.estimated_duration)
                    drop_dead_str = drop_dead_dt.strftime("%I:%M %p")
                    if self.estimated_duration < 60:
                        dur_text = f"{self.estimated_duration}m"
                    elif self.estimated_duration % 60 == 0:
                        dur_text = f"{self.estimated_duration // 60}h"
                    else:
                        dur_text = f"{self.estimated_duration // 60}h {self.estimated_duration % 60}m"

                    self.summary_card.configure(
                        fg_color=("#FEF2F2", "#3A0D0D"),
                        border_color=("#FCA5A5", "#7F1D1D"),
                    )
                    self.lbl_sched_summary.configure(
                        text=f"🚨 Point of No Return: {drop_dead_str}\n(Start by {drop_dead_str} to finish your {dur_text} work before {rem_str} deadline!)",
                        text_color=("#DC2626", "#F87171"),
                    )
                    return

            self.summary_card.configure(
                fg_color=("#ECFDF5", "#042218"),
                border_color=("#A7F3D0", "#064E3B"),
            )
            if rem_str:
                self.lbl_sched_summary.configure(
                    text=f"📌 Scheduled for: {d_str} at {rem_str}",
                    text_color=("#065F46", "#34D399"),
                )
            else:
                self.lbl_sched_summary.configure(
                    text=f"📌 Scheduled for: {d_str} (No reminder time)",
                    text_color=("#065F46", "#34D399"),
                )
        else:
            self.summary_card.configure(
                fg_color=("#ECFDF5", "#042218"),
                border_color=("#A7F3D0", "#064E3B"),
            )
            if hasattr(self, "btn_save"):
                self.btn_save.configure(state="normal", fg_color="#10B981")
            self.lbl_sched_summary.configure(
                text="⚠️ No due date set (Task will be unscheduled)",
                text_color=theme.TEXT_MUTED,
            )

    def _on_edit_clicked(self) -> None:
        self.destroy()
        if self.on_edit_task:
            self.on_edit_task(self.task)

    def _on_save_clicked(self) -> None:
        due_date_str = self.selected_date.strftime("%Y-%m-%d") if self.selected_date else None
        reminder_time_str = self.selected_reminder if (self.selected_date and self.switch_reminder.get()) else None

        # Validate schedule date and time
        is_valid, err_msg = validate_schedule_time(self.selected_date, reminder_time_str)
        if not is_valid:
            self._update_schedule_summary()
            return

        saved_dur = self.estimated_duration if self.task.get("quadrant") == "Q1_DO" else 0
        self.on_save_schedule(self.task["id"], due_date_str, reminder_time_str, saved_dur)
        self.destroy()

    def _on_mark_completed(self) -> None:
        if self.on_complete_task and "id" in self.task:
            self.on_complete_task(self.task["id"])
        self.destroy()

    def _on_delete_clicked(self) -> None:
        if self.on_delete_task and "id" in self.task:
            task_id = self.task["id"]
            self.destroy()
            self.on_delete_task(task_id)
        else:
            self.destroy()

