"""
ui/quadrant_guide_modal.py
Quadrant Guide and Analytics Explanation Modal for Prior.
Provides contextual education explaining how tasks completed in each
Eisenhower quadrant feed the Analytics dashboard, along with an icon guide
for task completion and archiving.
"""

from typing import Any, Dict, Optional
import customtkinter as ctk

from ui import theme
from ui.smooth_scroll import SmoothScrollableFrame


class QuadrantGuideModal(ctk.CTkToplevel):
    """
    Contextual guide modal displaying quadrant principles, analytics integration,
    and icon legend (completed vs archived).
    """

    QUADRANT_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
        "Q1_DO": {
            "name": "Q1: Urgent & Important",
            "tagline": "Do First - Immediate crises, critical deadlines & deep focus execution",
            "analytics_points": [
                (
                    "🍅 Deep Work & Today's Focus (Timer-Exclusive)",
                    "Running the 25m Pomodoro Focus Timer logs focus sprints directly into Today's Focus (🍅), Lifetime Deep Work, and Active Focus Days in Analytics.",
                ),
                (
                    "📈 7-Day Focus Velocity & Daily Cadence",
                    "Deep work sprints completed on Q1 tasks populate the daily bar chart in your 7-Day Velocity view, illustrating your daily focus minutes and sprint volume.",
                ),
                (
                    "🏆 Most Focused Tasks Leaderboard",
                    "Q1 tasks with high time investment compete for top positions on your leaderboard, spotlighting where your deep focus is most heavily concentrated.",
                ),
                (
                    "📅 Weekly vs. All-Time Completion Impact",
                    "Checking off Q1 tasks directly increases your overall Completion Rate and drives the Q1 distribution bar in both 'This Week' and 'All Time' views.",
                ),
            ],
        },
        "Q2_SCHEDULE": {
            "name": "Q2: Not Urgent & Important",
            "tagline": "Schedule - Strategic goals, planning & proactive pipeline",
            "analytics_points": [
                (
                    "🎯 Proactive Focus Score (Pipeline Health)",
                    "Q2 is the sole driver of the Focus Score card in Analytics. Scheduling 4+ upcoming, forward-looking Q2 tasks achieves an optimal 100% pipeline health rating.",
                ),
                (
                    "🛡️ Overdue Task Penalty & Crisis Prevention",
                    "Delayed tasks are excluded from your proactive score. Addressing Q2 goals on schedule prevents them from turning into urgent, stressful Q1 fires.",
                ),
                (
                    "📅 Weekly Rolling Horizon vs. All-Time Roadmap",
                    "The 'This Week' view tracks tasks scheduled within your rolling 7-day sprint window, while 'All Time' evaluates your strategic vision and lifetime habits.",
                ),
                (
                    "📊 Matrix Completion & Quadrant Balance",
                    "Completing Q2 tasks raises your overall Matrix Completion Rate and ensures your productivity is anchored in long-term high-value growth.",
                ),
            ],
        },
        "Q3_DELEGATE": {
            "name": "Q3: Urgent & Not Important",
            "tagline": "Delegate - Urgent requests, interruptions & handoffs",
            "analytics_points": [
                (
                    "⏱️ Interruption Audit & Demand Monitoring",
                    "Tracked in the Eisenhower Quadrant Distribution to measure how much task volume is absorbed by urgent external demands versus your core goals.",
                ),
                (
                    "📅 Weekly Sprints vs. All-Time Request Influx",
                    "Comparing 'This Week' against 'All Time' reveals whether unexpected requests are temporarily spiking in your sprint or dominating your routine.",
                ),
                (
                    "🤝 Effective Delegation & Handoff Throughput",
                    "Checking off Q3 tasks reflects quickly resolved administrative handoffs, delegated duties, and brief peer responses.",
                ),
                (
                    "📊 Matrix Completion Rate Contribution",
                    "Resolving Q3 tasks contributes to your total completed task count and progress rates without pulling deep focus time away from Q1 and Q2.",
                ),
            ],
        },
        "Q4_ELIMINATE": {
            "name": "Q4: Not Urgent & Not Important",
            "tagline": "Eliminate - Distractions, low-value chores & clutter",
            "analytics_points": [
                (
                    "🧹 Decluttering Progress & Waste Audit",
                    "Tracked in the Eisenhower Quadrant Distribution to audit low-leverage activities. A healthy productivity profile keeps your Q4 footprint minimal.",
                ),
                (
                    "🧠 Cognitive Bandwidth & Mental Clarity",
                    "Clearing non-urgent, non-important tasks eliminates backlog fatigue, freeing mental clarity for high-leverage Q1 sprints and Q2 planning.",
                ),
                (
                    "📅 Weekly vs. All-Time Clutter Ratio",
                    "The 'This Week' view catches recent distractions entering your queue, while 'All Time' reflects your progress in pruning habitual time-wasters.",
                ),
                (
                    "📥 Clean Board with Archive Integration",
                    "Once finished, archive Q4 tasks (📥) to remove visual clutter from your matrix while preserving full historical completion accuracy in Analytics.",
                ),
            ],
        },
    }

    def __init__(self, master: Any, q_key: str = "Q1_DO", **kwargs) -> None:
        super().__init__(master, fg_color=theme.BG_CARD, **kwargs)

        # Immediately withdraw to prevent white flash during creation
        self.withdraw()

        # Set native background
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg_hex = theme.BG_CARD[1] if is_dark else theme.BG_CARD[0]
        try:
            self.config(background=bg_hex)
        except Exception:
            pass

        self.q_key = q_key if q_key in theme.QUADRANTS else "Q1_DO"
        self.info = theme.QUADRANTS[self.q_key]
        self.q_guide = self.QUADRANT_DESCRIPTIONS.get(
            self.q_key, self.QUADRANT_DESCRIPTIONS["Q1_DO"]
        )

        self.title(f"Prior - {self.info['title']} Guide")
        theme.apply_prior_icon(self)

        self._position_modal(master)
        self._build_ui()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.destroy())

        # Reveal smoothly
        self.after(20, self._reveal_modal)

    def _position_modal(self, master: Any) -> None:
        """Positions and sizes the modal centered relative to master window."""
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(530, max(420, screen_w - 40))
            h = min(660, max(460, screen_h - 80))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(min(420, w), min(460, h))
        except Exception:
            self.geometry("530x660")

    def _reveal_modal(self) -> None:
        """Smoothly reveals the window and captures focus."""
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
        """Constructs the guide interface with rich typography and visual cards."""
        self.configure(fg_color=theme.BG_CARD)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=18)

        # 1. Top Header Row
        header_row = ctk.CTkFrame(container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 14))

        header_left = ctk.CTkFrame(header_row, fg_color="transparent")
        header_left.pack(side="left", fill="both", expand=True)

        # Pill badge
        badge_frame = ctk.CTkFrame(header_left, fg_color="transparent")
        badge_frame.pack(fill="x", pady=(0, 4))

        color_dot = ctk.CTkFrame(
            badge_frame,
            width=12,
            height=12,
            corner_radius=6,
            fg_color=self.info["color"],
        )
        color_dot.pack(side="left", padx=(0, 8))

        lbl_title = ctk.CTkLabel(
            badge_frame,
            text=self.q_guide["name"],
            font=(theme.FONT_DISPLAY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_title.pack(side="left")

        lbl_sub = ctk.CTkLabel(
            header_left,
            text=self.q_guide["tagline"],
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x")

        # Divider
        divider = ctk.CTkFrame(container, height=1, fg_color=theme.BORDER_COLOR)
        divider.pack(fill="x", pady=(0, 14))

        # Scrollable container in case of smaller displays
        scroll_content = SmoothScrollableFrame(
            container,
            fg_color="transparent",
            scrollbar_button_color=theme.BORDER_COLOR,
        )
        scroll_content.pack(fill="both", expand=True, pady=(0, 12))

        # ====================================================================
        # Section 1: Analytics & Progress Tracking
        # ====================================================================
        sec1_title = ctk.CTkLabel(
            scroll_content,
            text="📊 Analytics & Progress Tracking",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=self.info["color"],
            anchor="w",
        )
        sec1_title.pack(fill="x", pady=(0, 6))

        card_analytics = ctk.CTkFrame(
            scroll_content,
            fg_color=theme.BG_MAIN,
            corner_radius=10,
            border_width=1,
            border_color=self.info["border"],
        )
        card_analytics.pack(fill="x", pady=(0, 16), padx=2)

        analytics_inner = ctk.CTkFrame(card_analytics, fg_color="transparent")
        analytics_inner.pack(fill="x", padx=14, pady=12)

        for heading, desc in self.q_guide["analytics_points"]:
            point_box = ctk.CTkFrame(analytics_inner, fg_color="transparent")
            point_box.pack(fill="x", pady=(0, 8))

            lbl_h = ctk.CTkLabel(
                point_box,
                text=heading,
                font=(theme.FONT_FAMILY, 12, "bold"),
                text_color=theme.TEXT_PRIMARY,
                anchor="w",
            )
            lbl_h.pack(fill="x")

            lbl_d = ctk.CTkLabel(
                point_box,
                text=desc,
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=440,
            )
            lbl_d.pack(fill="x", pady=(1, 0))

        # ====================================================================
        # Section 2: Completed Tasks & Icon Guide
        # ====================================================================
        sec2_title = ctk.CTkLabel(
            scroll_content,
            text="🏷️ Completed Tasks & Icon Guide",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        sec2_title.pack(fill="x", pady=(0, 6))

        card_icons = ctk.CTkFrame(
            scroll_content,
            fg_color=theme.BG_MAIN,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        card_icons.pack(fill="x", pady=(0, 8), padx=2)

        icons_inner = ctk.CTkFrame(card_icons, fg_color="transparent")
        icons_inner.pack(fill="x", padx=14, pady=12)

        # 1. Checkmark row
        row_check = ctk.CTkFrame(icons_inner, fg_color="transparent")
        row_check.pack(fill="x", pady=(0, 10))

        badge_check = ctk.CTkLabel(
            row_check,
            text="✓",
            font=(theme.FONT_FAMILY, 12, "bold"),
            width=26,
            height=26,
            corner_radius=6,
            fg_color=self.info["color"],
            text_color="#FFFFFF",
        )
        badge_check.pack(side="left", padx=(0, 10), anchor="n")

        text_check_box = ctk.CTkFrame(row_check, fg_color="transparent")
        text_check_box.pack(side="left", fill="both", expand=True)

        lbl_chk_title = ctk.CTkLabel(
            text_check_box,
            text="Completed Task",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_chk_title.pack(fill="x")

        lbl_chk_desc = ctk.CTkLabel(
            text_check_box,
            text="Checking off a task marks it done, increases your overall Completion Rate, and updates your quadrant distribution across both This Week and All Time Analytics.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=410,
        )
        lbl_chk_desc.pack(fill="x", pady=(1, 0))

        # 2. Archive row
        row_arch = ctk.CTkFrame(icons_inner, fg_color="transparent")
        row_arch.pack(fill="x")

        badge_arch = ctk.CTkLabel(
            row_arch,
            text="📥",
            font=(theme.FONT_FAMILY, 13),
            width=26,
            height=26,
            corner_radius=6,
            fg_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
        )
        badge_arch.pack(side="left", padx=(0, 10), anchor="n")

        text_arch_box = ctk.CTkFrame(row_arch, fg_color="transparent")
        text_arch_box.pack(side="left", fill="both", expand=True)

        lbl_arch_title = ctk.CTkLabel(
            text_arch_box,
            text="Archive Task",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_arch_title.pack(fill="x")

        lbl_arch_desc = ctk.CTkLabel(
            text_arch_box,
            text="Hides the finished task from your board to keep it tidy, while preserving 100% of your analytics stats, 7-day velocity chart, and deep work focus history.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=410,
        )
        lbl_arch_desc.pack(fill="x", pady=(1, 0))

        # Bottom Got It Button
        btn_got_it = ctk.CTkButton(
            container,
            text="Got it",
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=34,
            corner_radius=8,
            fg_color=self.info["color"],
            hover_color=self.info["color_dark"],
            text_color="#FFFFFF",
            command=self.destroy,
        )
        btn_got_it.pack(fill="x", pady=(4, 0))
