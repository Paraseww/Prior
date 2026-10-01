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
from ui.scrollable_dropdown import ScrollableOptionMenu


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
        self.current_time_str = self.selected_reminder or "12:00 PM"

        self.title("Prior - Schedule Task & Reminder")
        self.geometry("540x680")
        self.minsize(500, 600)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        # Center modal
        self._center_modal(master)
        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            w = 540
            h = 680
            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2
            self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

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

        # Calendar Days Grid Frame
        self.grid_frame = ctk.CTkFrame(cal_box, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=6, pady=(0, 6))
        self._render_mini_calendar()

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

        btn_save = ctk.CTkButton(
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
        btn_save.pack(side="right", fill="x", expand=True, padx=(6, 0))

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
        """Renders compact 7-column calendar grid inside the modal."""
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="sched_modal_cal_col")

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
                    font=(theme.FONT_FAMILY, 10, "bold" if is_selected or is_today else "normal"),
                    width=28,
                    height=24,
                    corner_radius=5,
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

    def _on_edit_clicked(self) -> None:
        self.destroy()
        if self.on_edit_task:
            self.on_edit_task(self.task)

    def _on_save_clicked(self) -> None:
        due_date_str = self.selected_date.strftime("%Y-%m-%d") if self.selected_date else None
        reminder_time_str = self.selected_reminder if (self.selected_date and self.switch_reminder.get()) else None
        self.on_save_schedule(self.task["id"], due_date_str, reminder_time_str)
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

