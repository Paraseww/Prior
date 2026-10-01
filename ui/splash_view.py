"""
ui/splash_view.py
Creative, organic-shaped, and interactive four-step onboarding flow for Prior:
Step 1: Clean Wireframe Welcome screen with custom 4-circle icon and 'Let's Get Started'.
Step 2: Dynamic Dual-Orb Concept Explorer: The Clock (Urgent) vs. The Compass (Important).
Step 3: 4-Quadrant Capsule Grid with vibrant circular orb avatars and interactive Q2 focus banner.
Step 4: Friendly personalization screen ('Hi there! What should we call you?') and theme selector.
"""

from pathlib import Path
from typing import Any, Callable, Dict
import customtkinter as ctk
from PIL import Image

import database
from ui import theme
from ui.dot_pattern import DottedFrame


class SplashView(DottedFrame):
    """
    Four-step interactive onboarding controller with dot-grid canvas.
    Uses circular orbs, capsule pods, and dynamic shapes instead of plain square boxes.
    """

    def __init__(self, master: Any, on_complete: Callable[[], None], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.on_complete = on_complete

        # Interactive states
        self.active_concept: str = "importance"
        self.selected_quadrant: str = "Q2"

        # Theme & profile persistence
        profile = database.get_profile()
        saved_theme = profile.get("theme", "dark")
        self.selected_theme: str = saved_theme
        saved_name = profile.get("name", "")
        self.entered_name: str = saved_name if saved_name != "User" else ""

        # Container for screens
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # Start on Step 1 (Welcome Screen)
        self._show_welcome_screen()

    # ========================================================================
    # Step 1: Welcome Screen
    # ========================================================================

    def _show_welcome_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        center_container = ctk.CTkFrame(self.container, fg_color="transparent")
        center_container.place(relx=0.5, rely=0.46, anchor="center")

        # Hero Header Row: [ Custom 4-Circle Icon ] + [ "Prior." Title ]
        hero_row = ctk.CTkFrame(center_container, fg_color="transparent")
        hero_row.pack(pady=(0, 36))

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(110, 110))
            lbl_icon = ctk.CTkLabel(hero_row, image=ctk_img, text="")
            lbl_icon.pack(side="left", padx=(0, 20))
        else:
            circle_frame = ctk.CTkFrame(
                hero_row,
                width=110,
                height=110,
                corner_radius=55,
                fg_color=("#CBD5E1", "#1E1E1E"),
                border_width=2,
                border_color=("#1E293B", "#333333"),
            )
            circle_frame.pack(side="left", padx=(0, 20))
            circle_frame.pack_propagate(False)

        lbl_title = ctk.CTkLabel(
            hero_row,
            text="Prior.",
            font=(theme.FONT_FAMILY, 54, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_title.pack(side="left", pady=10)

        # Tagline
        tagline_text = (
            "organize your tasks, focus on what matters, and turn\n"
            "priorities into progress"
        )
        lbl_tagline = ctk.CTkLabel(
            center_container,
            text=tagline_text,
            font=(theme.FONT_FAMILY, 19),
            text_color=theme.TEXT_PRIMARY,
            justify="center",
        )
        lbl_tagline.pack(pady=(0, 48))

        # "Let's Get Started" Button
        btn_start = ctk.CTkButton(
            center_container,
            text="Let's Get Started  →",
            font=(theme.FONT_FAMILY, 17, "bold"),
            width=260,
            height=52,
            corner_radius=14,
            border_width=2,
            border_color=("#1E293B", "#333333"),
            fg_color=("#D1D5DB", "#1E1E1E"),
            hover_color=("#9CA3AF", "#2A2A2A"),
            text_color=("#0F172A", "#FFFFFF"),
            command=self._show_matrix_concept_screen,
        )
        btn_start.pack()

    # ========================================================================
    # Step 2: Dynamic Dual-Orb Concept Screen (Circles & Pills)
    # ========================================================================

    def _show_matrix_concept_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self.container,
            fg_color=theme.BG_CARD,
            corner_radius=24,
            border_width=2,
            border_color=theme.BORDER_COLOR,
            width=780,
            height=550,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=38, pady=24)

        # Step Capsule Pill
        pill_step = ctk.CTkFrame(inner, fg_color=theme.BG_INPUT, corner_radius=12, height=24)
        pill_step.pack(anchor="w", pady=(0, 4))
        lbl_step = ctk.CTkLabel(
            pill_step,
            text="  STEP 2 OF 4  •  THE TWO FORCES  ",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.ACCENT_PRIMARY,
        )
        lbl_step.pack(padx=8, pady=2)

        # Title & Subtitle
        lbl_title = ctk.CTkLabel(
            inner,
            text="Not all tasks are created equal.",
            font=(theme.FONT_FAMILY, 26, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            inner,
            text="Click an orb to see how Urgency and Importance pull your attention:",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 14))

        # ====================================================================
        # Dynamic Shape Stage: Dual Orbs + VS Pill Connector
        # ====================================================================
        stage_row = ctk.CTkFrame(inner, fg_color="transparent")
        stage_row.pack(fill="x", pady=(0, 16))
        stage_row.columnconfigure(0, weight=1)
        stage_row.columnconfigure(1, weight=0)
        stage_row.columnconfigure(2, weight=1)

        def _select_force(force: str) -> None:
            self.active_concept = force
            self._show_matrix_concept_screen()

        # Orb 1 (Urgency - The Clock)
        is_urg = (self.active_concept == "urgency")
        col_urg = ctk.CTkFrame(stage_row, fg_color="transparent")
        col_urg.grid(row=0, column=0)

        orb_urg = ctk.CTkFrame(
            col_urg,
            width=124,
            height=124,
            corner_radius=62,
            fg_color=("#FEF3C7", "#271704") if is_urg else theme.BG_INPUT,
            border_width=3 if is_urg else 1.5,
            border_color="#F59E0B" if is_urg else theme.BORDER_COLOR,
            cursor="hand2",
        )
        orb_urg.pack(pady=(0, 8))
        orb_urg.pack_propagate(False)

        lbl_urg_content = ctk.CTkLabel(
            orb_urg,
            text="⚡\nURGENT\nThe Clock",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color="#F59E0B" if is_urg else theme.TEXT_PRIMARY,
            justify="center",
        )
        lbl_urg_content.place(relx=0.5, rely=0.5, anchor="center")

        pill_urg_tag = ctk.CTkFrame(
            col_urg,
            corner_radius=12,
            fg_color=("#FDE68A", "#452405") if is_urg else theme.BG_INPUT,
            height=26,
            cursor="hand2",
        )
        pill_urg_tag.pack()
        lbl_urg_tag = ctk.CTkLabel(
            pill_urg_tag,
            text="“Demands Time NOW”",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color="#B45309" if is_urg else theme.TEXT_MUTED,
        )
        lbl_urg_tag.pack(padx=10, pady=3)

        # Center Connector (VS Pill)
        vs_container = ctk.CTkFrame(stage_row, fg_color="transparent")
        vs_container.grid(row=0, column=1, padx=12)

        pill_vs = ctk.CTkFrame(
            vs_container,
            width=48,
            height=32,
            corner_radius=16,
            fg_color=theme.BG_INPUT,
            border_width=1.5,
            border_color=theme.BORDER_COLOR,
        )
        pill_vs.pack(pady=40)
        pill_vs.pack_propagate(False)
        lbl_vs = ctk.CTkLabel(
            pill_vs,
            text="VS",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_MUTED,
        )
        lbl_vs.place(relx=0.5, rely=0.5, anchor="center")

        # Orb 2 (Importance - The Compass)
        is_imp = (self.active_concept == "importance")
        col_imp = ctk.CTkFrame(stage_row, fg_color="transparent")
        col_imp.grid(row=0, column=2)

        orb_imp = ctk.CTkFrame(
            col_imp,
            width=124,
            height=124,
            corner_radius=62,
            fg_color=("#ECFDF5", "#04261B") if is_imp else theme.BG_INPUT,
            border_width=3 if is_imp else 1.5,
            border_color="#10B981" if is_imp else theme.BORDER_COLOR,
            cursor="hand2",
        )
        orb_imp.pack(pady=(0, 8))
        orb_imp.pack_propagate(False)

        lbl_imp_content = ctk.CTkLabel(
            orb_imp,
            text="🎯\nIMPORTANT\nThe Compass",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color="#10B981" if is_imp else theme.TEXT_PRIMARY,
            justify="center",
        )
        lbl_imp_content.place(relx=0.5, rely=0.5, anchor="center")

        pill_imp_tag = ctk.CTkFrame(
            col_imp,
            corner_radius=12,
            fg_color=("#A7F3D0", "#064E3B") if is_imp else theme.BG_INPUT,
            height=26,
            cursor="hand2",
        )
        pill_imp_tag.pack()
        lbl_imp_tag = ctk.CTkLabel(
            pill_imp_tag,
            text="“Builds Your FUTURE”",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color="#047857" if is_imp else theme.TEXT_MUTED,
        )
        lbl_imp_tag.pack(padx=10, pady=3)

        # Click bindings for orbs and labels
        for w in (orb_urg, lbl_urg_content, pill_urg_tag, lbl_urg_tag):
            w.bind("<Button-1>", lambda _: _select_force("urgency"))
        for w in (orb_imp, lbl_imp_content, pill_imp_tag, lbl_imp_tag):
            w.bind("<Button-1>", lambda _: _select_force("importance"))

        # ====================================================================
        # Interactive Capsule Insight Card (Smooth Rounded Capsule)
        # ====================================================================
        capsule_color = ("#FFFBEB", "#231503") if is_urg else ("#ECFDF5", "#032318")
        capsule_border = "#F59E0B" if is_urg else "#10B981"
        capsule_insight = ctk.CTkFrame(
            inner,
            fg_color=capsule_color,
            corner_radius=18,
            border_width=1.5,
            border_color=capsule_border,
            height=80,
        )
        capsule_insight.pack(fill="x", pady=(0, 14))
        capsule_insight.pack_propagate(False)

        ci_inner = ctk.CTkFrame(capsule_insight, fg_color="transparent")
        ci_inner.pack(fill="both", expand=True, padx=18, pady=10)

        active_title = (
            "⚡ The Urgency Trap" if is_urg else "🎯 The Importance Superpower"
        )
        active_body = (
            "Urgent matters scream through deadlines, notifications, and crises. They trick you into feeling busy, but reacting all day burns you out without building your own dreams."
            if is_urg else
            "Important matters are quiet: learning skills, deep health, strategic planning, and relationships. They never scream for attention, but they create 90% of your real life success."
        )

        lbl_ins_head = ctk.CTkLabel(
            ci_inner,
            text=active_title,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color="#F59E0B" if is_urg else "#10B981",
            anchor="w",
        )
        lbl_ins_head.pack(fill="x", pady=(0, 2))

        lbl_ins_body = ctk.CTkLabel(
            ci_inner,
            text=active_body,
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=680,
        )
        lbl_ins_body.pack(fill="x")

        # Bottom Bridge Pill
        bridge_pill = ctk.CTkFrame(
            inner,
            fg_color=("#F3E8FF", "#180F23"),
            corner_radius=14,
            border_width=1,
            border_color=("#D8B4FE", "#581C87"),
            height=34,
        )
        bridge_pill.pack(fill="x", pady=(0, 16))
        bridge_pill.pack_propagate(False)

        lbl_bridge = ctk.CTkLabel(
            bridge_pill,
            text="✨ Prior merges Urgency and Importance into 4 Action Zones so you always know your next winning move.",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=("#6B21A8", "#E9D5FF"),
        )
        lbl_bridge.place(relx=0.5, rely=0.5, anchor="center")

        # Bottom Navigation
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        btn_back = ctk.CTkButton(
            btn_row,
            text="← Back",
            font=(theme.FONT_FAMILY, 14),
            width=100,
            height=46,
            corner_radius=14,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._show_welcome_screen,
        )
        btn_back.pack(side="left", padx=(0, 10))

        btn_next = ctk.CTkButton(
            btn_row,
            text="Next: Meet the 4 Quadrants  →",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=46,
            corner_radius=14,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._show_quadrants_screen,
        )
        btn_next.pack(side="right", fill="x", expand=True)

    # ========================================================================
    # Step 3: Creative 4-Quadrant Capsule Grid with Circular Orb Avatars
    # ========================================================================

    def _show_quadrants_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self.container,
            fg_color=theme.BG_CARD,
            corner_radius=24,
            border_width=2,
            border_color=theme.BORDER_COLOR,
            width=800,
            height=560,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=34, pady=20)

        # Step Capsule Pill
        pill_step = ctk.CTkFrame(inner, fg_color=theme.BG_INPUT, corner_radius=12, height=24)
        pill_step.pack(anchor="w", pady=(0, 4))
        lbl_step = ctk.CTkLabel(
            pill_step,
            text="  STEP 3 OF 4  •  THE 4 ACTION ZONES  ",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.ACCENT_PRIMARY,
        )
        lbl_step.pack(padx=8, pady=2)

        # Title & Subtitle
        lbl_title = ctk.CTkLabel(
            inner,
            text="The 4 Action Quadrants",
            font=(theme.FONT_FAMILY, 26, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            inner,
            text="Tap any quadrant to explore where your tasks belong:",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 12))

        # Quadrant Specs with Colored Orbs and exact required content
        quadrant_specs: Dict[str, Dict[str, Any]] = {
            "Q1": {
                "name": "Do First",
                "meta": "(Urgent & Important)",
                "desc": "Tasks requiring immediate attention, such as crises or deadlines.",
                "color": "#EF4444",  # Red
                "bg_active": ("#FEF2F2", "#290A0A"),
                "badge": "⚡ DO NOW",
                "icon": "🔥",
            },
            "Q2": {
                "name": "Schedule",
                "meta": "(Important & Not Urgent)",
                "desc": "Long-term goals and strategic planning that should be time-blocked.",
                "color": "#10B981",  # Green
                "bg_active": ("#ECFDF5", "#032419"),
                "badge": "⭐ GROWTH ZONE",
                "icon": "🌱",
            },
            "Q3": {
                "name": "Delegate",
                "meta": "(Urgent & Not Important)",
                "desc": "Interruptions or routine tasks that can be handed off to others.",
                "color": "#F59E0B",  # Orange / Amber
                "bg_active": ("#FFFBEB", "#251602"),
                "badge": "🤝 HAND OFF",
                "icon": "🤝",
            },
            "Q4": {
                "name": "Delete",
                "meta": "(Not Urgent & Not Important)",
                "desc": "Distractions and time-wasters that should be eliminated.",
                "color": "#3B82F6",  # Blue
                "bg_active": ("#EFF6FF", "#041630"),
                "badge": "🗑️ DROP IT",
                "icon": "🗑",
            },
        }

        # 2x2 Capsule Pod Grid
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 12))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        coords = {
            "Q1": (0, 0),
            "Q2": (0, 1),
            "Q3": (1, 0),
            "Q4": (1, 1),
        }

        def _select_quad(qid: str) -> None:
            self.selected_quadrant = qid
            self._show_quadrants_screen()

        # Render 4 Organic Capsule Pods with Solid Colored Orbs
        for qid, q in quadrant_specs.items():
            r, c = coords[qid]
            is_active = (self.selected_quadrant == qid)

            bg_c = q["bg_active"] if is_active else theme.BG_INPUT
            border_c = q["color"] if is_active else theme.BORDER_COLOR
            border_w = 2.5 if is_active else 1.5

            # Capsule Container with rounded corners
            pod = ctk.CTkFrame(
                grid,
                fg_color=bg_c,
                corner_radius=20,
                border_width=border_w,
                border_color=border_c,
                height=110,
                cursor="hand2",
            )
            pod.grid(row=r, column=c, padx=(0, 6) if c == 0 else (6, 0), pady=(0, 6) if r == 0 else (6, 0), sticky="nsew")
            pod.pack_propagate(False)

            # Left side: Solid Circular Orb Avatar
            orb_avatar = ctk.CTkFrame(
                pod,
                width=52,
                height=52,
                corner_radius=26,
                fg_color=q["color"],
                border_width=2 if is_active else 0,
                border_color="#FFFFFF" if is_active else q["color"],
            )
            orb_avatar.pack(side="left", padx=(14, 10))
            orb_avatar.pack_propagate(False)

            # Dedicated Emoji Icon Label (cleanly centered on upper half)
            lbl_orb_icon = ctk.CTkLabel(
                orb_avatar,
                text=q["icon"],
                font=("Segoe UI Emoji", 14),
                text_color="#FFFFFF",
            )
            lbl_orb_icon.place(relx=0.5, rely=0.34, anchor="center")

            # Dedicated Q-Number Label (cleanly centered on lower half)
            lbl_orb_qid = ctk.CTkLabel(
                orb_avatar,
                text=qid,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color="#FFFFFF",
            )
            lbl_orb_qid.place(relx=0.5, rely=0.72, anchor="center")

            # Right side content
            info_frame = ctk.CTkFrame(pod, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=10)

            # Top row: Title + Meta Pill + Badge
            top_line = ctk.CTkFrame(info_frame, fg_color="transparent")
            top_line.pack(fill="x", pady=(0, 4))

            lbl_name = ctk.CTkLabel(
                top_line,
                text=q["name"],
                font=(theme.FONT_FAMILY, 15, "bold"),
                text_color=theme.TEXT_PRIMARY,
                anchor="w",
            )
            lbl_name.pack(side="left", padx=(0, 6))

            lbl_meta = ctk.CTkLabel(
                top_line,
                text=q["meta"],
                font=(theme.FONT_FAMILY, 10),
                text_color=theme.TEXT_MUTED,
                anchor="w",
            )
            lbl_meta.pack(side="left")

            if is_active:
                lbl_badge = ctk.CTkLabel(
                    top_line,
                    text=q["badge"],
                    font=(theme.FONT_FAMILY, 9, "bold"),
                    text_color=q["color"],
                    anchor="e",
                )
                lbl_badge.pack(side="right")

            # 1-Line Description
            lbl_desc = ctk.CTkLabel(
                info_frame,
                text=q["desc"],
                font=(theme.FONT_FAMILY, 11),
                text_color=theme.TEXT_PRIMARY if is_active else theme.TEXT_SECONDARY,
                justify="left",
                anchor="w",
                wraplength=270,
            )
            lbl_desc.pack(fill="x")

            # Click binding to all pod elements
            for w in (pod, orb_avatar, lbl_orb_icon, lbl_orb_qid, info_frame, top_line, lbl_name, lbl_meta, lbl_desc):
                w.bind("<Button-1>", lambda _, k=qid: _select_quad(k))

        # ====================================================================
        # Highlight Capsule: The Quadrant 2 Golden Takeaway
        # ====================================================================
        capsule_takeaway = ctk.CTkFrame(
            inner,
            fg_color=("#ECFDF5", "#032419"),
            corner_radius=16,
            border_width=1.5,
            border_color=("#A7F3D0", "#065F46"),
            height=54,
        )
        capsule_takeaway.pack(fill="x", pady=(0, 16))
        capsule_takeaway.pack_propagate(False)

        ct_inner = ctk.CTkFrame(capsule_takeaway, fg_color="transparent")
        ct_inner.pack(fill="both", expand=True, padx=16, pady=8)

        lbl_takeaway = ctk.CTkLabel(
            ct_inner,
            text="💡 By systematically categorizing tasks, the matrix encourages focusing on Quadrant 2 activities, which drive significant results without the pressure of immediate deadlines.",
            font=(theme.FONT_FAMILY, 11),
            text_color=("#065F46", "#34D399"),
            justify="left",
            anchor="w",
            wraplength=700,
        )
        lbl_takeaway.pack(fill="x")

        # Bottom Navigation
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        btn_back = ctk.CTkButton(
            btn_row,
            text="← Back",
            font=(theme.FONT_FAMILY, 14),
            width=100,
            height=46,
            corner_radius=14,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._show_matrix_concept_screen,
        )
        btn_back.pack(side="left", padx=(0, 10))

        btn_next = ctk.CTkButton(
            btn_row,
            text="Next: Personalize Prior  →",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=46,
            corner_radius=14,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._show_name_setup_screen,
        )
        btn_next.pack(side="right", fill="x", expand=True)

    # ========================================================================
    # Step 4: Name Personalization & Theme Screen
    # ========================================================================

    def _show_name_setup_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self.container,
            fg_color=theme.BG_CARD,
            corner_radius=24,
            border_width=2,
            border_color=theme.BORDER_COLOR,
            width=480,
            height=510,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=30)

        # Step Pill
        pill_step = ctk.CTkFrame(inner, fg_color=theme.BG_INPUT, corner_radius=12, height=24)
        pill_step.pack(anchor="center", pady=(0, 6))
        lbl_step = ctk.CTkLabel(
            pill_step,
            text="  STEP 4 OF 4  •  PERSONALIZATION  ",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.ACCENT_PRIMARY,
        )
        lbl_step.pack(padx=8, pady=2)

        # Small Top Logo
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(48, 48))
            lbl_logo = ctk.CTkLabel(inner, image=ctk_img, text="")
            lbl_logo.pack(pady=(0, 6))

        # Greeting Title
        lbl_greeting = ctk.CTkLabel(
            inner,
            text="Hi there! 👋",
            font=(theme.FONT_FAMILY, 26, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_greeting.pack(pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            inner,
            text="How should we call you in Prior?",
            font=(theme.FONT_FAMILY, 15),
            text_color=theme.TEXT_SECONDARY,
        )
        lbl_sub.pack(pady=(0, 18))

        # Name Entry Box
        self.name_entry = ctk.CTkEntry(
            inner,
            placeholder_text="Enter your name...",
            font=(theme.FONT_FAMILY, 16),
            height=46,
            corner_radius=14,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            border_width=2,
        )
        self.name_entry.pack(fill="x", pady=(0, 4))
        if self.entered_name:
            self.name_entry.insert(0, self.entered_name)
        self.name_entry.focus_set()
        self.name_entry.bind("<KeyRelease>", self._on_name_typed)
        self.name_entry.bind("<Return>", lambda _: self._save_and_launch())

        # Error validation label
        self.lbl_error = ctk.CTkLabel(
            inner,
            text="",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=("#EF4444", "#F87171"),
            anchor="w",
            height=18,
        )
        self.lbl_error.pack(fill="x", pady=(0, 10))

        # Theme Selector
        lbl_theme = ctk.CTkLabel(
            inner,
            text="Choose your preferred theme",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_theme.pack(fill="x", pady=(0, 6))

        self.theme_segment = ctk.CTkSegmentedButton(
            inner,
            values=["Dark Mode", "Light Mode"],
            font=(theme.FONT_FAMILY, 13),
            height=38,
            corner_radius=12,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_HOVER,
            command=self._on_theme_toggle,
        )
        self.theme_segment.pack(fill="x", pady=(0, 20))
        current_mode = ctk.get_appearance_mode().lower()
        active_val = "Light Mode" if current_mode == "light" or self.selected_theme == "light" else "Dark Mode"
        self.theme_segment.set(active_val)

        # Action Buttons: Back + Continue
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x")

        btn_back = ctk.CTkButton(
            btn_row,
            text="← Back",
            font=(theme.FONT_FAMILY, 14),
            width=90,
            height=44,
            corner_radius=14,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._show_quadrants_screen,
        )
        btn_back.pack(side="left", padx=(0, 10))

        btn_continue = ctk.CTkButton(
            btn_row,
            text="Continue to Workspace →",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=44,
            corner_radius=14,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._save_and_launch,
        )
        btn_continue.pack(side="right", fill="x", expand=True)

    def _on_name_typed(self, _: Any) -> None:
        """Clears validation error and stores typed name."""
        self.entered_name = self.name_entry.get().strip()
        self.name_entry.configure(border_color=theme.BORDER_COLOR)
        self.lbl_error.configure(text="")

    def _on_theme_toggle(self, value: str) -> None:
        mode = "dark" if value == "Dark Mode" else "light"
        ctk.set_appearance_mode(mode)
        self.selected_theme = mode
        database.update_profile(theme=mode)

    def _save_and_launch(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            self.name_entry.configure(border_color="#EF4444")
            self.lbl_error.configure(text="⚠️ Please enter your name to continue")
            self.name_entry.focus_set()
            return

        selected_theme = "dark" if self.theme_segment.get() == "Dark Mode" else "light"

        # Update profile in SQLite
        database.update_profile(
            name=name,
            theme=selected_theme,
            onboarding_completed=1,
        )

        # Notify parent app to transition to workspace
        self.on_complete()
