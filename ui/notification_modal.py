"""
ui/notification_modal.py
Notification & Task Reminder Flyout Modal for Prior.
Displays categorized reminders for delayed/overdue tasks, tasks due today,
tasks due tomorrow, and upcoming deadlines within the next 2-3 days.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import customtkinter as ctk

from project import get_task_notifications
from ui import theme
from ui.smooth_scroll import SmoothScrollableFrame


class NotificationModal(ctk.CTkToplevel):
    """
    Dedicated Flyout Modal for Task Notifications and Reminders.
    """

    def __init__(
        self,
        master: Any,
        tasks: List[Dict[str, Any]],
        on_toggle: Callable[[int], None],
        on_edit: Callable[[Dict[str, Any]], None],
        on_schedule: Callable[[Dict[str, Any]], None],
        on_refresh: Optional[Callable[[], None]] = None,
        on_focus: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=theme.BG_CARD)

        # Immediately withdraw to prevent any white flash / blink during construction
        self.withdraw()

        # Set native Tk window background to theme color (kills OS white flash)
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg_hex = theme.BG_CARD[1] if is_dark else theme.BG_CARD[0]
        try:
            self.config(background=bg_hex)
        except Exception:
            pass

        self.tasks = tasks
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_schedule = on_schedule
        self.on_refresh = on_refresh
        self.on_focus = on_focus
        if hasattr(master, "dismissed_notification_ids"):
            self.dismissed_task_ids: Set[int] = master.dismissed_notification_ids
        else:
            self.dismissed_task_ids: Set[int] = set()

        self.title("Prior - Task Reminders & Notifications")

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        # Position and size modal centered relative to master without premature painting
        self._position_modal(master)

        # Build full UI content while window is hidden
        self._build_ui()

        # Reveal smoothly once completely painted and dark-themed
        self.after(20, self._reveal_modal)

    def _position_modal(self, master: Any) -> None:
        """Positions and sizes the modal relative to parent window and screen bounds."""
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(540, max(440, screen_w - 40))
            h = min(660, max(440, screen_h - 90))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            # Clamp coordinates to ensure modal is fully within visible screen area
            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(min(440, w), min(420, h))
        except Exception:
            self.geometry("540x660")

    def _reveal_modal(self) -> None:
        """Reveals the fully constructed modal smoothly and takes focus."""
        try:
            if not self.winfo_exists():
                return
            self.deiconify()
            self.transient(self.master)
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.configure(fg_color=theme.BG_CARD)

        # Clear existing children if re-rendering
        for child in self.winfo_children():
            child.destroy()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=22, pady=18)

        # Filter out dismissed tasks
        visible_tasks = [t for t in self.tasks if t.get("id") not in self.dismissed_task_ids]

        # Calculate notification buckets
        notifications = get_task_notifications(visible_tasks)
        total_count = notifications["total_count"]

        # ====================================================================
        # 1. Header Bar
        # ====================================================================
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(side="left", fill="x", expand=True)

        lbl_icon = ctk.CTkLabel(
            title_row,
            text="🔔",
            font=(theme.FONT_FAMILY, 20),
        )
        lbl_icon.pack(side="left", padx=(0, 8))

        lbl_title = ctk.CTkLabel(
            title_row,
            text="Reminders & Alerts",
            font=(theme.FONT_DISPLAY, 18, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_title.pack(side="left", padx=(0, 10))

        # Status badge
        if total_count > 0:
            badge_text = f"{total_count} Need Attention"
            if notifications["overdue_count"] > 0:
                badge_fg = ("#FEF2F2", "#2A0A0A")
                badge_border = ("#FCA5A5", "#7F1D1D")
                badge_text_col = ("#DC2626", "#F87171")
            else:
                badge_fg = ("#FFFBEB", "#261603")
                badge_border = ("#FDE68A", "#78350F")
                badge_text_col = ("#D97706", "#FBBF24")
        else:
            badge_text = "All Clear"
            badge_fg = ("#ECFDF5", "#042218")
            badge_border = ("#A7F3D0", "#064E3B")
            badge_text_col = ("#059669", "#34D399")

        badge_frame = ctk.CTkFrame(
            title_row,
            fg_color=badge_fg,
            corner_radius=12,
            border_width=1,
            border_color=badge_border,
            height=24,
        )
        badge_frame.pack(side="left")
        lbl_badge = ctk.CTkLabel(
            badge_frame,
            text=badge_text,
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=badge_text_col,
        )
        lbl_badge.pack(padx=8, pady=2)

        # Action button at header right: "Clear all notifications"
        if total_count > 0:
            btn_clear_all = ctk.CTkButton(
                header,
                text="Clear all notifications",
                font=(theme.FONT_FAMILY, 11, "bold"),
                height=26,
                corner_radius=6,
                fg_color="transparent",
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_SECONDARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=self._clear_all_notifications,
            )
            btn_clear_all.pack(side="right")

        # ====================================================================
        # 2. Main Scrollable Content Area
        # ====================================================================
        if total_count == 0:
            self._render_empty_state(container)
        else:
            scroll_frame = SmoothScrollableFrame(
                container,
                fg_color="transparent",
                corner_radius=0,
            )
            scroll_frame.pack(fill="both", expand=True, pady=(0, 8))

            # ⚠️ Section 1: Delayed & Overdue Tasks (Top priority)
            if notifications["overdue_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="Delayed & Overdue",
                    icon="⚠️",
                    count=notifications["overdue_count"],
                    title_color=("#DC2626", "#F87171"),
                    tasks=notifications["overdue"],
                    category_type="overdue",
                )

            # ⏰ Section 2: Due Today
            if notifications["today_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="Due Today",
                    icon="⏰",
                    count=notifications["today_count"],
                    title_color=("#D97706", "#FBBF24"),
                    tasks=notifications["today"],
                    category_type="today",
                )

            # ⏳ Section 3: Due Tomorrow
            if notifications["tomorrow_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="Due Tomorrow",
                    icon="⏳",
                    count=notifications["tomorrow_count"],
                    title_color=("#2563EB", "#60A5FA"),
                    tasks=notifications["tomorrow"],
                    category_type="tomorrow",
                )

            # 🗓 Section 4: Upcoming Deadlines (Next 2-3 Days)
            if notifications["upcoming_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="Upcoming Deadlines",
                    icon="🗓",
                    count=notifications["upcoming_count"],
                    title_color=theme.TEXT_PRIMARY,
                    tasks=notifications["upcoming"],
                    category_type="upcoming",
                )

        # ====================================================================
        # 3. Bottom Footer
        # ====================================================================
        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(fill="x", pady=(4, 0))

        lbl_tip = ctk.CTkLabel(
            footer,
            text="💡 Tip: Keep tasks in Q2 (Schedule) to handle them before they become urgent crises.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="center",
            wraplength=480,
            justify="center",
        )
        lbl_tip.pack(fill="x")

    def _render_empty_state(self, parent: ctk.CTkFrame) -> None:
        """Renders an all-clear empty state message when no reminders are active."""
        empty_box = ctk.CTkFrame(
            parent,
            fg_color=theme.BG_CARD_HOVER,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        empty_box.pack(fill="both", expand=True, pady=10)

        inner = ctk.CTkFrame(empty_box, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        lbl_icon = ctk.CTkLabel(inner, text="🎉", font=(theme.FONT_FAMILY, 40))
        lbl_icon.pack(pady=(0, 10))

        lbl_heading = ctk.CTkLabel(
            inner,
            text="You're all caught up!",
            font=(theme.FONT_DISPLAY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_heading.pack(pady=(0, 6))

        lbl_desc = ctk.CTkLabel(
            inner,
            text="No overdue tasks or immediate deadlines within the next 3 days.\nStay proactive by reviewing your long-term goals in Calendar & Matrix.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        )
        lbl_desc.pack()

    def _render_section(
        self,
        parent: Any,
        title: str,
        icon: str,
        count: int,
        title_color: Any,
        tasks: List[Dict[str, Any]],
        category_type: str,
    ) -> None:
        """Renders a clean styled section with task reminder cards."""
        sec_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sec_frame.pack(fill="x", pady=(0, 14))

        # Clean section header row (no heavy full-width colored box)
        header_row = ctk.CTkFrame(sec_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 8))

        # Title on left
        title_box = ctk.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left")

        clean_icon = icon.replace("\ufe0f", "") if isinstance(icon, str) else icon

        lbl_icon = ctk.CTkLabel(
            title_box,
            text=clean_icon,
            font=(theme.FONT_FAMILY, 13),
        )
        lbl_icon.pack(side="left", padx=(0, 6))

        lbl_sec_title = ctk.CTkLabel(
            title_box,
            text=title,
            font=(theme.FONT_DISPLAY, 13, "bold"),
            text_color=title_color,
        )
        lbl_sec_title.pack(side="left")

        # Subtle count pill on right
        pill_count = ctk.CTkFrame(
            header_row,
            fg_color=theme.BG_CARD_HOVER,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            height=22,
        )
        pill_count.pack(side="right")
        lbl_count = ctk.CTkLabel(
            pill_count,
            text=f"{count} task{'s' if count != 1 else ''}",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        lbl_count.pack(padx=8, pady=2)

        # Render Task Cards
        for task in tasks:
            self._render_task_card(sec_frame, task, category_type)

    def _render_task_card(self, parent: Any, task: Dict[str, Any], category_type: str) -> None:
        """Renders an interactive task reminder card with quick actions."""
        quadrant_info = theme.QUADRANTS.get(
            task.get("quadrant", "Q1_DO"),
            theme.QUADRANTS["Q1_DO"],
        )
        is_delayed = (category_type == "overdue") or bool(task.get("is_delayed", False))
        is_q1 = task.get("quadrant") == "Q1_DO"

        # Elevated card container
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.BG_CARD_HOVER,
            corner_radius=10,
            border_width=1,
            border_color=theme.DELAYED_BORDER if is_delayed else theme.BORDER_COLOR,
        )
        card.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        # --------------------------------------------------------------------
        # Row 1: Priority Badges on Left, Relative Timing + Dismiss on Right
        # --------------------------------------------------------------------
        row_top = ctk.CTkFrame(inner, fg_color="transparent")
        row_top.pack(fill="x", pady=(0, 6))

        left_badges = ctk.CTkFrame(row_top, fg_color="transparent")
        left_badges.pack(side="left")

        # Quadrant Pill
        q_badge_frame = ctk.CTkFrame(
            left_badges,
            fg_color=theme.DELAYED_BG if is_delayed else quadrant_info["bg_header"],
            corner_radius=6,
            border_width=1,
            border_color=theme.DELAYED_BORDER if is_delayed else quadrant_info["border"],
        )
        q_badge_frame.pack(side="left", padx=(0, 6))
        lbl_q_badge = ctk.CTkLabel(
            q_badge_frame,
            text=quadrant_info["badge"],
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.DELAYED_TEXT if is_delayed else quadrant_info["text"],
        )
        lbl_q_badge.pack(padx=6, pady=2)

        # Runway Pill (STRICTLY ONLY FOR RED / Q1_DO TASKS)
        est_duration = int(task.get("estimated_duration") or 0)
        if is_q1 and est_duration > 0:
            if est_duration < 60:
                dur_text = f"{est_duration}m"
            elif est_duration % 60 == 0:
                dur_text = f"{est_duration // 60}h"
            else:
                dur_text = f"{est_duration // 60}h {est_duration % 60}m"

            runway_pill = ctk.CTkFrame(
                left_badges,
                fg_color=theme.DELAYED_BG if is_delayed else ("#FEF2F2", "#2A0A0A"),
                corner_radius=6,
                border_width=1,
                border_color=theme.DELAYED_BORDER if is_delayed else ("#FCA5A5", "#7F1D1D"),
            )
            runway_pill.pack(side="left", padx=(0, 6))
            lbl_runway_pill = ctk.CTkLabel(
                runway_pill,
                text=f"⏱️ {dur_text} Runway",
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.DELAYED_TEXT if is_delayed else ("#DC2626", "#F87171"),
            )
            lbl_runway_pill.pack(padx=6, pady=2)

        # If delayed / overdue: show explicit warning tag
        days_diff = task.get("days_diff", 0)
        if is_delayed:
            if days_diff < 0:
                delay_lbl = f"⚠️ Overdue {abs(days_diff)}d"
            else:
                rem_time = task.get("reminder_time", "")
                delay_lbl = f"⚠️ Passed ({rem_time})" if rem_time else "⚠️ Passed Today"

            overdue_pill = ctk.CTkFrame(
                left_badges,
                fg_color=("#FEF2F2", "#2A0A0A"),
                corner_radius=6,
                border_width=1,
                border_color=("#FCA5A5", "#7F1D1D"),
            )
            overdue_pill.pack(side="left")
            lbl_overdue_pill = ctk.CTkLabel(
                overdue_pill,
                text=delay_lbl,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=("#DC2626", "#F87171"),
            )
            lbl_overdue_pill.pack(padx=6, pady=2)

        # Right side: Relative timing chip & dismiss button
        right_box = ctk.CTkFrame(row_top, fg_color="transparent")
        right_box.pack(side="right")

        if not is_delayed:
            if category_type == "upcoming" and days_diff > 0:
                lbl_timing = ctk.CTkLabel(
                    right_box,
                    text=f"In {days_diff} days",
                    font=(theme.FONT_FAMILY, 11),
                    text_color=theme.TEXT_SECONDARY,
                )
                lbl_timing.pack(side="left", padx=(0, 8))
            elif category_type == "tomorrow":
                lbl_timing = ctk.CTkLabel(
                    right_box,
                    text="Tomorrow",
                    font=(theme.FONT_FAMILY, 11),
                    text_color=("#D97706", "#FBBF24"),
                )
                lbl_timing.pack(side="left", padx=(0, 8))
            elif category_type == "today":
                lbl_timing = ctk.CTkLabel(
                    right_box,
                    text="Today",
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    text_color=("#DC2626", "#F87171"),
                )
                lbl_timing.pack(side="left", padx=(0, 8))

        # Cross mark to dismiss task from flyout
        btn_dismiss = ctk.CTkButton(
            right_box,
            text="✕",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="transparent",
            hover_color=theme.BG_CARD,
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=lambda t_id=task.get("id"): self._on_dismiss_task(t_id),
        )
        btn_dismiss.pack(side="left")

        # --------------------------------------------------------------------
        # Row 2: Task Title and Description
        # --------------------------------------------------------------------
        title_text = task.get("title", "Untitled Task")
        lbl_title = ctk.CTkLabel(
            inner,
            text=title_text,
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.DELAYED_TITLE if is_delayed else theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        desc_text = task.get("description", "").strip()
        if desc_text:
            short_desc = desc_text if len(desc_text) <= 80 else desc_text[:77] + "..."
            lbl_desc = ctk.CTkLabel(
                inner,
                text=short_desc,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.DELAYED_DESC if is_delayed else theme.TEXT_SECONDARY,
                anchor="w",
            )
            lbl_desc.pack(fill="x", pady=(0, 4))

        # --------------------------------------------------------------------
        # Row 3: Scheduled Due Date & Reminder Time
        # --------------------------------------------------------------------
        due_str = task.get("due_date", "")
        date_display = due_str
        if due_str:
            try:
                parsed_due = datetime.strptime(due_str, "%Y-%m-%d").date()
                date_display = parsed_due.strftime("%b %d, %Y")
            except Exception:
                pass

        reminder_info = f"  •  🔔 {task['reminder_time']}" if task.get("reminder_time") else ""

        row_date = ctk.CTkFrame(inner, fg_color="transparent")
        row_date.pack(fill="x", pady=(2, 6))

        lbl_due_date = ctk.CTkLabel(
            row_date,
            text=f"📅 {date_display}{reminder_info}",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        lbl_due_date.pack(side="left")

        # --------------------------------------------------------------------
        # Row 4: Action Buttons (Right-aligned, clean, uniform height 26)
        # --------------------------------------------------------------------
        row_actions = ctk.CTkFrame(inner, fg_color="transparent")
        row_actions.pack(fill="x", pady=(2, 0))

        btn_box = ctk.CTkFrame(row_actions, fg_color="transparent")
        btn_box.pack(side="right")

        if is_delayed:
            # Reschedule button (primary for delayed)
            btn_reschedule = ctk.CTkButton(
                btn_box,
                text="📅 Reschedule",
                width=96,
                height=26,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=lambda t=task: self._on_reschedule_click(t),
            )
            btn_reschedule.pack(side="left", padx=(0, 6))

            # Edit button (uses clean Unicode ✎ and text)
            btn_edit = ctk.CTkButton(
                btn_box,
                text="✎ Edit",
                width=58,
                height=26,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_SECONDARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=lambda t=task: self._on_edit_click(t),
            )
            btn_edit.pack(side="left")
        else:
            # Focus button - strictly only for Q1 tasks
            if is_q1:
                btn_focus = ctk.CTkButton(
                    btn_box,
                    text="🍅 Focus",
                    width=72,
                    height=26,
                    corner_radius=6,
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    fg_color=("#FEF2F2", "#2A0A0A"),
                    hover_color=("#FEE2E2", "#450A0A"),
                    text_color=("#DC2626", "#F87171"),
                    border_width=1,
                    border_color=("#FCA5A5", "#7F1D1D"),
                    command=lambda t=task: self._on_focus_click(t),
                )
                btn_focus.pack(side="left", padx=(0, 6))

            # Done button
            btn_done = ctk.CTkButton(
                btn_box,
                text="✓ Done",
                width=66,
                height=26,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color=("#ECFDF5", "#042218"),
                hover_color=("#D1FAE5", "#064E3B"),
                text_color=("#059669", "#34D399"),
                border_width=1,
                border_color=("#34D399", "#064E3B"),
                command=lambda t_id=task["id"]: self._on_done_click(t_id),
            )
            btn_done.pack(side="left", padx=(0, 6))

            # Schedule button
            btn_schedule = ctk.CTkButton(
                btn_box,
                text="📅 Schedule",
                width=88,
                height=26,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_PRIMARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=lambda t=task: self._on_reschedule_click(t),
            )
            btn_schedule.pack(side="left", padx=(0, 6))

            # Edit button (uses clean Unicode ✎ and text)
            btn_edit = ctk.CTkButton(
                btn_box,
                text="✎ Edit",
                width=58,
                height=26,
                corner_radius=6,
                font=(theme.FONT_FAMILY, 11, "bold"),
                fg_color=theme.BG_CARD,
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_SECONDARY,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                command=lambda t=task: self._on_edit_click(t),
            )
            btn_edit.pack(side="left")

    def _on_done_click(self, task_id: int) -> None:
        """Handles completing a task directly from the notification modal."""
        self.on_toggle(task_id)
        # Update internal tasks list and re-render modal
        self.tasks = [t for t in self.tasks if t.get("id") != task_id]
        self._build_ui()
        if self.on_refresh:
            self.on_refresh()

    def _on_dismiss_task(self, task_id: Optional[int]) -> None:
        """Hides/dismisses a single task from the notification panel."""
        if task_id is not None:
            self.dismissed_task_ids.add(task_id)
            if hasattr(self.master, "dismissed_notification_ids"):
                self.master.dismissed_notification_ids.add(task_id)
        if hasattr(self.master, "all_tasks"):
            self.tasks = list(self.master.all_tasks)
        self._build_ui()
        if self.on_refresh:
            self.on_refresh()

    def _clear_all_notifications(self) -> None:
        """Clears all currently active notifications from the notification panel."""
        visible_tasks = [t for t in self.tasks if t.get("id") not in self.dismissed_task_ids]
        notifications = get_task_notifications(visible_tasks)
        all_notif_tasks = (
            notifications.get("overdue", [])
            + notifications.get("today", [])
            + notifications.get("tomorrow", [])
            + notifications.get("upcoming", [])
        )
        for t in all_notif_tasks:
            t_id = t.get("id")
            if t_id is not None:
                self.dismissed_task_ids.add(t_id)
                if hasattr(self.master, "dismissed_notification_ids"):
                    self.master.dismissed_notification_ids.add(t_id)

        if hasattr(self.master, "all_tasks"):
            self.tasks = list(self.master.all_tasks)
        self._build_ui()
        if self.on_refresh:
            self.on_refresh()

    def _on_reschedule_click(self, task: Dict[str, Any]) -> None:
        """Closes notification modal and opens the ScheduleModal for the task."""
        self.destroy()
        self.on_schedule(task)

    def _on_edit_click(self, task: Dict[str, Any]) -> None:
        """Closes notification modal and opens the TaskModal for editing."""
        self.destroy()
        self.on_edit(task)

    def _on_focus_click(self, task: Dict[str, Any]) -> None:
        """Closes notification modal and launches Pomodoro timer for this task."""
        self.destroy()
        if self.on_focus:
            self.on_focus(task)
        elif hasattr(self.master, "open_pomodoro_modal"):
            self.master.open_pomodoro_modal(task)

    def destroy(self) -> None:
        """Cleans up active modal reference and destroys the window."""
        try:
            if hasattr(self.master, "active_notification_modal") and self.master.active_notification_modal is self:
                self.master.active_notification_modal = None
        except Exception:
            pass
        super().destroy()
