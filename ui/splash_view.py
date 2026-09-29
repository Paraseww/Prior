"""
ui/splash_view.py
Two-step onboarding flow for Prior:
Step 1: Clean Wireframe Welcome screen with custom 4-circle icon and 'Let's Get Started'.
Step 2: Friendly personalization screen ('Hi there! What should we call you?') and theme selector.
"""

from pathlib import Path
from typing import Any, Callable
import customtkinter as ctk
from PIL import Image

import database
from ui import theme
from ui.dot_pattern import DottedFrame


class SplashView(DottedFrame):
    """
    Two-step onboarding splash controller with dot-grid canvas.
    """

    def __init__(self, master: Any, on_complete: Callable[[], None], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.on_complete = on_complete

        # Container for screens
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # Start on Step 1 (Welcome Screen)
        self._show_welcome_screen()

    # ========================================================================
    # Step 1: Welcome Screen (Matches Wireframe Drawing)
    # ========================================================================

    def _show_welcome_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        center_container = ctk.CTkFrame(self.container, fg_color="transparent")
        center_container.place(relx=0.5, rely=0.46, anchor="center")

        # 1. Hero Header Row: [ Custom 4-Circle Icon ] + [ "Prior." Title ]
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

        # 2. Tagline (2 lines, centered)
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

        # 3. "Let's Get Started" Wireframe Button
        btn_start = ctk.CTkButton(
            center_container,
            text="Let's Get Started",
            font=(theme.FONT_FAMILY, 17, "bold"),
            width=260,
            height=52,
            corner_radius=14,
            border_width=2,
            border_color=("#1E293B", "#333333"),
            fg_color=("#D1D5DB", "#1E1E1E"),
            hover_color=("#9CA3AF", "#2A2A2A"),
            text_color=("#0F172A", "#FFFFFF"),
            command=self._show_name_setup_screen,
        )
        btn_start.pack()

    # ========================================================================
    # Step 2: Name Personalization & Theme Screen
    # ========================================================================

    def _show_name_setup_screen(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self.container,
            fg_color=theme.BG_CARD,
            corner_radius=20,
            border_width=2,
            border_color=theme.BORDER_COLOR,
            width=480,
            height=500,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=35)

        # Small Top Logo
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(52, 52))
            lbl_logo = ctk.CTkLabel(inner, image=ctk_img, text="")
            lbl_logo.pack(pady=(0, 10))

        # Greeting Title
        lbl_greeting = ctk.CTkLabel(
            inner,
            text="Hi there! 👋",
            font=(theme.FONT_FAMILY, 28, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        lbl_greeting.pack(pady=(0, 4))

        lbl_sub = ctk.CTkLabel(
            inner,
            text="How should we call you in Prior?",
            font=(theme.FONT_FAMILY, 16),
            text_color=theme.TEXT_SECONDARY,
        )
        lbl_sub.pack(pady=(0, 24))

        # Name Entry Box
        self.name_entry = ctk.CTkEntry(
            inner,
            placeholder_text="Enter your name...",
            font=(theme.FONT_FAMILY, 16),
            height=46,
            corner_radius=12,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            border_width=2,
        )
        self.name_entry.pack(fill="x", pady=(0, 4))
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
        self.lbl_error.pack(fill="x", pady=(0, 14))

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
            corner_radius=10,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_HOVER,
            command=self._on_theme_toggle,
        )
        self.theme_segment.pack(fill="x", pady=(0, 24))
        self.theme_segment.set("Dark Mode")

        # Action Buttons: Back + Continue
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x")

        btn_back = ctk.CTkButton(
            btn_row,
            text="← Back",
            font=(theme.FONT_FAMILY, 14),
            width=90,
            height=44,
            corner_radius=12,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._show_welcome_screen,
        )
        btn_back.pack(side="left", padx=(0, 10))

        btn_continue = ctk.CTkButton(
            btn_row,
            text="Continue to Workspace →",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=44,
            corner_radius=12,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._save_and_launch,
        )
        btn_continue.pack(side="right", fill="x", expand=True)

    def _on_name_typed(self, _: Any) -> None:
        """Clears validation error when user begins typing."""
        self.name_entry.configure(border_color=theme.BORDER_COLOR)
        self.lbl_error.configure(text="")

    def _on_theme_toggle(self, value: str) -> None:
        mode = "dark" if value == "Dark Mode" else "light"
        ctk.set_appearance_mode(mode)

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
