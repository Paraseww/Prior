"""
ui/schedule_modal.py
Interactive Scheduling and Reminder modal dialog for Prior.
Allows users to assign due dates, choose quick presets, select calendar days, and configure reminder times.
"""

import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

from ui import theme


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
    ) -> None:
        super().__init__(master)
        self.task = task
        self.on_save_schedule = on_save_schedule
        self.on_complete_task = on_complete_task
        self.on_edit_task = on_edit_task

        self.title("Prior — Schedule Task & Reminder")
        self.geometry("520x730")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Apply Prior application icon
        theme.apply_prior_icon(self)

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
        self.reminder_enabled = bool(self.task.get("reminder_time"))
        self.selected_time: str = self.task.get("reminder_time") or "06:00 AM"

        # Center modal
        self._center_modal(master)
        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() - 520) // 2
            y = master.winfo_y() + (master.winfo_height() - 730) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=18)

        # 1. Target Task Header Card
        task_box = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        task_box.pack(fill="x", pady=(0, 12))

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

        if self.on_edit_task:
            btn_edit = ctk.CTkButton(
                header_row,
                text="✎ Edit Task",
                font=(theme.FONT_FAMILY, 11, "bold"),
                width=76,
                height=24,
                corner_radius=6,
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self._on_edit_clicked,
            )
            btn_edit.pack(side="right")

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

        # 2. Section: Date Selection & Quick Presets
        lbl_section_date = ctk.CTkLabel(
            container,
            text="1. Choose Due Date",
            font=(theme.FONT_DISPLAY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_section_date.pack(fill="x", pady=(0, 6))

        # Quick Date Presets Row (Uniform Grid)
        presets_row = ctk.CTkFrame(container, fg_color="transparent")
        presets_row.pack(fill="x", pady=(0, 8))

        presets = [
            ("Today", 0),
            ("Tomorrow", 1),
            ("+7 Days", 7),
        ]

        for col, (label, offset) in enumerate(presets):
            presets_row.grid_columnconfigure(col, weight=1, uniform="date_col")
            btn_p = ctk.CTkButton(
                presets_row,
                text=label,
                font=(theme.FONT_FAMILY, 11),
                width=0,
                height=28,
                corner_radius=6,
                fg_color=theme.BG_INPUT,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=lambda off=offset: self._apply_date_offset(off),
            )
            btn_p.grid(row=0, column=col, sticky="nsew", padx=2)

        # Embedded Calendar Box
        cal_box = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        cal_box.pack(fill="x", pady=(0, 12))

        # Month Nav Header
        cal_header = ctk.CTkFrame(cal_box, fg_color="transparent", height=34)
        cal_header.pack(fill="x", padx=10, pady=(6, 2))

        btn_prev = ctk.CTkButton(
            cal_header,
            text="◀",
            width=30,
            height=24,
            corner_radius=5,
            fg_color=theme.BG_CARD,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._prev_month,
        )
        btn_prev.pack(side="left")

        month_name = calendar.month_name[self.cal_month]
        self.lbl_cal_title = ctk.CTkLabel(
            cal_header,
            text=f"{month_name} {self.cal_year}",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.lbl_cal_title.pack(side="left", fill="x", expand=True)

        btn_next = ctk.CTkButton(
            cal_header,
            text="▶",
            width=30,
            height=24,
            corner_radius=5,
            fg_color=theme.BG_CARD,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._next_month,
        )
        btn_next.pack(side="right")

        # Calendar Days Grid Frame
        self.grid_frame = ctk.CTkFrame(cal_box, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=8, pady=(0, 6))
        self._render_mini_calendar()

        # 3. Section: Reminder & Time Picker
        lbl_section_time = ctk.CTkLabel(
            container,
            text="2. Reminder Time",
            font=(theme.FONT_DISPLAY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_section_time.pack(fill="x", pady=(0, 6))

        # Time Presets Row (Uniform Grid)
        time_presets_row = ctk.CTkFrame(container, fg_color="transparent")
        time_presets_row.pack(fill="x", pady=(0, 8))

        time_presets = [
            ("🌅 06:00 AM", "06:00 AM"),
            ("☀️ 12:00 PM", "12:00 PM"),
            ("🌆 06:00 PM", "06:00 PM"),
        ]

        self.time_buttons: Dict[str, ctk.CTkButton] = {}
        for col, (label, val) in enumerate(time_presets):
            time_presets_row.grid_columnconfigure(col, weight=1, uniform="time_col")
            btn_t = ctk.CTkButton(
                time_presets_row,
                text=label,
                font=(theme.FONT_FAMILY, 11),
                width=0,
                height=28,
                corner_radius=6,
                fg_color=theme.BG_INPUT if val != self.selected_time else "#10B981",
                hover_color=theme.BG_CARD_HOVER if val != self.selected_time else "#059669",
                text_color=theme.TEXT_PRIMARY if val != self.selected_time else "#FFFFFF",
                command=lambda v=val: self._select_preset_time(v),
            )
            btn_t.grid(row=0, column=col, sticky="nsew", padx=2)
            self.time_buttons[val] = btn_t

        # Custom Time Selector Row
        custom_time_box = ctk.CTkFrame(container, fg_color="transparent")
        custom_time_box.pack(fill="x", pady=(0, 10))

        lbl_custom = ctk.CTkLabel(
            custom_time_box,
            text="Custom Time:",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
        )
        lbl_custom.pack(side="left", padx=(0, 8))

        # Parse current hour, minute, am/pm
        init_hour, init_min, init_ampm = self._parse_time_parts(self.selected_time)

        hours = [f"{i:02d}" for i in range(1, 13)]
        self.opt_hour = ctk.CTkOptionMenu(
            custom_time_box,
            values=hours,
            width=64,
            height=30,
            fg_color="#10B981",
            button_color="#059669",
            button_hover_color="#047857",
            dropdown_hover_color="#059669",
            command=self._on_custom_time_changed,
        )
        self.opt_hour.set(init_hour)
        self.opt_hour.pack(side="left", padx=2)

        lbl_colon = ctk.CTkLabel(custom_time_box, text=":", font=(theme.FONT_FAMILY, 14, "bold"))
        lbl_colon.pack(side="left")

        minutes = ["00", "15", "30", "45"]
        self.opt_minute = ctk.CTkOptionMenu(
            custom_time_box,
            values=minutes,
            width=64,
            height=30,
            fg_color="#10B981",
            button_color="#059669",
            button_hover_color="#047857",
            dropdown_hover_color="#059669",
            command=self._on_custom_time_changed,
        )
        self.opt_minute.set(init_min)
        self.opt_minute.pack(side="left", padx=2)

        ampm_list = ["AM", "PM"]
        self.opt_ampm = ctk.CTkOptionMenu(
            custom_time_box,
            values=ampm_list,
            width=64,
            height=30,
            fg_color="#10B981",
            button_color="#059669",
            button_hover_color="#047857",
            dropdown_hover_color="#059669",
            command=self._on_custom_time_changed,
        )
        self.opt_ampm.set(init_ampm)
        self.opt_ampm.pack(side="left", padx=4)

        # 4. Schedule Live Summary Banner
        self.summary_card = ctk.CTkFrame(
            container,
            fg_color=("#ECFDF5", "#042218"),
            corner_radius=8,
            border_width=1,
            border_color=("#A7F3D0", "#064E3B"),
        )
        self.summary_card.pack(fill="x", pady=(0, 16))

        self.lbl_summary = ctk.CTkLabel(
            self.summary_card,
            text="",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=("#065F46", "#34D399"),
        )
        self.lbl_summary.pack(padx=12, pady=8)
        self._update_summary_banner()

        # 5. Action Buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=(theme.FONT_FAMILY, 13),
            height=38,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self.destroy,
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_save = ctk.CTkButton(
            btn_row,
            text="💾 Save Schedule",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=38,
            corner_radius=8,
            fg_color="#10B981",
            hover_color="#059669",
            text_color="#FFFFFF",
            command=self._on_save_clicked,
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # 6. Mark Task Completed & Finish Button
        btn_complete = ctk.CTkButton(
            container,
            text="✓ Mark Task Completed & Finish",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=36,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#ECFDF5", "#042218"),
            text_color=("#10B981", "#34D399"),
            border_width=1,
            border_color=("#10B981", "#059669"),
            command=self._on_mark_completed,
        )
        btn_complete.pack(fill="x", pady=(10, 0))

    def _render_mini_calendar(self) -> None:
        """Renders compact 7-column calendar grid inside the modal."""
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="mini_cal_col")

        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col, d_name in enumerate(day_names):
            lbl = ctk.CTkLabel(
                self.grid_frame,
                text=d_name,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.TEXT_SECONDARY,
                height=20,
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=(0, 4))

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self.cal_year, self.cal_month)
        today = date.today()

        for row_idx, week in enumerate(weeks):
            self.grid_frame.grid_rowconfigure(row_idx + 1, weight=1)
            for col_idx, cell_date in enumerate(week):
                is_curr_month = (cell_date.month == self.cal_month)
                is_selected = (self.selected_date and cell_date == self.selected_date)
                is_today = (cell_date == today)

                if is_selected:
                    btn_fg = "#10B981"
                    text_color = "#FFFFFF"
                elif is_today:
                    btn_fg = ("#ECFDF5", "#042218")
                    text_color = "#10B981"
                elif is_curr_month:
                    btn_fg = theme.BG_CARD
                    text_color = theme.TEXT_PRIMARY
                else:
                    btn_fg = "transparent"
                    text_color = theme.TEXT_MUTED

                def _make_handler(d: date):
                    return lambda: self._on_date_tile_clicked(d)

                btn_cell = ctk.CTkButton(
                    self.grid_frame,
                    text=str(cell_date.day),
                    font=(theme.FONT_FAMILY, 11, "bold" if is_selected or is_today else "normal"),
                    width=28,
                    height=26,
                    corner_radius=6,
                    fg_color=btn_fg,
                    hover_color="#059669" if is_selected else theme.BG_CARD_HOVER,
                    text_color=text_color,
                    command=_make_handler(cell_date),
                )
                btn_cell.grid(row=row_idx + 1, column=col_idx, sticky="nsew", padx=1, pady=1)

    def _on_date_tile_clicked(self, selected: date) -> None:
        self.selected_date = selected
        if selected.year != self.cal_year or selected.month != self.cal_month:
            self.cal_year = selected.year
            self.cal_month = selected.month
            month_name = calendar.month_name[self.cal_month]
            self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")

        self._render_mini_calendar()
        self._update_summary_banner()

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

    def _apply_date_offset(self, days_offset: Optional[int]) -> None:
        if days_offset is None:
            self.selected_date = None
        else:
            self.selected_date = date.today() + timedelta(days=days_offset)
            self.cal_year = self.selected_date.year
            self.cal_month = self.selected_date.month
            month_name = calendar.month_name[self.cal_month]
            self.lbl_cal_title.configure(text=f"{month_name} {self.cal_year}")

        self._render_mini_calendar()
        self._update_summary_banner()

    def _get_weekend_offset(self) -> int:
        today = date.today()
        # Saturday is weekday 5
        days_ahead = (5 - today.weekday()) % 7
        return days_ahead if days_ahead > 0 else 7

    def _get_next_monday_offset(self) -> int:
        today = date.today()
        # Monday is weekday 0
        days_ahead = (0 - today.weekday()) % 7
        return days_ahead if days_ahead > 0 else 7

    def _select_preset_time(self, time_val: str) -> None:
        self.selected_time = time_val
        h, m, ampm = self._parse_time_parts(time_val)
        self.opt_hour.set(h)
        self.opt_minute.set(m)
        self.opt_ampm.set(ampm)

        for val, btn in self.time_buttons.items():
            if val == time_val:
                btn.configure(fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF")
            else:
                btn.configure(fg_color=theme.BG_INPUT, hover_color=theme.BG_CARD_HOVER, text_color=theme.TEXT_PRIMARY)

        self._update_summary_banner()

    def _on_custom_time_changed(self, _: Any = None) -> None:
        h = self.opt_hour.get()
        m = self.opt_minute.get()
        ampm = self.opt_ampm.get()
        self.selected_time = f"{h}:{m} {ampm}"

        for val, btn in self.time_buttons.items():
            if val == self.selected_time:
                btn.configure(fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF")
            else:
                btn.configure(fg_color=theme.BG_INPUT, hover_color=theme.BG_CARD_HOVER, text_color=theme.TEXT_PRIMARY)

        self._update_summary_banner()

    def _parse_time_parts(self, time_str: str) -> tuple[str, str, str]:
        try:
            parts = time_str.strip().split()
            ampm = parts[1].upper() if len(parts) > 1 else "AM"
            time_parts = parts[0].split(":")
            h = f"{int(time_parts[0]):02d}"
            m = f"{int(time_parts[1]):02d}"
            return h, m, ampm
        except Exception:
            return "06", "00", "AM"

    def _update_summary_banner(self) -> None:
        if self.selected_date:
            d_str = self.selected_date.strftime("%A, %b %d, %Y")
            self.lbl_summary.configure(
                text=f"📌 Scheduled for: {d_str} at {self.selected_time}",
            )
        else:
            self.lbl_summary.configure(
                text="⚠️ No due date set (Task will be unscheduled)",
            )

    def _on_edit_clicked(self) -> None:
        self.destroy()
        if self.on_edit_task:
            self.on_edit_task(self.task)

    def _on_save_clicked(self) -> None:
        due_date_str = self.selected_date.strftime("%Y-%m-%d") if self.selected_date else None
        reminder_time_str = self.selected_time if self.selected_date else None
        self.on_save_schedule(self.task["id"], due_date_str, reminder_time_str)
        self.destroy()

    def _on_mark_completed(self) -> None:
        if self.on_complete_task and "id" in self.task:
            self.on_complete_task(self.task["id"])
        self.destroy()
