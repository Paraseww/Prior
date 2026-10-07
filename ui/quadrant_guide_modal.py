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


class QuadrantGuideModal(ctk.CTkToplevel):
    """
    Contextual guide modal displaying quadrant principles, analytics integration,
    and icon legend (completed vs archived).
    """

    QUADRANT_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
        "Q1_DO": {
            "name": "Q1: Urgent & Important",
            "tagline": "Do First — Immediate crises & critical deadlines",
            "analytics_points": [
                (
                    "📈 7-Day Velocity Chart",
                    "Tasks completed here directly drive the daily focus bars in your 7-Day Focus Velocity chart.",
                ),
                (
                    "🍅 Deep Work & Today's Focus",
                    "Focus sprints completed for Q1 tasks are logged into your Today's Focus and Lifetime Deep Work stats.",
                ),
                (
                    "🎯 High-Impact Execution",
                    "Reflects your most vital, deadline-driven execution. Keeping this high ensures peak productivity.",
                ),
            ],
        },
        "Q2_SCHEDULE": {
            "name": "Q2: Not Urgent & Important",
            "tagline": "Schedule — Long-term growth, planning & deep work",
            "analytics_points": [
                (
                    "🎯 Proactive Focus Score",
                    "Tasks scheduled and completed here feed your weekly Proactive Pipeline target (4+ upcoming tasks).",
                ),
                (
                    "📊 Matrix Completion Rate",
                    "Boosts your overall completion rate and balances your Eisenhower quadrant distribution.",
                ),
                (
                    "🛡️ Crisis Prevention",
                    "Investing time here prevents urgent Q1 firefighting by addressing important priorities early.",
                ),
            ],
        },
        "Q3_DELEGATE": {
            "name": "Q3: Urgent & Not Important",
            "tagline": "Delegate — Interruptions, quick requests & busywork",
            "analytics_points": [
                (
                    "📊 Quadrant Breakdown",
                    "Completed tasks here are tracked in your Eisenhower Quadrant Distribution overview.",
                ),
                (
                    "⏱️ Interruption Audit",
                    "Helps you monitor how much time is consumed by urgent demands from others versus your core goals.",
                ),
                (
                    "🤝 Effective Delegation",
                    "Checking off tasks here reflects resolved administrative handoffs and quick requests.",
                ),
            ],
        },
        "Q4_ELIMINATE": {
            "name": "Q4: Not Urgent & Not Important",
            "tagline": "Eliminate — Distractions, time wasters & clutter",
            "analytics_points": [
                (
                    "📊 Matrix Distribution",
                    "Completed tasks here are accounted for in your total completed task count and progress rates.",
                ),
                (
                    "🧹 Decluttering Progress",
                    "Logging tasks here helps audit low-value activities and measure how effectively you eliminate waste.",
                ),
                (
                    "🧠 Mental Clarity",
                    "Clearing out low-priority items frees cognitive bandwidth for high-leverage Q1 and Q2 work.",
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

        self.title(f"Prior — {self.info['title']} Guide")
        theme.apply_prior_icon(self)

        self._position_modal(master)
        self._build_ui()

        # Reveal smoothly
        self.after(20, self._reveal_modal)

    def _position_modal(self, master: Any) -> None:
        """Positions and sizes the modal centered relative to master window."""
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            w = min(520, max(420, screen_w - 40))
            h = min(620, max(460, screen_h - 80))

            x = master.winfo_x() + (master.winfo_width() - w) // 2
            y = master.winfo_y() + (master.winfo_height() - h) // 2

            pos_x = max(10, min(x, screen_w - w - 20))
            pos_y = max(10, min(y, screen_h - h - 50))

            self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
            self.minsize(min(420, w), min(460, h))
        except Exception:
            self.geometry("520x620")

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

        btn_close = ctk.CTkButton(
            header_row,
            text="✕",
            width=28,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=self.destroy,
        )
        btn_close.pack(side="right", anchor="n")

        # Divider
        divider = ctk.CTkFrame(container, height=1, fg_color=theme.BORDER_COLOR)
        divider.pack(fill="x", pady=(0, 14))

        # Scrollable container in case of smaller displays
        scroll_content = ctk.CTkScrollableFrame(
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
            text="Checking off a task marks it done and immediately logs its completion and Pomodoro focus records into your local analytics database.",
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
