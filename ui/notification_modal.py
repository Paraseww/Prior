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
    ) -> None:
        super().__init__(master)
        self.tasks = tasks
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_schedule = on_schedule
        self.on_refresh = on_refresh
        if hasattr(master, "dismissed_notification_ids"):
            self.dismissed_task_ids: Set[int] = master.dismissed_notification_ids
        else:
            self.dismissed_task_ids: Set[int] = set()

        self.title("Prior - Task Reminders & Notifications")
        self.geometry("540x660")
        self.minsize(480, 500)
        self.transient(master)
        self.grab_set()

        # Apply Prior application icon
        theme.apply_prior_icon(self)

        # Center modal relative to master window
        self._center_modal(master)
        self._build_ui()

    def _center_modal(self, master: Any) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() - 540) // 2
            y = master.winfo_y() + (master.winfo_height() - 660) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
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
            badge_fg = ("#FEE2E2", "#2A0A0A") if notifications["overdue_count"] > 0 else ("#FEF3C7", "#261603")
            badge_text_col = ("#B91C1C", "#F87171") if notifications["overdue_count"] > 0 else ("#B45309", "#FBBF24")
        else:
            badge_text = "All Clear"
            badge_fg = ("#ECFDF5", "#042218")
            badge_text_col = ("#065F46", "#34D399")

        badge_frame = ctk.CTkFrame(
            title_row,
            fg_color=badge_fg,
            corner_radius=12,
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
                height=28,
                corner_radius=8,
                fg_color=theme.BG_INPUT,
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
            scroll_frame = ctk.CTkScrollableFrame(
                container,
                fg_color="transparent",
                corner_radius=0,
            )
            scroll_frame.pack(fill="both", expand=True, pady=(0, 10))

            # 🔴 Section 1: Delayed / Overdue Tasks
            if notifications["overdue_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="⚠️ Delayed & Overdue Tasks",
                    count=notifications["overdue_count"],
                    header_bg=("#FEE2E2", "#2A0A0A"),
                    header_text_color=("#991B1B", "#F87171"),
                    tasks=notifications["overdue"],
                    category_type="overdue",
                )

            # 🟠 Section 2: Due Today
            if notifications["today_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="⏰ Due Today",
                    count=notifications["today_count"],
                    header_bg=("#FEF3C7", "#261603"),
                    header_text_color=("#92400E", "#FBBF24"),
                    tasks=notifications["today"],
                    category_type="today",
                )

            # 🟡 Section 3: Due Tomorrow
            if notifications["tomorrow_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="⏳ Due Tomorrow",
                    count=notifications["tomorrow_count"],
                    header_bg=("#FFFBEB", "#1C1917"),
                    header_text_color=("#B45309", "#FDE68A"),
                    tasks=notifications["tomorrow"],
                    category_type="tomorrow",
                )

            # 🟢 Section 4: Upcoming in 2-3 Days
            if notifications["upcoming_count"] > 0:
                self._render_section(
                    parent=scroll_frame,
                    title="🗓️ Upcoming Deadlines",
                    count=notifications["upcoming_count"],
                    header_bg=("#F5F3FF", "#181226"),
                    header_text_color=("#6D28D9", "#C4B5FD"),
                    tasks=notifications["upcoming"],
                    category_type="upcoming",
                )

        # ====================================================================
        # 3. Bottom Footer
        # ====================================================================
        footer = ctk.CTkFrame(
            container,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        footer.pack(fill="x", pady=(8, 0))

        inner_footer = ctk.CTkFrame(footer, fg_color="transparent")
        inner_footer.pack(fill="x", padx=12, pady=8)

        lbl_tip = ctk.CTkLabel(
            inner_footer,
            text="💡 Tip: Keep tasks in Q2 (Schedule) to handle them before they become urgent crises.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
            wraplength=480,
            justify="left",
        )
        lbl_tip.pack(fill="x")

    def _render_empty_state(self, parent: ctk.CTkFrame) -> None:
        """Renders an all-clear empty state message when no reminders are active."""
        empty_box = ctk.CTkFrame(
            parent,
            fg_color=theme.BG_INPUT,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        empty_box.pack(fill="both", expand=True, pady=10)

        inner = ctk.CTkFrame(empty_box, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        lbl_icon = ctk.CTkLabel(inner, text="🎉", font=(theme.FONT_FAMILY, 44))
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
        count: int,
        header_bg: Any,
        header_text_color: Any,
        tasks: List[Dict[str, Any]],
        category_type: str,
    ) -> None:
        """Renders a collapsible/styled section with task reminder cards."""
        sec_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sec_frame.pack(fill="x", pady=(0, 14))

        # Section Header Banner
        banner = ctk.CTkFrame(
            sec_frame,
            fg_color=header_bg,
            corner_radius=8,
            height=32,
        )
        banner.pack(fill="x", pady=(0, 8))
        banner.pack_propagate(False)

        inner_ban = ctk.CTkFrame(banner, fg_color="transparent")
        inner_ban.pack(fill="both", expand=True, padx=10)

        lbl_sec_title = ctk.CTkLabel(
            inner_ban,
            text=title,
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=header_text_color,
        )
        lbl_sec_title.pack(side="left")

        lbl_count = ctk.CTkLabel(
            inner_ban,
            text=f"{count} task{'s' if count != 1 else ''}",
            font=(theme.FONT_FAMILY, 11),
            text_color=header_text_color,
        )
        lbl_count.pack(side="right")

        # Render Task Cards
        for task in tasks:
            self._render_task_card(sec_frame, task, category_type)

    def _render_task_card(self, parent: Any, task: Dict[str, Any], category_type: str) -> None:
        """Renders an interactive task reminder card with quick actions."""
        quadrant_info = theme.QUADRANTS.get(
            task.get("quadrant", "Q1_DO"),
            theme.QUADRANTS["Q1_DO"],
        )

        card = ctk.CTkFrame(
            parent,
            fg_color=theme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        card.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Row 1: Badges (Quadrant + Relative Due Status)
        row_badges = ctk.CTkFrame(inner, fg_color="transparent")
        row_badges.pack(fill="x", pady=(0, 4))

        # Quadrant Pill
        q_badge_frame = ctk.CTkFrame(
            row_badges,
            fg_color=quadrant_info["bg_header"],
            corner_radius=6,
        )
        q_badge_frame.pack(side="left", padx=(0, 8))
        lbl_q_badge = ctk.CTkLabel(
            q_badge_frame,
            text=quadrant_info["badge"],
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=quadrant_info["text"],
        )
        lbl_q_badge.pack(padx=6, pady=1)

        # Relative Status Badge
        days_diff = task.get("days_diff", 0)
        due_str = task.get("due_date", "")
        if category_type == "overdue":
            status_text = f"⚠️ Overdue by {abs(days_diff)} day{'s' if abs(days_diff) != 1 else ''}"
            status_fg = ("#FEE2E2", "#2A0A0A")
            status_text_col = ("#B91C1C", "#F87171")
        elif category_type == "today":
            status_text = "⚡ Due Today"
            status_fg = ("#FEF3C7", "#261603")
            status_text_col = ("#B45309", "#FBBF24")
        elif category_type == "tomorrow":
            status_text = "⏳ Due Tomorrow"
            status_fg = ("#FFFBEB", "#1C1917")
            status_text_col = ("#B45309", "#FDE68A")
        else:
            status_text = f"📌 {days_diff} days left"
            status_fg = ("#F5F3FF", "#181226")
            status_text_col = ("#6D28D9", "#C4B5FD")

        status_badge_frame = ctk.CTkFrame(
            row_badges,
            fg_color=status_fg,
            corner_radius=6,
        )
        status_badge_frame.pack(side="left")
        lbl_status_badge = ctk.CTkLabel(
            status_badge_frame,
            text=status_text,
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=status_text_col,
        )
        lbl_status_badge.pack(padx=6, pady=1)

        # Cross mark to remove/dismiss this task from notification panel
        btn_dismiss = ctk.CTkButton(
            row_badges,
            text="✕",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="transparent",
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=lambda t_id=task.get("id"): self._on_dismiss_task(t_id),
        )
        btn_dismiss.pack(side="right")

        # Row 2: Task Title
        title_text = task.get("title", "Untitled Task")
        lbl_title = ctk.CTkLabel(
            inner,
            text=title_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        # Optional task description (truncated)
        desc_text = task.get("description", "").strip()
        if desc_text:
            short_desc = desc_text if len(desc_text) <= 80 else desc_text[:77] + "..."
            lbl_desc = ctk.CTkLabel(
                inner,
                text=short_desc,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_SECONDARY,
                anchor="w",
            )
            lbl_desc.pack(fill="x", pady=(0, 6))

        # Row 3: Due Date Details & Quick Action Buttons
        row_actions = ctk.CTkFrame(inner, fg_color="transparent")
        row_actions.pack(fill="x", pady=(4, 0))

        # Due Date info text
        date_display = due_str
        if due_str:
            try:
                parsed_due = datetime.strptime(due_str, "%Y-%m-%d").date()
                date_display = parsed_due.strftime("%b %d, %Y")
            except Exception:
                pass

        reminder_info = f" • 🔔 {task['reminder_time']}" if task.get("reminder_time") else ""
        lbl_due_date = ctk.CTkLabel(
            row_actions,
            text=f"📅 {date_display}{reminder_info}",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
        )
        lbl_due_date.pack(side="left")

        # Action Buttons on Right
        btn_box = ctk.CTkFrame(row_actions, fg_color="transparent")
        btn_box.pack(side="right")

        # Done button (✓)
        btn_done = ctk.CTkButton(
            btn_box,
            text="✓ Done",
            width=65,
            height=26,
            corner_radius=6,
            font=(theme.FONT_FAMILY, 11, "bold"),
            fg_color=("#ECFDF5", "#042218"),
            hover_color=("#A7F3D0", "#064E3B"),
            text_color=("#065F46", "#34D399"),
            command=lambda t_id=task["id"]: self._on_done_click(t_id),
        )
        btn_done.pack(side="left", padx=(0, 6))

        # Reschedule button (📅)
        btn_reschedule = ctk.CTkButton(
            btn_box,
            text="📅 Schedule",
            width=85,
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

        # Edit button (✏️)
        btn_edit = ctk.CTkButton(
            btn_box,
            text="✏️",
            width=28,
            height=26,
            corner_radius=6,
            font=(theme.FONT_FAMILY, 11),
            fg_color=theme.BG_CARD,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
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
