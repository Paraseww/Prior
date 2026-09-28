"""
ui/splash_view.py
First-time onboarding splash screen for Prior.
Provides friendly name customization, theme preference, and smooth transition to workspace.
"""

from pathlib import Path
from typing import Callable
import customtkinter as ctk

import database
from ui import theme


class SplashView(ctk.CTkFrame):
    """
    Onboarding Splash View displayed on first launch.
    """

    def __init__(self, master: ctk.CTk, on_complete: Callable[[], None], **kwargs) -> None:
        super().__init__(master, fg_color=theme.BG_MAIN, **kwargs)
        self.on_complete = on_complete

        self._build_ui()

    def _build_ui(self) -> None:
        # Centered container card
        card = ctk.CTkFrame(
            self,
            fg_color=theme.BG_CARD,
            corner_radius=20,
            border_width=1,
            border_color=theme.BORDER_COLOR,
            width=520,
            height=580,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # Decorative Top Logo (Figma icon or Styled Badge)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            from PIL import Image
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(84, 84))
            lbl_logo_img = ctk.CTkLabel(card, image=ctk_img, text="")
            lbl_logo_img.pack(pady=(35, 10))
        else:
            logo_frame = ctk.CTkFrame(
                card,
                width=84,
                height=84,
                corner_radius=42,
                fg_color=theme.ACCENT_PRIMARY,
            )
            logo_frame.pack(pady=(35, 10))
            logo_frame.pack_propagate(False)

            logo_label = ctk.CTkLabel(
                logo_frame,
                text="P",
                font=(theme.FONT_DISPLAY, 40, "bold"),
                text_color="#FFFFFF",
            )
            logo_label.place(relx=0.5, rely=0.5, anchor="center")

        # App Title & Tagline
        title = ctk.CTkLabel(
            card,
            text="Prior.",
            font=(theme.FONT_DISPLAY, 32, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        title.pack(pady=(0, 6))

        tagline = ctk.CTkLabel(
            card,
            text="Organize your tasks, focus on what matters,\nand turn priorities into progress.",
            font=(theme.FONT_FAMILY, 14),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        )
        tagline.pack(pady=(0, 30))

        # Name Entry Field
        name_label = ctk.CTkLabel(
            card,
            text="What should we call you?",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        name_label.pack(fill="x", padx=55, pady=(0, 6))

        self.name_entry = ctk.CTkEntry(
            card,
            placeholder_text="e.g. Alex",
            font=(theme.FONT_FAMILY, 14),
            height=42,
            corner_radius=10,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
        )
        self.name_entry.pack(fill="x", padx=55, pady=(0, 20))
        self.name_entry.insert(0, "Alex")

        # Theme Preference Selector
        theme_label = ctk.CTkLabel(
            card,
            text="Preferred Theme",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        theme_label.pack(fill="x", padx=55, pady=(0, 6))

        self.theme_segment = ctk.CTkSegmentedButton(
            card,
            values=["Dark Mode", "Light Mode"],
            font=(theme.FONT_FAMILY, 13),
            height=36,
            corner_radius=8,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_HOVER,
            command=self._on_theme_toggle,
        )
        self.theme_segment.pack(fill="x", padx=55, pady=(0, 35))
        self.theme_segment.set("Dark Mode")

        # Get Started CTA Button
        btn_start = ctk.CTkButton(
            card,
            text="Let's Get Started →",
            font=(theme.FONT_FAMILY, 15, "bold"),
            height=46,
            corner_radius=12,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._save_and_continue,
        )
        btn_start.pack(fill="x", padx=55, pady=(0, 20))

    def _on_theme_toggle(self, value: str) -> None:
        mode = "dark" if value == "Dark Mode" else "light"
        ctk.set_appearance_mode(mode)

    def _save_and_continue(self) -> None:
        user_name = self.name_entry.get().strip() or "User"
        selected_theme = "dark" if self.theme_segment.get() == "Dark Mode" else "light"

        # Update database profile
        database.update_profile(
            name=user_name,
            theme=selected_theme,
            onboarding_completed=1,
        )

        # Notify parent window to show workspace
        self.on_complete()
