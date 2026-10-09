"""
ui/analytics_view.py
Productivity analytics, Eisenhower distribution, and Deep Focus Pomodoro dashboard for Prior.
Provides comprehensive insights into task completion velocity, 7-day sprint cadence,
focus time distribution across quadrants, and top focused tasks leaderboard.
"""

from typing import Any, Dict, List
import customtkinter as ctk

import database
from project import calculate_matrix_stats, filter_tasks_by_scope, format_focus_duration
from ui import theme
from ui.dot_pattern import DottedScrollableFrame


class AnalyticsView(DottedScrollableFrame):
    """
    Productivity Analytics & Eisenhower Distribution Dashboard with dot-matrix canvas.
    Elevated in Chunk 4 to include live Pomodoro Deep Work metrics, 7-day velocity charts,
    quadrant time investment breakdown, and top-focused tasks leaderboard.
    """

    def __init__(self, master: Any, tasks: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.tasks = tasks
        self.time_scope: str = "week"

        self._build_ui()

    def _build_ui(self) -> None:
        # Main Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=15)

        # Header Title
        lbl_head = ctk.CTkLabel(
            container,
            text="Productivity & Focus Analytics",
            font=(theme.FONT_DISPLAY, 22, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_head.pack(fill="x", pady=(0, 4))

        lbl_sub = ctk.CTkLabel(
            container,
            text="Comprehensive insights into task completion velocity, Eisenhower priority distribution, and deep work habits.",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 20))

        # ========================================================================
        # Section 1: Eisenhower Matrix & Task Overview
        # ========================================================================
        sec1_header_row = ctk.CTkFrame(container, fg_color="transparent")
        sec1_header_row.pack(fill="x", pady=(0, 10))

        sec1_header = ctk.CTkLabel(
            sec1_header_row,
            text="📊 Eisenhower Matrix & Task Overview",
            font=(theme.FONT_DISPLAY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        sec1_header.pack(side="left")

        # Segmented Time Toggle [ 📅 This Week ]  [ 🌐 All Time ]
        toggle_box = ctk.CTkFrame(
            sec1_header_row,
            fg_color=("#EAE6DF", "#1E1E1E"),
            corner_radius=18,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            height=34,
        )
        toggle_box.pack(side="right")

        self.btn_scope_week = ctk.CTkButton(
            toggle_box,
            text="📅 This Week",
            width=100,
            height=26,
            corner_radius=14,
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda: self._set_time_scope("week"),
        )
        self.btn_scope_week.pack(side="left", padx=(3, 2), pady=3)

        self.btn_scope_all = ctk.CTkButton(
            toggle_box,
            text="🌐 All Time",
            width=90,
            height=26,
            corner_radius=14,
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda: self._set_time_scope("all"),
        )
        self.btn_scope_all.pack(side="left", padx=(2, 3), pady=3)

        # Dynamic Section 1 Container (Cards & Quadrants)
        self.sec1_content = ctk.CTkFrame(container, fg_color="transparent")
        self.sec1_content.pack(fill="x", pady=(0, 10))

        self._update_toggle_buttons()
        self._render_section1_content()

        # ========================================================================
        # Section 2: Deep Work & Pomodoro Focus (Chunk 4 Elevation)
        # ========================================================================
        divider = ctk.CTkFrame(container, height=1, fg_color=theme.BORDER_COLOR)
        divider.pack(fill="x", pady=(16, 20))

        lbl_focus_head = ctk.CTkLabel(
            container,
            text="🍅 Deep Work & Pomodoro Focus",
            font=(theme.FONT_DISPLAY, 18, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_focus_head.pack(fill="x", pady=(0, 4))

        lbl_focus_sub = ctk.CTkLabel(
            container,
            text="Live metrics logged from your local Pomodoro sessions. Track deep work consistency, daily velocity, and priority allocation.",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_focus_sub.pack(fill="x", pady=(0, 16))

        # Focus Metric Cards Row
        today_stats = database.get_daily_pomodoro_stats(quadrant="Q1_DO")
        lifetime_stats = database.get_all_time_pomodoro_summary(quadrant="Q1_DO")

        focus_cards_row = ctk.CTkFrame(container, fg_color="transparent")
        focus_cards_row.pack(fill="x", pady=(0, 20))

        # 1. Today's Focus Card
        today_mins = int(today_stats.get("total_focus_minutes") or today_stats.get("total_minutes") or 0)
        today_sprints = int(today_stats.get("sprints_count", 0))
        card_today = self._create_metric_card(
            focus_cards_row,
            title="Today's Focus",
            value=f"{today_sprints} 🍅  ({format_focus_duration(today_mins)})",
            subtitle=f"{today_sprints} focus sprints completed today",
            accent_color=("#EF4444", "#F87171"),
        )
        card_today.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 2. Lifetime Focus Card
        total_focus_mins = lifetime_stats.get("total_focus_minutes", 0)
        total_sprints = lifetime_stats.get("total_sprints", 0)
        card_lifetime = self._create_metric_card(
            focus_cards_row,
            title="Lifetime Deep Work",
            value=format_focus_duration(total_focus_mins),
            subtitle=f"Across {total_sprints} completed sprints",
            accent_color=theme.ACCENT_PRIMARY,
        )
        card_lifetime.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 3. Focus Consistency Card
        active_days = lifetime_stats.get("active_days_count", 0)
        card_days = self._create_metric_card(
            focus_cards_row,
            title="Active Focus Days",
            value=f"{active_days} Days",
            subtitle="Recorded days with deep work",
            accent_color=("#10B981", "#34D399"),
        )
        card_days.pack(side="left", fill="both", expand=True)

        # ========================================================================
        # Section 3: 7-Day Focus Velocity (Bar Chart Card)
        # ========================================================================
        weekly_data = database.get_weekly_pomodoro_breakdown(quadrant="Q1_DO")
        week_total_mins = sum(d["focus_minutes"] for d in weekly_data)
        week_total_sprints = sum(d["sprints_count"] for d in weekly_data)

        card_weekly = ctk.CTkFrame(
            container,
            fg_color=theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        card_weekly.pack(fill="x", pady=(0, 20))

        w_header = ctk.CTkFrame(card_weekly, fg_color="transparent")
        w_header.pack(fill="x", padx=18, pady=(16, 4))

        w_title = ctk.CTkLabel(
            w_header,
            text="📈 7-Day Focus Velocity",
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        w_title.pack(side="left")

        w_summary = ctk.CTkLabel(
            w_header,
            text=f"Past 7 Days: {format_focus_duration(week_total_mins)} ({week_total_sprints} sprints)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        w_summary.pack(side="right")

        w_subtitle = ctk.CTkLabel(
            card_weekly,
            text="Daily focus minutes and sprint volume over the past week.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        w_subtitle.pack(fill="x", padx=18, pady=(0, 14))

        chart_row = ctk.CTkFrame(card_weekly, fg_color="transparent")
        chart_row.pack(fill="x", padx=18, pady=(0, 18))

        max_mins = max([d["focus_minutes"] for d in weekly_data] + [60])

        for day in weekly_data:
            col = ctk.CTkFrame(chart_row, fg_color="transparent")
            col.pack(side="left", fill="both", expand=True, padx=4)

            # Top: minutes label
            mins = day["focus_minutes"]
            mins_text = format_focus_duration(mins) if mins > 0 else "0m"
            is_today = day.get("is_today", False)
            lbl_m = ctk.CTkLabel(
                col,
                text=mins_text,
                font=(theme.FONT_FAMILY, 11, "bold" if is_today else "normal"),
                text_color=("#EF4444", "#F87171") if is_today else theme.TEXT_SECONDARY,
            )
            lbl_m.pack(pady=(0, 6))

            # Vertical bar
            bar = ctk.CTkProgressBar(
                col,
                orientation="vertical",
                width=24,
                height=96,
                corner_radius=6,
                fg_color=("#E5E0D8", "#222222"),
                progress_color=("#EF4444", "#F87171") if is_today else theme.ACCENT_PRIMARY,
            )
            bar.pack(pady=(0, 6))
            bar_val = min(1.0, mins / max_mins) if max_mins > 0 else 0.0
            bar.set(bar_val)

            # Sprint badge / count
            sprints = day["sprints_count"]
            sprint_str = f"{sprints} 🍅" if sprints > 0 else "—"
            lbl_s = ctk.CTkLabel(
                col,
                text=sprint_str,
                font=(theme.FONT_FAMILY, 10),
                text_color=theme.TEXT_MUTED,
            )
            lbl_s.pack(pady=(0, 2))

            # Day label
            day_label = "Today" if is_today else day["day_name"]
            lbl_d = ctk.CTkLabel(
                col,
                text=day_label,
                font=(theme.FONT_FAMILY, 12, "bold" if is_today else "normal"),
                text_color=("#EF4444", "#F87171") if is_today else theme.TEXT_PRIMARY,
            )
            lbl_d.pack()

            # Date subtext (MM/DD)
            date_short = day["date"][5:].replace("-", "/")
            lbl_date = ctk.CTkLabel(
                col,
                text=date_short,
                font=(theme.FONT_FAMILY, 10),
                text_color=theme.TEXT_MUTED,
            )
            lbl_date.pack()

        # ========================================================================
        # Section 4: Most Focused Tasks Leaderboard
        # ========================================================================
        split_row = ctk.CTkFrame(container, fg_color="transparent")
        split_row.pack(fill="x", pady=(0, 20))

        # --- Most Focused Tasks Leaderboard ---
        card_top = ctk.CTkFrame(
            split_row,
            fg_color=theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        card_top.pack(side="left", fill="both", expand=True)

        top_header = ctk.CTkFrame(card_top, fg_color="transparent")
        top_header.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            top_header,
            text="🏆 Most Focused Tasks",
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")

        top_tasks = database.get_top_focused_tasks(limit=5, quadrant="Q1_DO")
        if top_tasks:
            ctk.CTkLabel(
                top_header,
                text=f"Top {len(top_tasks)} Tasks",
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=theme.TEXT_SECONDARY,
            ).pack(side="right")

        ctk.CTkLabel(
            card_top,
            text="Tasks with the highest accumulated deep work time.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 12))

        top_inner_box = ctk.CTkFrame(card_top, fg_color="transparent")
        top_inner_box.pack(fill="x", padx=16, pady=(0, 16))

        if not top_tasks:
            lbl_empty_t = ctk.CTkLabel(
                top_inner_box,
                text="No focused tasks yet.\nLaunch a Pomodoro sprint on any task to see it on the leaderboard.",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_MUTED,
                justify="center",
            )
            lbl_empty_t.pack(pady=28)
        else:
            for idx, task in enumerate(top_tasks, 1):
                row_item = ctk.CTkFrame(
                    top_inner_box,
                    fg_color=theme.BG_CARD_HOVER,
                    corner_radius=8,
                    border_width=1,
                    border_color=theme.BORDER_COLOR,
                )
                row_item.pack(fill="x", pady=4)

                inner_r = ctk.CTkFrame(row_item, fg_color="transparent")
                inner_r.pack(fill="x", padx=12, pady=8)

                # Rank indicator (#1, #2, #3, ...)
                lbl_rank = ctk.CTkLabel(
                    inner_r,
                    text=f"#{idx}",
                    font=(theme.FONT_FAMILY, 12, "bold"),
                    text_color=theme.TEXT_SECONDARY,
                    width=28,
                    anchor="w",
                )
                lbl_rank.pack(side="left")

                # Task title (truncated)
                raw_title = task.get("title", "Untitled Task")
                title_display = raw_title if len(raw_title) <= 40 else f"{raw_title[:38]}..."
                is_done = task.get("is_completed", 0) == 1

                lbl_t_name = ctk.CTkLabel(
                    inner_r,
                    text=title_display,
                    font=(theme.FONT_FAMILY, 13, "bold"),
                    text_color=theme.TEXT_MUTED if is_done else theme.TEXT_PRIMARY,
                    anchor="w",
                )
                lbl_t_name.pack(side="left", padx=(4, 8))

                # Stats on right: Sprints & Duration
                t_mins = task.get("focus_minutes", 0)
                t_sprints = task.get("sprints_count", 0)
                lbl_t_stats = ctk.CTkLabel(
                    inner_r,
                    text=f"{t_sprints} 🍅  •  {format_focus_duration(t_mins)}",
                    font=(theme.FONT_FAMILY, 12, "bold"),
                    text_color=theme.ACCENT_PRIMARY,
                )
                lbl_t_stats.pack(side="right")

    def _create_metric_card(
        self,
        master: Any,
        title: str,
        value: str,
        subtitle: str,
        accent_color: Any,
    ) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            height=110,
        )
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        lbl_t = ctk.CTkLabel(
            inner,
            text=title,
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_t.pack(fill="x")

        lbl_v = ctk.CTkLabel(
            inner,
            text=value,
            font=(theme.FONT_DISPLAY, 22, "bold"),
            text_color=accent_color,
            anchor="w",
        )
        lbl_v.pack(fill="x", pady=(2, 2))

        lbl_s = ctk.CTkLabel(
            inner,
            text=subtitle,
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        lbl_s.pack(fill="x")

        return card

    def _set_time_scope(self, scope: str) -> None:
        if self.time_scope == scope:
            return
        self.time_scope = scope
        self._update_toggle_buttons()
        self._render_section1_content()

    def _update_toggle_buttons(self) -> None:
        if self.time_scope == "week":
            self.btn_scope_week.configure(
                fg_color=theme.ACCENT_PRIMARY,
                text_color="#FFFFFF",
                hover_color=theme.ACCENT_HOVER,
            )
            self.btn_scope_all.configure(
                fg_color="transparent",
                text_color=theme.TEXT_SECONDARY,
                hover_color=("#D5D0C8", "#2A2A2A"),
            )
        else:
            self.btn_scope_week.configure(
                fg_color="transparent",
                text_color=theme.TEXT_SECONDARY,
                hover_color=("#D5D0C8", "#2A2A2A"),
            )
            self.btn_scope_all.configure(
                fg_color=theme.ACCENT_PRIMARY,
                text_color="#FFFFFF",
                hover_color=theme.ACCENT_HOVER,
            )

    def _render_section1_content(self) -> None:
        for child in self.sec1_content.winfo_children():
            child.destroy()

        filtered_tasks = filter_tasks_by_scope(self.tasks, scope=self.time_scope)
        stats = calculate_matrix_stats(filtered_tasks)

        # Top 3 Metrics Cards Row
        cards_row = ctk.CTkFrame(self.sec1_content, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, 14))

        # 1. Total Tasks Card
        total_sub = (
            f"{stats['completed_tasks']} completed • {stats['pending_tasks']} pending (This Week)"
            if self.time_scope == "week"
            else f"{stats['completed_tasks']} completed • {stats['pending_tasks']} pending (All Time)"
        )
        card_total = self._create_metric_card(
            cards_row,
            title="Total Tasks",
            value=str(stats["total_tasks"]),
            subtitle=total_sub,
            accent_color=theme.ACCENT_PRIMARY,
        )
        card_total.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 2. Completion Rate Card
        comp_sub = (
            "Weekly tasks completed"
            if self.time_scope == "week"
            else "Overall tasks completed"
        )
        card_comp = self._create_metric_card(
            cards_row,
            title="Completion Rate",
            value=f"{stats['completion_rate']}%",
            subtitle=comp_sub,
            accent_color="#10B981",
        )
        card_comp.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 3. Proactive Focus Score Card (Weekly Pipeline Health Target)
        proactive_q2 = stats.get("proactive_q2_tasks", 0)
        target_q2 = stats.get("target_q2_tasks", 4)
        focus_score = stats.get("focus_score", 0.0)

        if proactive_q2 == 0:
            focus_sub = f"0/{target_q2} upcoming • Schedule next goals"
            focus_accent = "#94A3B8"
        elif proactive_q2 == 1:
            focus_sub = f"1/{target_q2} upcoming • Getting started"
            focus_accent = "#3B82F6"
        elif proactive_q2 == 2:
            focus_sub = f"2/{target_q2} upcoming • Building momentum"
            focus_accent = "#3B82F6"
        elif proactive_q2 == 3:
            focus_sub = f"3/{target_q2} upcoming • Solid weekly plan"
            focus_accent = "#3B82F6"
        else:
            focus_sub = f"{proactive_q2}/{target_q2} upcoming • Optimal pipeline 🎯"
            focus_accent = "#10B981"

        card_focus = self._create_metric_card(
            cards_row,
            title="Focus Score (Q2 Schedule)",
            value=f"{focus_score}%",
            subtitle=focus_sub,
            accent_color=focus_accent,
        )
        card_focus.pack(side="left", fill="both", expand=True)

        # Quadrant Active Task Distribution Cards
        q_grid = ctk.CTkFrame(self.sec1_content, fg_color="transparent")
        q_grid.pack(fill="x", pady=(0, 10))

        quadrant_keys = ["Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"]
        for q_key in quadrant_keys:
            info = theme.QUADRANTS[q_key]
            active_count = stats["quadrant_counts"].get(q_key, 0)
            completed_count = stats.get("quadrant_completed", {}).get(q_key, 0)
            total_in_q = active_count + completed_count
            comp_pct = round((completed_count / total_in_q) * 100.0, 1) if total_in_q > 0 else 0.0

            q_card = ctk.CTkFrame(
                q_grid,
                fg_color=theme.BG_CARD,
                corner_radius=12,
                border_width=1,
                border_color=info["border"],
            )
            q_card.pack(fill="x", pady=5)

            q_inner = ctk.CTkFrame(q_card, fg_color="transparent")
            q_inner.pack(fill="x", padx=16, pady=(10, 6))

            dot = ctk.CTkFrame(q_inner, width=12, height=12, corner_radius=6, fg_color=info["color"])
            dot.pack(side="left", padx=(0, 10))

            lbl_q_name = ctk.CTkLabel(
                q_inner,
                text=info["title"],
                font=(theme.FONT_FAMILY, 14, "bold"),
                text_color=theme.TEXT_PRIMARY,
            )
            lbl_q_name.pack(side="left")

            lbl_q_sub = ctk.CTkLabel(
                q_inner,
                text=f"— {info['subtitle'].split('—')[-1].strip()}",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_SECONDARY,
            )
            lbl_q_sub.pack(side="left", padx=(6, 0))

            # Dynamic text badge accounting for both active and completed tasks
            if total_in_q == 0:
                count_text = "0 tasks"
                text_col = theme.TEXT_MUTED
                bar_val = 0.0
            elif active_count == 0 and completed_count > 0:
                count_text = f"✓ All {completed_count} completed (100%)"
                text_col = ("#065F46", "#34D399")
                bar_val = 1.0
            elif active_count > 0 and completed_count > 0:
                count_text = f"{active_count} active • {completed_count} done ({comp_pct}%)"
                text_col = info["text"][0] if ctk.get_appearance_mode() == "Light" else info["text"][1]
                bar_val = comp_pct / 100.0
            else:
                count_text = f"{active_count} active tasks"
                text_col = info["text"][0] if ctk.get_appearance_mode() == "Light" else info["text"][1]
                bar_val = 0.0

            lbl_q_count = ctk.CTkLabel(
                q_inner,
                text=count_text,
                font=(theme.FONT_FAMILY, 13, "bold"),
                text_color=text_col,
            )
            lbl_q_count.pack(side="right")

            # Proportional mini progress bar
            bar_track = ctk.CTkProgressBar(
                q_card,
                height=4,
                corner_radius=2,
                fg_color=("#E5E0D8", "#222222"),
                progress_color="#10B981" if (active_count == 0 and completed_count > 0) else info["color"],
            )
            bar_track.pack(fill="x", padx=16, pady=(0, 8))
            bar_track.set(bar_val)

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Refreshes matrix statistics and focus analytics with fresh task & session data."""
        self.tasks = tasks
        saved_scope = getattr(self, "time_scope", "week")
        for child in self.winfo_children():
            child.destroy()
        self.time_scope = saved_scope
        self._build_ui()
