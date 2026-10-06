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

from project import calculate_pomodoro_stage, format_timer_display
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

        # State Variables
        self.current_mode = "work"         # "work", "short_break", "long_break"
        self.sprint_count = 1              # 1 to SET_SIZE (current sprint in set)
        self.completed_sprints_in_set = 0  # 0 to SET_SIZE
        self.completed_sprints_total = 0   # Total completed in this session
        self.total_seconds = self.WORK_TIME
        self.remaining_seconds = self.WORK_TIME
        self.is_running = False
        self._timer_id: Optional[str] = None
        self.pill_buttons: List[ctk.CTkButton] = []

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

            w = min(560, max(490, screen_w - 40))
            h = min(620, max(520, screen_h - 70))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(480, 500)
        except Exception:
            self.geometry("540x600")
            self.minsize(480, 500)

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
            text="🎯 FOCUS TARGET",
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

        task_title = self.task.get("title", "Prior Focus Task")
        lbl_title = ctk.CTkLabel(
            inner_task,
            text=task_title,
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            wraplength=450,
            justify="left",
        )
        lbl_title.pack(fill="x", pady=(4, 0))

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

        # Estimated Runway / Focus Sprint Recommendation - STRICTLY FOR Q1 (Red Box)
        est_duration = int(self.task.get("estimated_duration") or 0)
        is_q1 = self.task.get("quadrant") == "Q1_DO"
        if is_q1 and est_duration > 0:
            if est_duration < 60:
                dur_phrase = f"{est_duration} mins"
            elif est_duration == 60:
                dur_phrase = "1 hour"
            elif est_duration % 60 == 0:
                dur_phrase = f"{est_duration // 60} hours"
            else:
                dur_phrase = f"{est_duration // 60}h {est_duration % 60}m"
            sprints = max(1, round(est_duration / 25))
            runway_badge = ctk.CTkFrame(
                inner_task,
                fg_color=("#FEF2F2", "#2B0B0B"),
                corner_radius=6,
                border_width=1,
                border_color=("#FCA5A5", "#7F1D1D"),
            )
            runway_badge.pack(anchor="w", pady=(6, 2))
            ctk.CTkLabel(
                runway_badge,
                text=f"⏱️ {dur_phrase} needed: Recommended {sprints} × 25m sprints with breaks.",
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=("#DC2626", "#F87171"),
            ).pack(padx=8, pady=4)

        # 2. Cycle Progress Tracker Card
        cycle_box = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        cycle_box.pack(fill="x", pady=(0, 12))

        inner_cycle = ctk.CTkFrame(cycle_box, fg_color="transparent")
        inner_cycle.pack(fill="x", padx=14, pady=10)

        cycle_head = ctk.CTkFrame(inner_cycle, fg_color="transparent")
        cycle_head.pack(fill="x", pady=(0, 8))

        lbl_cycle_title = ctk.CTkLabel(
            cycle_head,
            text="🍅 4-STAGE POMODORO CYCLE",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_cycle_title.pack(side="left")

        self.lbl_total_tally = ctk.CTkLabel(
            cycle_head,
            text=f"Total Done: {self.completed_sprints_total} 🍅",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="e",
        )
        self.lbl_total_tally.pack(side="right")

        # Pills Row (Sprint 1 .. 4) using equal-width uniform grid
        pills_row = ctk.CTkFrame(inner_cycle, fg_color="transparent")
        pills_row.pack(fill="x")
        for col in range(self.SET_SIZE):
            pills_row.grid_columnconfigure(col, weight=1, uniform="sprint_pill")

        self.pill_buttons.clear()
        for i in range(1, self.SET_SIZE + 1):
            btn = ctk.CTkButton(
                pills_row,
                text=f"Sprint {i}",
                font=(theme.FONT_FAMILY, 11, "bold"),
                height=32,
                width=0,
                corner_radius=8,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_MUTED,
                command=lambda idx=i: self._on_sprint_pill_click(idx),
            )
            btn.grid(row=0, column=i - 1, sticky="ew", padx=3)
            self.pill_buttons.append(btn)

        # 3. Mode Selector: Focus (25m) / Short Break (5m) / Long Break (15m)
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
            text=f"🍅 SPRINT {self.sprint_count} OF {self.SET_SIZE} • DEEP FOCUS",
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
        btn_complete = ctk.CTkButton(
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
        btn_complete.pack(fill="x")

    def _update_cycle_tracker(self) -> None:
        """Updates the 4-stage pill buttons and total session completed count."""
        self.lbl_total_tally.configure(text=f"Total Done: {self.completed_sprints_total} 🍅")

        for idx, btn in enumerate(self.pill_buttons, start=1):
            if idx <= self.completed_sprints_in_set:
                # Completed sprint in current set
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
                else:
                    # Currently active break stage
                    if self.current_mode == "short_break":
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
        """Allows jumping directly to a chosen sprint in the 4-stage cycle."""
        self.sprint_count = sprint_idx
        self._set_stage("work", status_msg=f"Selected Sprint {sprint_idx} of {self.SET_SIZE}.")

    def _update_theme_colors(self) -> None:
        """Dynamically styles timer frame, progress bar, and action buttons according to mode."""
        if self.current_mode == "work":
            accent = "#EF4444"
            hover = "#DC2626"
            badge_text = f"🍅 SPRINT {self.sprint_count} OF {self.SET_SIZE} • DEEP FOCUS"
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
            badge_text = "🌴 LONG BREAK • 15 MINUTES"
            badge_color = ("#4F46E5", "#818CF8")
            start_btn_text = "🌴  Start Long Break (15m)"
            self.mode_segment.configure(selected_color="#6366F1", selected_hover_color="#4F46E5")

        self.timer_frame.configure(border_color=accent)
        self.progress_bar.configure(progress_color=accent)
        self.lbl_stage_badge.configure(text=badge_text, text_color=badge_color)

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
                status_msg = f"Sprint {self.sprint_count} of {self.SET_SIZE} • Stay in the zone."
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
                self.lbl_status.configure(text=f"Focus active: Sprint {self.sprint_count} of {self.SET_SIZE}. Keep going!")
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
            )

            task_title = (self.task.get("title") or "Prior Focus Task").strip()

            if self.current_mode == "work":
                self.completed_sprints_total += 1
                if stage_info["is_set_completed"]:
                    self.completed_sprints_in_set = 0
                    self.sprint_count = 1
                    status_text = "🏆 4 Sprints finished! You completed a full set. Enjoy a 15-minute Long Break!"
                    self._set_stage("long_break", status_msg=status_text)
                    self._notify_stage_completion(
                        title="🏆 4 Sprints Completed! Full Set Finished!",
                        message=f"Outstanding work on \"{task_title}\"! Take a 15-minute Long Break.",
                        sound_type="set_completed",
                    )
                else:
                    self.completed_sprints_in_set += 1
                    self.sprint_count = self.completed_sprints_in_set + 1
                    status_text = f"🎉 Sprint {self.completed_sprints_in_set} finished! Take a 5-minute breather."
                    self._set_stage("short_break", status_msg=status_text)
                    self._notify_stage_completion(
                        title=f"🍅 Sprint {self.completed_sprints_in_set} Completed!",
                        message=f"Great focus on \"{task_title}\"! Time for a 5-minute breather.",
                        sound_type="work_done",
                    )
            elif self.current_mode == "short_break":
                status_text = f"⚡ Break finished! Ready for Sprint {self.sprint_count} of {self.SET_SIZE}."
                self._set_stage("work", status_msg=status_text)
                self._notify_stage_completion(
                    title="⚡ Short Break Finished!",
                    message=f"Recharged? Time to dive into Sprint {self.sprint_count} of {self.SET_SIZE}.",
                    sound_type="break_done",
                )
            else:  # long_break
                self.sprint_count = 1
                self.completed_sprints_in_set = 0
                status_text = f"✨ Fully recharged! Ready to start Set 2 (Sprint 1 of {self.SET_SIZE})."
                self._set_stage("work", status_msg=status_text)
                self._notify_stage_completion(
                    title="✨ Long Break Finished!",
                    message=f"Fully recharged! Ready to start Sprint 1 on \"{task_title}\".",
                    sound_type="break_done",
                )

    def _on_skip_stage(self) -> None:
        """Skips the active sprint or break to advance immediately to the next stage."""
        self._stop_timer_loop()
        self.is_running = False

        stage_info = calculate_pomodoro_stage(
            completed_sprints=self.completed_sprints_in_set,
            current_mode=self.current_mode,
            set_size=self.SET_SIZE,
        )

        if self.current_mode == "work":
            self.completed_sprints_total += 1
            if stage_info["is_set_completed"]:
                self.completed_sprints_in_set = 0
                self.sprint_count = 1
                self._set_stage("long_break", status_msg="Skipped to Long Break (15m).")
            else:
                self.completed_sprints_in_set += 1
                self.sprint_count = self.completed_sprints_in_set + 1
                self._set_stage("short_break", status_msg=f"Skipped to Short Break (after Sprint {self.completed_sprints_in_set}).")
        elif self.current_mode == "short_break":
            self._set_stage("work", status_msg=f"Skipped break. Ready for Sprint {self.sprint_count} of {self.SET_SIZE}.")
        else:  # long_break
            self.sprint_count = 1
            self.completed_sprints_in_set = 0
            self._set_stage("work", status_msg=f"Skipped long break. Ready for Sprint 1 of {self.SET_SIZE}.")

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

    def destroy(self) -> None:
        self._stop_timer_loop()
        try:
            if hasattr(self.master, "active_pomodoro_modal") and self.master.active_pomodoro_modal is self:
                self.master.active_pomodoro_modal = None
        except Exception:
            pass
        super().destroy()
