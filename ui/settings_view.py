"""
ui/settings_view.py
Settings and preferences view for Prior.
Allows customizing display name, appearance theme, startup preferences, and database management.
"""

from typing import Any, Callable, Dict
import customtkinter as ctk

import database
from ui import theme
from ui.dot_pattern import DottedScrollableFrame


class SettingsView(DottedScrollableFrame):
    """
    Settings & User Preferences panel with dot-matrix canvas.
    """

    def __init__(
        self,
        master: Any,
        profile: Dict[str, Any],
        on_profile_updated: Callable[[], None],
        on_data_cleared: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.profile = profile
        self.on_profile_updated = on_profile_updated
        self.on_data_cleared = on_data_cleared

        self._build_ui()

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=15)

        # Header Title
        lbl_head = ctk.CTkLabel(
            container,
            text="Application Settings & Preferences",
            font=(theme.FONT_DISPLAY, 22, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_head.pack(fill="x", pady=(0, 4))

        lbl_sub = ctk.CTkLabel(
            container,
            text="Customize your profile, visual appearance, and data preferences.",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 20))

        # ====================================================================
        # 1. Profile Customization Section
        # ====================================================================
        sec_profile = self._create_section(container, "User Profile")

        lbl_name = ctk.CTkLabel(sec_profile, text="Display Name", font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY, anchor="w")
        lbl_name.pack(fill="x", pady=(0, 4))

        name_row = ctk.CTkFrame(sec_profile, fg_color="transparent")
        name_row.pack(fill="x", pady=(0, 10))

        self.entry_name = ctk.CTkEntry(
            name_row,
            font=(theme.FONT_FAMILY, 13),
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
            width=260,
        )
        self.entry_name.pack(side="left", padx=(0, 10))
        self.entry_name.insert(0, self.profile.get("name", "User"))

        btn_save_name = ctk.CTkButton(
            name_row,
            text="Update Name",
            font=(theme.FONT_FAMILY, 12, "bold"),
            height=36,
            corner_radius=8,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._on_save_name,
        )
        btn_save_name.pack(side="left")

        # ====================================================================
        # 2. Appearance & Theme Section
        # ====================================================================
        sec_theme = self._create_section(container, "Appearance")

        lbl_theme = ctk.CTkLabel(sec_theme, text="Color Mode", font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY, anchor="w")
        lbl_theme.pack(fill="x", pady=(0, 4))

        current_theme = self.profile.get("theme", "dark")
        self.seg_theme = ctk.CTkSegmentedButton(
            sec_theme,
            values=["Dark Mode", "Light Mode"],
            font=(theme.FONT_FAMILY, 12),
            height=34,
            corner_radius=8,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_HOVER,
            command=self._on_theme_changed,
        )
        self.seg_theme.pack(fill="x", pady=(0, 10))
        self.seg_theme.set("Dark Mode" if current_theme == "dark" else "Light Mode")

        # ====================================================================
        # 3. System Integration Section
        # ====================================================================
        sec_sys = self._create_section(container, "System Integration")

        startup_val = bool(self.profile.get("startup_enabled", 0))
        self.switch_startup = ctk.CTkSwitch(
            sec_sys,
            text="Launch Prior on Windows Startup",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            command=self._on_startup_toggled,
        )
        self.switch_startup.pack(fill="x", pady=(4, 6))
        if startup_val:
            self.switch_startup.select()

        lbl_startup_hint = ctk.CTkLabel(
            sec_sys,
            text="When enabled, Prior starts minimized in your Windows system tray.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        lbl_startup_hint.pack(fill="x")

        # ====================================================================
        # 4. Data Management Section
        # ====================================================================
        sec_data = self._create_section(container, "Data Management")

        data_row = ctk.CTkFrame(sec_data, fg_color="transparent")
        data_row.pack(fill="x", pady=6)

        btn_clear_comp = ctk.CTkButton(
            data_row,
            text="🧹 Clear Completed Tasks",
            font=(theme.FONT_FAMILY, 12),
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._clear_completed,
        )
        btn_clear_comp.pack(side="left", padx=(0, 10))

        btn_replay_intro = ctk.CTkButton(
            data_row,
            text="🔄 Replay Welcome Onboarding",
            font=(theme.FONT_FAMILY, 12),
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=self._replay_onboarding,
        )
        btn_replay_intro.pack(side="left")

    def _create_section(self, parent: Any, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        lbl_sec = ctk.CTkLabel(
            inner,
            text=title,
            font=(theme.FONT_DISPLAY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_sec.pack(fill="x", pady=(0, 10))

        return inner

    def _on_save_name(self) -> None:
        new_name = self.entry_name.get().strip() or "User"
        database.update_profile(name=new_name)
        self.profile["name"] = new_name
        self.on_profile_updated()

    def _on_theme_changed(self, value: str) -> None:
        new_theme = "dark" if value == "Dark Mode" else "light"
        ctk.set_appearance_mode(new_theme)
        database.update_profile(theme=new_theme)
        self.profile["theme"] = new_theme
        self.on_profile_updated()

    def _on_startup_toggled(self) -> None:
        is_on = bool(self.switch_startup.get())
        database.update_profile(startup_enabled=1 if is_on else 0)
        self.profile["startup_enabled"] = 1 if is_on else 0

    def _clear_completed(self) -> None:
        database.clear_completed_tasks()
        self.on_data_cleared()

    def _replay_onboarding(self) -> None:
        database.update_profile(onboarding_completed=0)
        self.profile["onboarding_completed"] = 0
        self.on_profile_updated()
