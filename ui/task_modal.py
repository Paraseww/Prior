"""
ui/task_modal.py
Modal dialog for creating and editing tasks with real-time Eisenhower quadrant evaluation,
embedded interactive calendar date picker, and comprehensive 1-12h / 00-59m / AM-PM reminder time controls.
"""

import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import determine_quadrant
from ui import theme
from ui.scrollable_dropdown import ScrollableOptionMenu


class TaskModal(ctk.CTkToplevel):
    """
    Modal window for Adding or Editing a task with full calendar & time scheduling controls.
    """

    def __init__(
        self,
        master: Any,
        on_save: Callable[[Dict[str, Any]], None],
        task: Optional[Dict[str, Any]] = None,
        default_quadrant: str = "Q1_DO",
        default_due_date: Optional[str] = None,
    ) -> None:
        super().__init__(master)
        self.on_save_callback = on_save
        self.task = task
        self.is_edit = task is not None
        self.current_quadrant = task.get("quadrant", default_quadrant) if task else default_quadrant
        self.default_due_date = default_due_date

        # Initial schedule state
        today = date.today()
        self.selected_date: Optional[date] = None
        raw_due = self.task.get("due_date") if self.task else self.default_due_date
        if raw_due:
            try:
                self.selected_date = datetime.strptime(str(raw_due).strip(), "%Y-%m-%d").date()
            except Exception:
                self.selected_date = None

        # Calendar Navigation state
        self.cal_year = self.selected_date.year if self.selected_date else today.year
        self.cal_month = self.selected_date.month if self.selected_date else today.month

        # Reminder Time state
        raw_reminder = self.task.get("reminder_time") if self.task else None
        self.reminder_enabled = bool(raw_reminder and str(raw_reminder).strip())
        self.selected_reminder: Optional[str] = str(raw_reminder).strip() if self.reminder_enabled else None
        self.current_time_str = self.selected_reminder or "12:00 PM"

        self.title("Edit Task" if self.is_edit else "Create New Task")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        # Center modal relative to master window with screen-adaptive dimensions
        self._center_modal(master)

        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(560, max(460, screen_w - 40))
            h = min(700, max(460, screen_h - 90))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(min(480, w), min(440, h))
        except Exception:
            self.geometry("560x700")
            self.minsize(520, 600)

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        # 1. Top Header Bar (Fixed)
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=24, pady=(18, 4))

        title_text = "Edit Task" if self.is_edit else "Create New Priority Task"
        if self.is_edit:
            subtitle_text = "Adjust task parameters, classification, and schedule"
        elif self.default_due_date:
            try:
                d_obj = datetime.strptime(self.default_due_date, "%Y-%m-%d")
                subtitle_text = f"📅 Scheduled for {d_obj.strftime('%A, %b %d, %Y')}"
            except Exception:
                subtitle_text = f"📅 Scheduled for {self.default_due_date}"
        else:
            subtitle_text = "Categorize and schedule your task on the Eisenhower Matrix"

        lbl_title = ctk.CTkLabel(
            top_bar,
            text=title_text,
            font=(theme.FONT_DISPLAY, 18, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            top_bar,
            text=subtitle_text,
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x")

        # 2. Main Scrollable Content Container
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=18, pady=(8, 8))

        # Task Title Field
        lbl_field_title = ctk.CTkLabel(
            scroll_frame,
            text="Task Title *",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_field_title.pack(fill="x", pady=(0, 3))

        self.entry_title = ctk.CTkEntry(
            scroll_frame,
            placeholder_text="What needs to get done?",
            font=(theme.FONT_FAMILY, 13),
            height=34,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
        )
        self.entry_title.pack(fill="x", pady=(0, 10))
        if self.task and self.task.get("title"):
            self.entry_title.insert(0, self.task["title"])

        # Description Field
        lbl_desc = ctk.CTkLabel(
            scroll_frame,
            text="Description / Notes (Optional)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_desc.pack(fill="x", pady=(0, 3))

        self.txt_desc = ctk.CTkTextbox(
            scroll_frame,
            font=(theme.FONT_FAMILY, 12),
            height=54,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            border_width=1,
        )
        self.txt_desc.pack(fill="x", pady=(0, 10))
        if self.task and self.task.get("description"):
            self.txt_desc.insert("1.0", self.task["description"])

        # Urgency & Importance Switches (Live determination)
        matrix_box = ctk.CTkFrame(scroll_frame, fg_color=theme.BG_INPUT, corner_radius=10, border_width=1, border_color=theme.BORDER_COLOR)
        matrix_box.pack(fill="x", pady=(0, 8))

        inner_box = ctk.CTkFrame(matrix_box, fg_color="transparent")
        inner_box.pack(fill="x", padx=14, pady=8)

        initial_urgent = self.current_quadrant in ("Q1_DO", "Q3_DELEGATE")
        initial_important = self.current_quadrant in ("Q1_DO", "Q2_SCHEDULE")

        self.switch_urgent = ctk.CTkSwitch(
            inner_box,
            text="🚨 Urgent (Immediate Deadline)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            command=self._on_switch_toggle,
        )
        self.switch_urgent.pack(side="left", fill="x", expand=True)
        if initial_urgent:
            self.switch_urgent.select()

        self.switch_important = ctk.CTkSwitch(
            inner_box,
            text="⭐ Important (High Value)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            command=self._on_switch_toggle,
        )
        self.switch_important.pack(side="right", fill="x", expand=True)
        if initial_important:
            self.switch_important.select()

        # Quadrant Preview Banner
        self.lbl_quadrant_badge = ctk.CTkLabel(
            scroll_frame,
            text="",
            font=(theme.FONT_FAMILY, 11, "bold"),
            height=26,
            corner_radius=6,
        )
        self.lbl_quadrant_badge.pack(fill="x", pady=(0, 12))
        self._update_quadrant_badge()

        # ====================================================================
        # 3. Schedule: Interactive Calendar Section
        # ====================================================================
        sched_box = ctk.CTkFrame(
            scroll_frame,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        sched_box.pack(fill="x", pady=(0, 12))

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
            presets_row.grid_columnconfigure(col, weight=1, uniform="task_modal_date_col")
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

        # Calendar Days Grid Frame
        self.grid_frame = ctk.CTkFrame(cal_box, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=6, pady=(0, 6))
        self._render_mini_calendar()

        # ====================================================================
        # 4. Reminder Time Section: 1-12h, 00-59m, AM/PM
        # ====================================================================
        time_box = ctk.CTkFrame(
            scroll_frame,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        time_box.pack(fill="x", pady=(0, 12))

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
            time_presets_row.grid_columnconfigure(col, weight=1, uniform="task_modal_time_col")
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
        # 5. Live Schedule Summary Banner
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
        self._update_schedule_summary()

        # ====================================================================
        # 6. Bottom Action Bar (Fixed)
        # ====================================================================
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(6, 16))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=(theme.FONT_FAMILY, 13),
            height=38,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_CARD_HOVER,
            command=self.destroy,
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_save = ctk.CTkButton(
            btn_row,
            text="Save Task" if self.is_edit else "Add to Board",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=38,
            corner_radius=8,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._on_save_clicked,
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(8, 0))

    def _render_mini_calendar(self) -> None:
        """Renders compact 7-column calendar grid inside the modal."""
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="task_modal_cal_col")

        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col, d_name in enumerate(day_names):
            lbl = ctk.CTkLabel(
                self.grid_frame,
                text=d_name,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.TEXT_SECONDARY,
                height=18,
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=(0, 2))

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
                    btn_fg = theme.ACCENT_PRIMARY
                    text_color = "#FFFFFF"
                elif is_today:
                    btn_fg = ("#EEF2FF", "#1E1B4B")
                    text_color = theme.ACCENT_PRIMARY
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
                    font=(theme.FONT_FAMILY, 10, "bold" if is_selected or is_today else "normal"),
                    width=28,
                    height=24,
                    corner_radius=5,
                    fg_color=btn_fg,
                    hover_color=theme.ACCENT_HOVER if is_selected else theme.BG_CARD_HOVER,
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
                    fg_color=theme.ACCENT_PRIMARY,
                    hover_color=theme.ACCENT_HOVER,
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
            if self.switch_reminder.get() and self.selected_reminder:
                self.lbl_sched_summary.configure(
                    text=f"📌 Scheduled for: {d_str} at {self.selected_reminder}",
                    text_color=("#065F46", "#34D399"),
                )
            else:
                self.lbl_sched_summary.configure(
                    text=f"📌 Scheduled for: {d_str} (No reminder time)",
                    text_color=("#065F46", "#34D399"),
                )
        else:
            self.lbl_sched_summary.configure(
                text="⚠️ No due date set (Task will be unscheduled)",
                text_color=theme.TEXT_MUTED,
            )

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

    def _on_save_clicked(self) -> None:
        title = self.entry_title.get().strip()
        if not title:
            self.entry_title.configure(border_color="#EF4444")
            return

        description = self.txt_desc.get("1.0", "end-1c").strip()
        due_date_str = self.selected_date.strftime("%Y-%m-%d") if self.selected_date else None
        reminder_time_str = self.selected_reminder if (self.selected_date and self.switch_reminder.get()) else None

        data = {
            "title": title,
            "description": description,
            "quadrant": self.current_quadrant,
            "due_date": due_date_str,
            "reminder_time": reminder_time_str,
        }

        self.on_save_callback(data)
        self.destroy()
