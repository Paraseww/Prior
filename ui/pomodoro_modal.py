"""
ui/pomodoro_modal.py
Interactive Pomodoro Focus Timer modal dialog for Prior.
Enables dedicated deep-work sessions (25m work / 5m break) on tasks with live countdown and progress.
"""

from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from project import format_timer_display
from ui import theme


class PomodoroModal(ctk.CTkToplevel):
    """
    Pomodoro Focus Timer window for a selected task.
    """

    WORK_TIME = 25 * 60      # 25 minutes in seconds
    SHORT_BREAK = 5 * 60     # 5 minutes in seconds
    LONG_BREAK = 15 * 60     # 15 minutes in seconds

    def __init__(
        self,
        master: Any,
        task: Dict[str, Any],
        on_complete_task: Optional[Callable[[int], None]] = None,
        on_edit_task: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__(master)
        self.task = task
        self.on_complete_task = on_complete_task
        self.on_edit_task = on_edit_task

        self.title("Prior — Pomodoro Focus Session")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # State Variables
        self.current_mode = "work"  # "work", "short_break", "long_break"
        self.total_seconds = self.WORK_TIME
        self.remaining_seconds = self.WORK_TIME
        self.is_running = False
        self._timer_id: Optional[str] = None

        self._center_modal(master)
        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() - 480) // 2
            y = master.winfo_y() + (master.winfo_height() - 520) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=25)

        # 1. Target Task Header Card
        task_box = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        task_box.pack(fill="x", pady=(0, 20))

        inner_task = ctk.CTkFrame(task_box, fg_color="transparent")
        inner_task.pack(fill="x", padx=14, pady=10)

        # Header row in task card: Target Tag + Edit Button
        header_row = ctk.CTkFrame(inner_task, fg_color="transparent")
        header_row.pack(fill="x")

        lbl_target = ctk.CTkLabel(
            header_row,
            text="🎯 CURRENT FOCUS TARGET",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.ACCENT_PRIMARY,
            anchor="w",
        )
        lbl_target.pack(side="left")

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
        btn_edit.pack(side="right")

        task_title = self.task.get("title", "Prior Focus Task")
        lbl_title = ctk.CTkLabel(
            inner_task,
            text=task_title,
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            wraplength=380,
            justify="left",
        )
        lbl_title.pack(fill="x", pady=(4, 0))

        # 2. Mode Selector: Focus (25m) / Short Break (5m) / Long Break (15m)
        self.mode_segment = ctk.CTkSegmentedButton(
            container,
            values=["Focus (25m)", "Short Break (5m)", "Long Break (15m)"],
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=36,
            corner_radius=10,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_HOVER,
            command=self._on_mode_selected,
        )
        self.mode_segment.pack(fill="x", pady=(0, 25))
        self.mode_segment.set("Focus (25m)")

        # 3. Big Countdown Timer Display
        timer_frame = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=20,
            border_width=2,
            border_color=theme.ACCENT_PRIMARY,
            height=140,
        )
        timer_frame.pack(fill="x", pady=(0, 15))
        timer_frame.pack_propagate(False)

        self.lbl_timer = ctk.CTkLabel(
            timer_frame,
            text=format_timer_display(self.remaining_seconds),
            font=(theme.FONT_FAMILY, 62, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.lbl_timer.place(relx=0.5, rely=0.42, anchor="center")

        self.lbl_status = ctk.CTkLabel(
            timer_frame,
            text="Stay in the zone. Deep work in progress.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
        )
        self.lbl_status.place(relx=0.5, rely=0.82, anchor="center")

        # 4. Smooth Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            container,
            height=8,
            corner_radius=4,
            progress_color=theme.ACCENT_PRIMARY,
            fg_color=theme.BG_INPUT,
        )
        self.progress_bar.pack(fill="x", pady=(0, 25))
        self.progress_bar.set(1.0)

        # 5. Timer Action Controls
        ctrl_row = ctk.CTkFrame(container, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 15))

        self.btn_toggle = ctk.CTkButton(
            ctrl_row,
            text="▶  Start Focus",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=46,
            corner_radius=12,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._toggle_timer,
        )
        self.btn_toggle.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_reset = ctk.CTkButton(
            ctrl_row,
            text="🔄 Reset",
            font=(theme.FONT_FAMILY, 14),
            width=100,
            height=46,
            corner_radius=12,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._reset_timer,
        )
        btn_reset.pack(side="right")

        # 6. Mark Task Done & Finish Button
        btn_complete = ctk.CTkButton(
            container,
            text="✓ Mark Task Completed & Finish",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=36,
            corner_radius=10,
            fg_color="transparent",
            hover_color=("#ECFDF5", "#064E3B"),
            text_color=("#10B981", "#34D399"),
            border_width=1,
            border_color=("#10B981", "#059669"),
            command=self._on_mark_completed,
        )
        btn_complete.pack(fill="x")

    def _on_mode_selected(self, value: str) -> None:
        self._stop_timer_loop()
        self.is_running = False
        self.btn_toggle.configure(text="▶  Start Focus")

        if "Focus" in value:
            self.current_mode = "work"
            self.total_seconds = self.WORK_TIME
            self.lbl_status.configure(text="Stay in the zone. Deep work in progress.")
        elif "Short" in value:
            self.current_mode = "short_break"
            self.total_seconds = self.SHORT_BREAK
            self.lbl_status.configure(text="Take a breather. Grab a glass of water.")
        else:
            self.current_mode = "long_break"
            self.total_seconds = self.LONG_BREAK
            self.lbl_status.configure(text="Step away from the screen for a full recharge.")

        self.remaining_seconds = self.total_seconds
        self._update_display()

    def _toggle_timer(self) -> None:
        if self.is_running:
            # Pause timer
            self.is_running = False
            self._stop_timer_loop()
            self.btn_toggle.configure(text="▶  Resume Focus")
            self.lbl_status.configure(text="Paused. Ready when you are.")
        else:
            # Start timer
            self.is_running = True
            self.btn_toggle.configure(text="⏸  Pause Session")
            self.lbl_status.configure(text="Focus mode active. Keep going!")
            self._tick()

    def _tick(self) -> None:
        if not self.is_running:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            self._timer_id = self.after(1000, self._tick)
        else:
            # Timer reached zero
            self.is_running = False
            self.btn_toggle.configure(text="▶  Start Next")
            self.lbl_status.configure(text="🎉 Session finished! Well done!")
            self._play_bell_notification()

    def _update_display(self) -> None:
        self.lbl_timer.configure(text=format_timer_display(self.remaining_seconds))
        fraction = self.remaining_seconds / self.total_seconds if self.total_seconds > 0 else 0.0
        self.progress_bar.set(fraction)

    def _reset_timer(self) -> None:
        self._stop_timer_loop()
        self.is_running = False
        self.remaining_seconds = self.total_seconds
        self.btn_toggle.configure(text="▶  Start Focus")
        self._update_display()

    def _stop_timer_loop(self) -> None:
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _play_bell_notification(self) -> None:
        try:
            self.bell()
        except Exception:
            pass

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

    def destroy(self) -> None:
        self._stop_timer_loop()
        super().destroy()
