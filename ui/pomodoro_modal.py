"""
ui/pomodoro_modal.py
Interactive Pomodoro Focus Timer modal dialog for Prior.
Enables dedicated deep-work sessions (25m work / 5m break / 15m long break) on tasks
with a 4-stage cycle engine, visual progress indicators, and automated stage progression.
"""

from pathlib import Path
import sys
import threading
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

import database
from project import (
    calculate_pomodoro_stage,
    calculate_recommended_sprints,
    format_timer_display,
)
from ui import theme


class PomodoroModal(ctk.CTkToplevel):
    """
    Pomodoro Focus Timer window for a selected task with 4-stage cycle progression.
    """

    WORK_TIME = 25 * 60      # 25 minutes in seconds
    SHORT_BREAK = 5 * 60     # 5 minutes in seconds
    LONG_BREAK = 15 * 60     # 15 minutes in seconds
    SET_SIZE = 4             # 4 sprints per cycle set

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_complete_task: Optional[Callable[[int], None]] = None,
        on_edit_task: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_delete_task: Optional[Callable[[int], None]] = None,
    ) -> None:
        super().__init__(master)
        self.task = task
        self.on_complete_task = on_complete_task
        self.on_edit_task = on_edit_task
        self.on_delete_task = on_delete_task

        self.title("Prior - Pomodoro Focus Session")
        self.resizable(True, True)
        self.transient(master)

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        # Window protocol handlers and completion state tracking
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self._marked_completed = False
        self._sessions_cleaned_up = False

        # Determine target sprints based on estimated duration (accounting for 130m cycle with 15m long break)
        est_duration = int(self.task.get("estimated_duration") or 0)
        if est_duration > 0:
            self.total_target_sprints = calculate_recommended_sprints(est_duration)
        else:
            self.total_target_sprints = self.SET_SIZE

        # State Variables
        self.current_mode = "work"         # "work", "short_break", "long_break"
        self.sprint_count = 1              # 1 to total_target_sprints (current sprint index)
        self.completed_sprints_in_set = 0  # 0 to total_target_sprints (completed sprints)

        # Check existing completed sprints for this task from SQLite
        t_id = self.task.get("id")
        if t_id:
            try:
                task_sessions = database.get_pomodoro_sessions(task_id=t_id, session_type="work")
                # If target sprints were already reached previously, but task remains uncompleted,
                # the previous session was dismissed/canceled without marking complete.
                # Reset sessions for this task so it opens with a fresh start window (Sprint 1).
                if len(task_sessions) >= self.total_target_sprints and not bool(self.task.get("is_completed", 0)):
                    database.delete_pomodoro_sessions_for_task(t_id)
                    task_sessions = []
                    if hasattr(self.master, "_load_and_refresh"):
                        try:
                            self.master._load_and_refresh()
                        except Exception:
                            pass

                self.completed_sprints_in_set = min(len(task_sessions), self.total_target_sprints)
                if self.completed_sprints_in_set >= self.total_target_sprints:
                    self.sprint_count = self.total_target_sprints
                    self.current_mode = "long_break"
                else:
                    self.sprint_count = self.completed_sprints_in_set + 1
            except Exception:
                pass

        # Initialize today's completed sprints count from SQLite
        try:
            today_stats = database.get_daily_pomodoro_stats()
            self.completed_sprints_total = int(today_stats.get("sprints_count", 0))
        except Exception:
            self.completed_sprints_total = 0

        self.total_seconds = self.LONG_BREAK if self.current_mode == "long_break" else self.WORK_TIME
        self.remaining_seconds = self.total_seconds
        self.is_running = False
        self._timer_id: Optional[str] = None
        self.pill_buttons: List[ctk.CTkButton] = []
        self.runway_badge: Optional[ctk.CTkFrame] = None
        self.lbl_runway_main: Optional[ctk.CTkLabel] = None
        self.lbl_runway_sub: Optional[ctk.CTkLabel] = None
        self.badge_sprints: Optional[ctk.CTkFrame] = None
        self.badge_cycles: Optional[ctk.CTkFrame] = None

        self._center_modal(master)
        self._build_ui()
        self._update_theme_colors()
        self._update_display()
        self._update_cycle_tracker()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(540, max(490, screen_w - 40))
            h = min(500, max(460, screen_h - 70))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(480, 440)
        except Exception:
            self.geometry("520x480")
            self.minsize(480, 440)

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

        # Header row in task card: Target Tag + Action Buttons
        header_row = ctk.CTkFrame(inner_task, fg_color="transparent")
        header_row.pack(fill="x")

        lbl_target = ctk.CTkLabel(
            header_row,
            text="FOCUS TARGET",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color="#EF4444",
            anchor="w",
        )
        lbl_target.pack(side="left")

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
                command=self._on_delete_click,
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
                command=self._on_edit_click,
            )
            btn_edit.pack(side="right", padx=(0, 6) if self.on_delete_task else 0)

        # Title row: Task title on left + Sprints & Cycles badges on right
        title_row = ctk.CTkFrame(inner_task, fg_color="transparent")
        title_row.pack(fill="x", pady=(4, 0))

        task_title = self.task.get("title", "Prior Focus Task")
        lbl_title = ctk.CTkLabel(
            title_row,
            text=task_title,
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            justify="left",
        )
        lbl_title.pack(side="left", fill="x", expand=True)

        # Right stats container: Sprints done | Cycles done (clean inline presentation)
        stats_box = ctk.CTkFrame(title_row, fg_color="transparent")
        stats_box.pack(side="right")

        self.badge_sprints = None
        self.badge_cycles = None

        self.lbl_sprints_done = ctk.CTkLabel(
            stats_box,
            text=f"Sprints done: {self.completed_sprints_in_set}",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.lbl_sprints_done.pack(side="left")

        self.lbl_stats_divider = ctk.CTkLabel(
            stats_box,
            text="|",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
        )
        self.lbl_stats_divider.pack(side="left", padx=6)

        self.lbl_cycles_done = ctk.CTkLabel(
            stats_box,
            text=f"Cycles done: {self.completed_sprints_in_set // 4}",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.lbl_cycles_done.pack(side="left")

        # Description / Notes (if present)
        task_notes = (self.task.get("description") or self.task.get("notes") or "").strip()
        if task_notes:
            lbl_notes = ctk.CTkLabel(
                inner_task,
                text=task_notes,
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_SECONDARY,
                anchor="w",
                wraplength=450,
                justify="left",
            )
            lbl_notes.pack(fill="x", pady=(3, 0))

        # Estimated Runway / Focus Sprint Recommendation - STRICTLY ONLY FOR RED (Q1_DO) TASKS
        is_q1 = self.task.get("quadrant") == "Q1_DO"
        est_duration = int(self.task.get("estimated_duration") or 0)
        if is_q1 and est_duration > 0:
            if est_duration < 60:
                dur_phrase = f"{est_duration} mins"
            elif est_duration == 60:
                dur_phrase = "1 hour"
            elif est_duration % 60 == 0:
                dur_phrase = f"{est_duration // 60} hours"
            else:
                dur_phrase = f"{est_duration // 60}h {est_duration % 60}m"

            sprints = self.total_target_sprints
            cycles = sprints // 4
            extra = sprints % 4

            if cycles > 0 and extra > 0:
                cycle_str = "1 cycle" if cycles == 1 else f"{cycles} cycles"
                extra_str = "1 extra sprint" if extra == 1 else f"{extra} extra sprints"
                sprint_str = "1 sprint" if sprints == 1 else f"{sprints} sprints"
                sentence = f"⏱️ Estimated {dur_phrase}: You'll need {cycle_str} and {extra_str}, for a total of {sprint_str}."
            elif cycles > 0 and extra == 0:
                cycle_str = "1 cycle" if cycles == 1 else f"{cycles} cycles"
                sprint_str = "1 sprint" if sprints == 1 else f"{sprints} sprints"
                if cycles == 1:
                    sentence = f"⏱️ Estimated {dur_phrase}: You'll need 1 cycle of 4 sprints."
                else:
                    sentence = f"⏱️ Estimated {dur_phrase}: You'll need {cycle_str}, for a total of {sprint_str}."
            else:
                sprint_str = "1 sprint" if sprints == 1 else f"{sprints} sprints"
                sentence = f"⏱️ Estimated {dur_phrase}: You'll need {sprint_str}."

            self._runway_dur_phrase = dur_phrase
            self._runway_sentence = sentence
            self.runway_badge = None

            self.lbl_runway_main = ctk.CTkLabel(
                inner_task,
                text=sentence,
                font=(theme.FONT_FAMILY, 12),
                text_color=("#DC2626", "#F87171"),
                anchor="w",
                wraplength=460,
                justify="left",
            )
            self.lbl_runway_main.pack(fill="x", pady=(4, 0))
            self.lbl_runway_sub = None

        # 2. Mode Selector: Focus (25m) / Short Break (5m) / Long Break (15m)
        self.mode_segment = ctk.CTkSegmentedButton(
            container,
            values=["Focus (25m)", "Short Break (5m)", "Long Break (15m)"],
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=34,
            corner_radius=10,
            selected_color="#EF4444",
            selected_hover_color="#DC2626",
            command=self._on_mode_selected,
        )
        self.mode_segment.pack(fill="x", pady=(0, 14))
        self.mode_segment.set("Focus (25m)")

        # 4. Big Countdown Timer Display
        self.timer_frame = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=18,
            border_width=2,
            border_color="#EF4444",
            height=130,
        )
        self.timer_frame.pack(fill="x", pady=(0, 10))
        self.timer_frame.pack_propagate(False)

        self.lbl_stage_badge = ctk.CTkLabel(
            self.timer_frame,
            text=f"🍅 SPRINT {self.sprint_count} OF {self.total_target_sprints} • DEEP FOCUS",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=("#DC2626", "#F87171"),
        )
        self.lbl_stage_badge.place(relx=0.5, rely=0.18, anchor="center")

        self.lbl_timer = ctk.CTkLabel(
            self.timer_frame,
            text=format_timer_display(self.remaining_seconds),
            font=(theme.FONT_FAMILY, 56, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.lbl_timer.place(relx=0.5, rely=0.52, anchor="center")

        self.lbl_status = ctk.CTkLabel(
            self.timer_frame,
            text="Stay in the zone. Deep work in progress.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
        )
        self.lbl_status.place(relx=0.5, rely=0.84, anchor="center")

        # 5. Smooth Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            container,
            height=6,
            corner_radius=3,
            progress_color="#EF4444",
            fg_color=theme.BG_INPUT,
        )
        self.progress_bar.pack(fill="x", pady=(0, 14))
        self.progress_bar.set(1.0)

        # 6. Timer Action Controls (Start/Pause, Skip, Reset)
        ctrl_row = ctk.CTkFrame(container, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 12))

        self.btn_toggle = ctk.CTkButton(
            ctrl_row,
            text=f"▶  Start Sprint {self.sprint_count} (25m)",
            font=(theme.FONT_FAMILY, 14, "bold"),
            height=44,
            corner_radius=12,
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="#FFFFFF",
            command=self._toggle_timer,
        )
        self.btn_toggle.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_skip = ctk.CTkButton(
            ctrl_row,
            text="⏭ Skip",
            font=(theme.FONT_FAMILY, 13, "bold"),
            width=80,
            height=44,
            corner_radius=12,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._on_skip_stage,
        )
        self.btn_skip.pack(side="left", padx=(0, 8))

        btn_reset = ctk.CTkButton(
            ctrl_row,
            text="🔄 Reset",
            font=(theme.FONT_FAMILY, 13),
            width=80,
            height=44,
            corner_radius=12,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._reset_timer,
        )
        btn_reset.pack(side="right")

        # 7. Mark Task Done & Finish Button
        self.btn_complete = ctk.CTkButton(
            container,
            text="✓ Mark Task Completed & Finish",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=36,
            corner_radius=10,
            fg_color="transparent",
            hover_color=("#FEF2F2", "#2A0A0A"),
            text_color=("#EF4444", "#F87171"),
            border_width=1,
            border_color=("#EF4444", "#DC2626"),
            command=self._on_mark_completed,
        )
        self.btn_complete.pack(fill="x")

    def _update_cycle_tracker(self) -> None:
        """Updates sprint and cycle badges and today's session completed count."""
        if hasattr(self, "lbl_total_tally") and self.lbl_total_tally:
            try:
                self.lbl_total_tally.configure(text=f"Today: {self.completed_sprints_total} 🍅")
            except Exception:
                pass

        cycles_done = self.completed_sprints_in_set // 4
        sprints_done = self.completed_sprints_in_set
        is_target_completed = self.completed_sprints_in_set >= self.total_target_sprints

        # Green theme when target completed, otherwise red/secondary
        if is_target_completed:
            sprints_color = ("#059669", "#34D399")
            cycles_color = ("#059669", "#34D399")
            pill_border = ("#10B981", "#059669")
            pill_bg = ("#ECFDF5", "#042218")
        else:
            sprints_color = ("#EF4444", "#F87171") if sprints_done > 0 else theme.TEXT_SECONDARY
            cycles_color = ("#EF4444", "#F87171") if cycles_done > 0 else theme.TEXT_SECONDARY
            pill_border = theme.BORDER_COLOR
            pill_bg = theme.BG_CARD

        if hasattr(self, "lbl_sprints_done") and self.lbl_sprints_done:
            self.lbl_sprints_done.configure(
                text=f"Sprints done: {sprints_done}",
                text_color=sprints_color,
            )

        if hasattr(self, "lbl_cycles_done") and self.lbl_cycles_done:
            self.lbl_cycles_done.configure(
                text=f"Cycles done: {cycles_done}",
                text_color=cycles_color,
            )

        # Update runway sentence text color when target completed
        if hasattr(self, "lbl_runway_main") and self.lbl_runway_main:
            if is_target_completed:
                dur_txt = getattr(self, "_runway_dur_phrase", "")
                sprints_txt = "1 sprint" if self.total_target_sprints == 1 else f"{self.total_target_sprints} sprints"
                if dur_txt:
                    self.lbl_runway_main.configure(
                        text=f"🎉 Estimated {dur_txt} completed: All {sprints_txt} finished! Outstanding focus!",
                        text_color=("#059669", "#34D399"),
                    )
                else:
                    self.lbl_runway_main.configure(text_color=("#059669", "#34D399"))
            else:
                orig_sentence = getattr(self, "_runway_sentence", None)
                if orig_sentence:
                    self.lbl_runway_main.configure(text=orig_sentence, text_color=("#DC2626", "#F87171"))
                else:
                    self.lbl_runway_main.configure(text_color=("#DC2626", "#F87171"))

        if hasattr(self, "btn_skip") and self.btn_skip:
            if self.completed_sprints_in_set >= self.total_target_sprints:
                self.btn_skip.configure(state="disabled")
            else:
                self.btn_skip.configure(state="normal")

        if hasattr(self, "btn_complete") and self.btn_complete:
            if self.completed_sprints_in_set >= self.total_target_sprints:
                self.btn_complete.configure(
                    text="🏆 Congrats, You Did It! Mark Completed & Finish",
                    fg_color=("#10B981", "#059669"),
                    text_color="#FFFFFF",
                    hover_color=("#059669", "#047857"),
                    border_color=("#10B981", "#059669"),
                )
            else:
                self.btn_complete.configure(
                    text="✓ Mark Task Completed & Finish",
                    fg_color="transparent",
                    hover_color=("#FEF2F2", "#2A0A0A"),
                    text_color=("#EF4444", "#F87171"),
                    border_color=("#EF4444", "#DC2626"),
                )

        for idx, btn in enumerate(self.pill_buttons, start=1):
            if idx <= self.completed_sprints_in_set:
                # Completed sprint
                btn.configure(
                    text=f"✓ Sprint {idx}",
                    fg_color=("#FEF2F2", "#2B0B0B"),
                    hover_color=("#FEE2E2", "#3B0E0E"),
                    border_color=("#FCA5A5", "#7F1D1D"),
                    text_color=("#DC2626", "#F87171"),
                    border_width=1,
                )
            elif idx == self.sprint_count:
                if self.current_mode == "work":
                    # Currently active work sprint
                    btn.configure(
                        text=f"▶ Sprint {idx}",
                        fg_color=("#EF4444", "#DC2626"),
                        hover_color=("#DC2626", "#B91C1C"),
                        border_color=("#DC2626", "#EF4444"),
                        text_color="#FFFFFF",
                        border_width=1,
                    )
                elif self.current_mode == "short_break":
                    # Currently active short break
                    btn.configure(
                        text=f"☕ Break {idx}",
                        fg_color=("#ECFDF5", "#042218"),
                        hover_color=("#D1FAE5", "#063A2A"),
                        border_color=("#6EE7B7", "#065F46"),
                        text_color=("#059669", "#34D399"),
                        border_width=1,
                    )
                else:  # long_break
                    btn.configure(
                        text="🌴 Break",
                        fg_color=("#EEF2FF", "#1E1B4B"),
                        hover_color=("#E0E7FF", "#2E2A72"),
                        border_color=("#A5B4FC", "#3730A3"),
                        text_color=("#4F46E5", "#818CF8"),
                        border_width=1,
                    )
            else:
                # Pending future sprint
                btn.configure(
                    text=f"Sprint {idx}",
                    fg_color=theme.BG_CARD,
                    hover_color=theme.BG_CARD_HOVER,
                    border_color=theme.BORDER_COLOR,
                    text_color=theme.TEXT_MUTED,
                    border_width=1,
                )

    def _on_sprint_pill_click(self, sprint_idx: int) -> None:
        """Allows jumping directly to a chosen sprint in the cycle."""
        self.sprint_count = sprint_idx
        self.completed_sprints_in_set = sprint_idx - 1
        self._set_stage("work", status_msg=f"Selected Sprint {sprint_idx} of {self.total_target_sprints}.")

    def _update_theme_colors(self) -> None:
        """Dynamically styles timer frame, progress bar, and action buttons according to mode."""
        if self.current_mode == "work":
            accent = "#EF4444"
            hover = "#DC2626"
            badge_text = f"🍅 SPRINT {self.sprint_count} OF {self.total_target_sprints} • DEEP FOCUS"
            badge_color = ("#DC2626", "#F87171")
            start_btn_text = f"▶  Start Sprint {self.sprint_count} (25m)"
            self.mode_segment.configure(selected_color="#EF4444", selected_hover_color="#DC2626")
        elif self.current_mode == "short_break":
            accent = "#10B981"
            hover = "#059669"
            badge_text = "☕ SHORT BREAK • 5 MINUTES"
            badge_color = ("#059669", "#34D399")
            start_btn_text = "☕  Start Short Break (5m)"
            self.mode_segment.configure(selected_color="#10B981", selected_hover_color="#059669")
        else:  # long_break
            accent = "#6366F1"
            hover = "#4F46E5"
            if self.completed_sprints_in_set >= self.total_target_sprints:
                badge_text = "🎉 CONGRATS, YOU DID IT! • LONG BREAK (15M)"
                badge_color = ("#4F46E5", "#818CF8")
            else:
                badge_text = "🌴 LONG BREAK • 15 MINUTES"
                badge_color = ("#4F46E5", "#818CF8")
            start_btn_text = "🌴  Start Long Break (15m)"
            self.mode_segment.configure(selected_color="#6366F1", selected_hover_color="#4F46E5")

        self.timer_frame.configure(border_color=accent)
        self.progress_bar.configure(progress_color=accent)
        self.lbl_stage_badge.configure(text=badge_text, text_color=badge_color)

        # Disable skip button if all target sprints are completed
        if hasattr(self, "btn_skip") and self.btn_skip:
            if self.completed_sprints_in_set >= self.total_target_sprints:
                self.btn_skip.configure(state="disabled")
            else:
                self.btn_skip.configure(state="normal")

        if not self.is_running:
            self.btn_toggle.configure(
                text=start_btn_text,
                fg_color=accent,
                hover_color=hover,
            )
        else:
            self.btn_toggle.configure(
                text="⏸  Pause Session" if self.current_mode == "work" else "⏸  Pause Break",
                fg_color=accent,
                hover_color=hover,
            )

    def _on_mode_selected(self, value: str) -> None:
        """Handles manual mode changes via the segmented button."""
        if "Focus" in value:
            self._set_stage("work")
        elif "Short" in value:
            self._set_stage("short_break")
        else:
            self._set_stage("long_break")

    def _set_stage(self, mode: str, status_msg: Optional[str] = None) -> None:
        """Sets active stage, resets countdown duration, and updates UI state."""
        self._stop_timer_loop()
        self.is_running = False
        self.current_mode = mode

        if mode == "work":
            self.total_seconds = self.WORK_TIME
            self.remaining_seconds = self.WORK_TIME
            self.mode_segment.set("Focus (25m)")
            if not status_msg:
                status_msg = f"Sprint {self.sprint_count} of {self.total_target_sprints} • Stay in the zone."
        elif mode == "short_break":
            self.total_seconds = self.SHORT_BREAK
            self.remaining_seconds = self.SHORT_BREAK
            self.mode_segment.set("Short Break (5m)")
            if not status_msg:
                status_msg = "Take a breather. Step away, hydrate, and relax."
        else:  # long_break
            self.total_seconds = self.LONG_BREAK
            self.remaining_seconds = self.LONG_BREAK
            self.mode_segment.set("Long Break (15m)")
            if not status_msg:
                status_msg = "Step away from the screen for a full recharge."

        self.lbl_status.configure(text=status_msg)
        self._update_theme_colors()
        self._update_display()
        self._update_cycle_tracker()

    def _toggle_timer(self) -> None:
        if self.is_running:
            # Pause timer
            self.is_running = False
            self._stop_timer_loop()
            if self.current_mode == "work":
                self.btn_toggle.configure(text="▶  Resume Focus")
                self.lbl_status.configure(text="Paused. Ready when you are.")
            else:
                self.btn_toggle.configure(text="▶  Resume Break")
                self.lbl_status.configure(text="Break paused. Ready when you are.")
        else:
            # Start timer
            self.is_running = True
            if self.current_mode == "work":
                self.btn_toggle.configure(text="⏸  Pause Session")
                self.lbl_status.configure(text=f"Focus active: Sprint {self.sprint_count} of {self.total_target_sprints}. Keep going!")
            else:
                self.btn_toggle.configure(text="⏸  Pause Break")
                self.lbl_status.configure(text="Rest and recharge. Step away from your desk.")
            self._tick()

        self._update_cycle_tracker()

    def _tick(self) -> None:
        if not self.is_running:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            self._timer_id = self.after(1000, self._tick)
        else:
            # Stage finished!
            self.is_running = False
            self._stop_timer_loop()

            stage_info = calculate_pomodoro_stage(
                completed_sprints=self.completed_sprints_in_set,
                current_mode=self.current_mode,
                set_size=self.SET_SIZE,
                total_target_sprints=self.total_target_sprints,
            )

            task_title = (self.task.get("title") or "Prior Focus Task").strip()

            if self.current_mode == "work":
                self.completed_sprints_total += 1
                # Persist completed sprint to SQLite database
                try:
                    task_id = self.task.get("id")
                    database.log_pomodoro_session(
                        task_id=task_id,
                        duration_minutes=round(self.WORK_TIME / 60),
                        session_type="work",
                    )
                except Exception:
                    pass

                self.completed_sprints_in_set += 1
                new_completed = self.completed_sprints_in_set

                if stage_info["is_set_completed"]:
                    set_num = new_completed // self.SET_SIZE
                    if new_completed < self.total_target_sprints:
                        self.sprint_count = new_completed + 1
                        status_text = f"🏆 Sprint {new_completed} finished! You completed Set {set_num}. Enjoy a 15-minute Long Break!"
                        notify_title = f"🏆 Set {set_num} Completed ({new_completed} Sprints)!"
                        notify_msg = f"Outstanding work on \"{task_title}\"! Take a 15-minute Long Break."
                    else:
                        self.sprint_count = self.total_target_sprints
                        status_text = f"🎉 Congrats, you did it! All {self.total_target_sprints} sprints completed! Enjoy your well-deserved 15-minute Long Break! 🏆"
                        notify_title = f"🎉 Congrats, You Did It! All {self.total_target_sprints} Sprints Completed!"
                        notify_msg = f"Outstanding work on \"{task_title}\"! Target achieved. Enjoy your 15-minute Long Break."
                    self._set_stage("long_break", status_msg=status_text)
                    self._notify_stage_completion(
                        title=notify_title,
                        message=notify_msg,
                        sound_type="set_completed",
                    )
                else:
                    self.sprint_count = min(new_completed + 1, self.total_target_sprints)
                    status_text = f"🎉 Sprint {new_completed} finished! Take a 5-minute breather."
                    self._set_stage("short_break", status_msg=status_text)
                    self._notify_stage_completion(
                        title=f"🍅 Sprint {new_completed} Completed!",
                        message=f"Great focus on \"{task_title}\"! Time for a 5-minute breather.",
                        sound_type="work_done",
                    )
            elif self.current_mode == "short_break":
                status_text = f"⚡ Break finished! Ready for Sprint {self.sprint_count} of {self.total_target_sprints}."
                self._set_stage("work", status_msg=status_text)
                self._notify_stage_completion(
                    title="⚡ Short Break Finished!",
                    message=f"Recharged? Time to dive into Sprint {self.sprint_count} of {self.total_target_sprints}.",
                    sound_type="break_done",
                )
            else:  # long_break
                if self.sprint_count < self.total_target_sprints and self.completed_sprints_in_set < self.total_target_sprints:
                    status_text = f"✨ Fully recharged! Ready to start Sprint {self.sprint_count} of {self.total_target_sprints}."
                    self._set_stage("work", status_msg=status_text)
                    self._notify_stage_completion(
                        title="✨ Long Break Finished!",
                        message=f"Fully recharged! Ready to start Sprint {self.sprint_count} on \"{task_title}\".",
                        sound_type="break_done",
                    )
                else:
                    self._mark_target_completed_celebration()

    def _mark_target_completed_celebration(self) -> None:
        """Celebrates full session target completion and prompts marking task done."""
        self._stop_timer_loop()
        self.is_running = False
        self.remaining_seconds = 0
        self._update_display()

        task_title = (self.task.get("title") or "Prior Focus Task").strip()
        celebrate_status = f"🎉 Congrats, you did it! All {self.total_target_sprints} sprints completed! Outstanding work on \"{task_title}\"! 🏆"
        self.lbl_status.configure(text=celebrate_status)
        self.lbl_stage_badge.configure(
            text="🏆 TARGET COMPLETED • CONGRATS, YOU DID IT!",
            text_color=("#10B981", "#34D399"),
        )
        self.timer_frame.configure(border_color="#10B981")
        self.progress_bar.configure(progress_color="#10B981")
        self.progress_bar.set(1.0)
        self.btn_toggle.configure(
            text="🏆 Target Achieved!",
            state="disabled",
            fg_color="#10B981",
            hover_color="#059669",
        )
        self.btn_skip.configure(state="disabled")

        if hasattr(self, "btn_complete") and self.btn_complete:
            self.btn_complete.configure(
                text="🏆 Congrats, You Did It! Mark Completed & Finish",
                fg_color=("#10B981", "#059669"),
                text_color="#FFFFFF",
                hover_color=("#059669", "#047857"),
                border_color=("#10B981", "#059669"),
            )

        self._notify_stage_completion(
            title="🏆 Target Completed! Congrats, You Did It!",
            message=f"Outstanding focus on \"{task_title}\"! All {self.total_target_sprints} sprints finished.",
            sound_type="set_completed",
        )

    def _on_skip_stage(self) -> None:
        """Skips the active sprint or break to advance immediately to the next stage."""
        if self.completed_sprints_in_set >= self.total_target_sprints:
            return  # Target already finished; do not roll back to Sprint 1

        self._stop_timer_loop()
        self.is_running = False

        stage_info = calculate_pomodoro_stage(
            completed_sprints=self.completed_sprints_in_set,
            current_mode=self.current_mode,
            set_size=self.SET_SIZE,
            total_target_sprints=self.total_target_sprints,
        )

        if self.current_mode == "work":
            self.completed_sprints_total += 1
            # Persist completed sprint to SQLite database
            try:
                task_id = self.task.get("id")
                database.log_pomodoro_session(
                    task_id=task_id,
                    duration_minutes=round(self.WORK_TIME / 60),
                    session_type="work",
                )
            except Exception:
                pass

            self.completed_sprints_in_set += 1
            new_completed = self.completed_sprints_in_set
            if stage_info["is_set_completed"]:
                if new_completed < self.total_target_sprints:
                    self.sprint_count = new_completed + 1
                    status_text = f"Skipped to Long Break (15m) after Sprint {new_completed}."
                else:
                    self.sprint_count = self.total_target_sprints
                    status_text = f"🎉 Congrats, you did it! All {self.total_target_sprints} sprints completed! Enjoy your well-deserved Long Break! 🏆"
                self._set_stage("long_break", status_msg=status_text)
            else:
                self.sprint_count = min(new_completed + 1, self.total_target_sprints)
                self._set_stage("short_break", status_msg=f"Skipped to Short Break (after Sprint {new_completed}).")
        elif self.current_mode == "short_break":
            self._set_stage("work", status_msg=f"Skipped break. Ready for Sprint {self.sprint_count} of {self.total_target_sprints}.")
        else:  # long_break
            if self.completed_sprints_in_set < self.total_target_sprints:
                self._set_stage("work", status_msg=f"Skipped long break. Ready for Sprint {self.sprint_count} of {self.total_target_sprints}.")
            else:
                return

    def _update_display(self) -> None:
        self.lbl_timer.configure(text=format_timer_display(self.remaining_seconds))
        fraction = self.remaining_seconds / self.total_seconds if self.total_seconds > 0 else 0.0
        self.progress_bar.set(fraction)

    def _reset_timer(self) -> None:
        self._stop_timer_loop()
        self.is_running = False
        self.remaining_seconds = self.total_seconds
        self._update_theme_colors()
        self._update_display()
        self._update_cycle_tracker()

    def _stop_timer_loop(self) -> None:
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _notify_stage_completion(self, title: str, message: str, sound_type: str = "work_done") -> None:
        """Dispatches an acoustic chime, native Windows desktop notification, and taskbar pulse."""
        # 1. Play acoustic chime in background thread
        self._play_acoustic_chime(sound_type)

        # 2. Flash Windows taskbar icon
        if hasattr(self.master, "flash_window"):
            try:
                self.master.flash_window()
            except Exception:
                pass

        # 3. Deliver desktop notification (toast / tray balloon)
        if hasattr(self.master, "notify_desktop"):
            try:
                self.master.notify_desktop(title, message)
            except Exception:
                pass
        elif hasattr(self.master, "_queue_desktop_notification"):
            try:
                self.master._queue_desktop_notification(title, message)
            except Exception:
                pass

    def _play_acoustic_chime(self, sound_type: str = "work_done") -> None:
        """Plays melodious chimes using winsound on Windows without blocking the GUI."""
        def _sound_worker() -> None:
            try:
                if sys.platform == "win32":
                    import winsound
                    if sound_type == "set_completed":
                        # C5, E5, G5, C6 triumphant ascending fanfare
                        for freq, dur in [(523, 100), (659, 100), (784, 100), (1046, 260)]:
                            winsound.Beep(freq, dur)
                    elif sound_type == "work_done":
                        # E5, A5, C#6 crisp upbeat completion chime
                        for freq, dur in [(659, 110), (880, 110), (1108, 220)]:
                            winsound.Beep(freq, dur)
                    else:  # break_done
                        # A4, E5 gentle two-tone wake-up chime
                        for freq, dur in [(440, 130), (659, 220)]:
                            winsound.Beep(freq, dur)
                else:
                    self.bell()
            except Exception:
                try:
                    self.bell()
                except Exception:
                    pass

        threading.Thread(target=_sound_worker, daemon=True).start()

    def _play_bell_notification(self) -> None:
        """Fallback bell notification."""
        self._play_acoustic_chime("work_done")

    def _on_edit_click(self) -> None:
        self._stop_timer_loop()
        task_data = self.task
        edit_callback = self.on_edit_task
        self.destroy()
        if edit_callback:
            edit_callback(task_data)

    def _on_mark_completed(self) -> None:
        self._marked_completed = True
        self._stop_timer_loop()
        if self.on_complete_task and "id" in self.task:
            self.on_complete_task(self.task["id"])
        self.destroy()

    def _on_delete_click(self) -> None:
        self._stop_timer_loop()
        task_id = self.task.get("id")
        delete_callback = self.on_delete_task
        self.destroy()
        if delete_callback and task_id:
            delete_callback(task_id)

    def _on_window_close(self) -> None:
        """Handler for window close button (✕ / Alt+F4)."""
        self._cleanup_uncompleted_target_sessions()
        self.destroy()

    def _cleanup_uncompleted_target_sessions(self) -> None:
        """
        If the modal is closed without marking the task completed after reaching
        the target sprint count, reset this task's logged sessions in SQLite so
        subsequent opens start cleanly at Sprint 1 instead of showing congratulations again.
        """
        if getattr(self, "_sessions_cleaned_up", False):
            return
        self._sessions_cleaned_up = True
        t_id = self.task.get("id")
        if t_id and not getattr(self, "_marked_completed", False):
            if self.completed_sprints_in_set >= self.total_target_sprints:
                try:
                    current_task = database.get_task_by_id(t_id)
                    if not current_task or not bool(current_task.get("is_completed", 0)):
                        database.delete_pomodoro_sessions_for_task(t_id)
                except Exception:
                    pass
                if hasattr(self.master, "_load_and_refresh"):
                    try:
                        self.master._load_and_refresh()
                    except Exception:
                        pass

    def destroy(self) -> None:
        self._stop_timer_loop()
        self._cleanup_uncompleted_target_sessions()
        try:
            if hasattr(self.master, "active_pomodoro_modal") and self.master.active_pomodoro_modal is self:
                self.master.active_pomodoro_modal = None
        except Exception:
            pass
        super().destroy()
