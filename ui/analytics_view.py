"""
ui/analytics_view.py
Productivity analytics and Eisenhower Focus Score dashboard for Prior.
"""

from typing import Any, Dict, List
import customtkinter as ctk

from project import calculate_matrix_stats
from ui import theme
from ui.dot_pattern import DottedScrollableFrame


class AnalyticsView(DottedScrollableFrame):
    """
    Productivity Analytics & Eisenhower Distribution Dashboard with dot-matrix canvas.
    """

    def __init__(self, master: Any, tasks: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.tasks = tasks

        self._build_ui()

    def _build_ui(self) -> None:
        stats = calculate_matrix_stats(self.tasks)

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
            text="Insights into your task distribution, completion velocity, and proactive planning score.",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 20))

        # Top 3 Metrics Cards Row
        cards_row = ctk.CTkFrame(container, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, 20))

        # 1. Total Tasks Card
        card_total = self._create_metric_card(
            cards_row,
            title="Total Tasks",
            value=str(stats["total_tasks"]),
            subtitle=f"{stats['completed_tasks']} completed • {stats['pending_tasks']} pending",
            accent_color=theme.ACCENT_PRIMARY,
        )
        card_total.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 2. Completion Rate Card
        card_comp = self._create_metric_card(
            cards_row,
            title="Completion Rate",
            value=f"{stats['completion_rate']}%",
            subtitle="Overall tasks completed",
            accent_color="#10B981",
        )
        card_comp.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 3. Proactive Focus Score Card
        card_focus = self._create_metric_card(
            cards_row,
            title="Focus Score (Q2 Schedule)",
            value=f"{stats['focus_score']}%",
            subtitle="Proactive planning index",
            accent_color="#3B82F6",
        )
        card_focus.pack(side="left", fill="both", expand=True)

        # Quadrant Distribution Section
        lbl_dist = ctk.CTkLabel(
            container,
            text="Eisenhower Matrix Active Task Distribution",
            font=(theme.FONT_DISPLAY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_dist.pack(fill="x", pady=(10, 10))

        q_grid = ctk.CTkFrame(container, fg_color="transparent")
        q_grid.pack(fill="x", pady=(0, 20))

        quadrant_keys = ["Q1_DO", "Q2_SCHEDULE", "Q3_DELEGATE", "Q4_ELIMINATE"]
        for i, q_key in enumerate(quadrant_keys):
            info = theme.QUADRANTS[q_key]
            count = stats["quadrant_counts"].get(q_key, 0)
            pending_total = stats["pending_tasks"]
            pct = round((count / pending_total) * 100.0, 1) if pending_total > 0 else 0.0

            q_card = ctk.CTkFrame(
                q_grid,
                fg_color=theme.BG_CARD,
                corner_radius=12,
                border_width=1,
                border_color=info["border"],
            )
            q_card.pack(fill="x", pady=6)

            q_inner = ctk.CTkFrame(q_card, fg_color="transparent")
            q_inner.pack(fill="x", padx=16, pady=12)

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

            lbl_q_count = ctk.CTkLabel(
                q_inner,
                text=f"{count} active tasks ({pct}%)",
                font=(theme.FONT_FAMILY, 13, "bold"),
                text_color=info["text"][0] if ctk.get_appearance_mode() == "Light" else info["text"][1],
            )
            lbl_q_count.pack(side="right")

    def _create_metric_card(
        self,
        master: Any,
        title: str,
        value: str,
        subtitle: str,
        accent_color: str,
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

        lbl_t = ctk.CTkLabel(inner, text=title, font=(theme.FONT_FAMILY, 12, "bold"), text_color=theme.TEXT_SECONDARY, anchor="w")
        lbl_t.pack(fill="x")

        lbl_v = ctk.CTkLabel(inner, text=value, font=(theme.FONT_DISPLAY, 26, "bold"), text_color=accent_color, anchor="w")
        lbl_v.pack(fill="x", pady=(2, 2))

        lbl_s = ctk.CTkLabel(inner, text=subtitle, font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w")
        lbl_s.pack(fill="x")

        return card

    def refresh_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        self.tasks = tasks
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
