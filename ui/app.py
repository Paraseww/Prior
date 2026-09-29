import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import customtkinter as ctk
from PIL import Image

import database
from project import filter_tasks, get_task_notifications
from ui import theme
from ui.analytics_view import AnalyticsView
from ui.calendar_view import CalendarView
from ui.dot_pattern import DottedFrame
from ui.list_view import ListView
from ui.matrix_view import MatrixView
from ui.notification_modal import NotificationModal
from ui.pomodoro_modal import PomodoroModal
from ui.schedule_modal import ScheduleModal
from ui.settings_view import SettingsView
from ui.splash_view import SplashView
from ui.task_modal import TaskModal
from ui.tray import TrayService


class PriorApp(ctk.CTk):
    """
    Main desktop application window for Prior.
    """

    def __init__(self) -> None:
        super().__init__()

        # Fetch local user profile
        self.profile: Dict[str, Any] = database.get_profile()

        # Configure Window Properties
        self.title("Prior — Eisenhower Matrix Task Manager")
        self.geometry("1120x740")
        self.minsize(980, 640)

        # Set Window Icon
        self._set_app_icon()

        # Set appearance theme
        app_mode = self.profile.get("theme", "dark")
        ctk.set_appearance_mode(app_mode)
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=theme.BG_MAIN)

        # State Variables
        self.current_tab = "matrix"
        self.search_query = ""
        self.all_tasks: List[Dict[str, Any]] = []

        # System Tray instance (created when minimized to tray)
        self.tray: Optional[TrayService] = None

        # Intercept window close (X) to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Root container
        self.root_container = ctk.CTkFrame(self, fg_color="transparent")
        self.root_container.pack(fill="both", expand=True)

        self._check_onboarding_and_render()

        # Bring window to front
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _set_app_icon(self) -> None:
        """Configures the window titlebar and taskbar icon."""
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        ico_path = assets_dir / "icon.ico"
        png_path = assets_dir / "icon.png"

        try:
            if ico_path.exists() and sys.platform == "win32":
                self.iconbitmap(str(ico_path))
            elif png_path.exists():
                from PIL import ImageTk
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, photo)
        except Exception:
            pass

    def _check_onboarding_and_render(self) -> None:
        # Clear existing container children
        for child in self.root_container.winfo_children():
            child.destroy()

        # Reload profile
        self.profile = database.get_profile()
        onboarding_done = bool(self.profile.get("onboarding_completed", 0))

        if not onboarding_done:
            self.splash = SplashView(
                self.root_container,
                on_complete=self._on_onboarding_completed,
            )
            self.splash.pack(fill="both", expand=True)
        else:
            self._render_main_workspace()

    def _on_onboarding_completed(self) -> None:
        self.profile = database.get_profile()
        self._check_onboarding_and_render()

    def _render_main_workspace(self) -> None:
        # Top App Bar
        self._build_top_bar()

        # Main Body (Sidebar + Content area)
        self.body_frame = ctk.CTkFrame(self.root_container, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        # Sidebar
        self._build_sidebar()

        # Content Area
        self.content_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=8, pady=8)

        # Load tasks from database & show initial tab
        self._load_and_refresh()

    def _build_top_bar(self) -> None:
        top_bar = ctk.CTkFrame(
            self.root_container,
            fg_color=theme.BG_SIDEBAR,
            corner_radius=0,
            height=64,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        inner_top = ctk.CTkFrame(top_bar, fg_color="transparent")
        inner_top.pack(fill="both", expand=True, padx=20, pady=10)

        # Left: App Logo + Title + Tagline
        brand_frame = ctk.CTkFrame(inner_top, fg_color="transparent")
        brand_frame.pack(side="left")

        # Custom Logo Image (Figma asset)
        png_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if png_path.exists():
            pil_img = Image.open(png_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
            lbl_logo = ctk.CTkLabel(brand_frame, image=ctk_img, text="")
            lbl_logo.pack(side="left", padx=(0, 10))
        else:
            logo_badge = ctk.CTkFrame(
                brand_frame,
                width=36,
                height=36,
                corner_radius=18,
                fg_color=theme.ACCENT_PRIMARY,
            )
            logo_badge.pack(side="left", padx=(0, 10))
            logo_badge.pack_propagate(False)

            lbl_logo = ctk.CTkLabel(
                logo_badge,
                text="P",
                font=(theme.FONT_DISPLAY, 18, "bold"),
                text_color="#FFFFFF",
            )
            lbl_logo.place(relx=0.5, rely=0.5, anchor="center")

        brand_text_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_text_box.pack(side="left")

        lbl_brand = ctk.CTkLabel(
            brand_text_box,
            text="Prior.",
            font=(theme.FONT_DISPLAY, 18, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_brand.pack(anchor="w")

        lbl_tag = ctk.CTkLabel(
            brand_text_box,
            text="Prioritize what matters.",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        )
        lbl_tag.pack(anchor="w")

        # Center: Live Search Bar
        search_box = ctk.CTkFrame(inner_top, fg_color="transparent")
        search_box.pack(side="left", expand=True, padx=40)

        self.search_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="🔍 Search tasks by title or notes...",
            font=(theme.FONT_FAMILY, 13),
            width=360,
            height=38,
            corner_radius=10,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_COLOR,
            text_color=theme.TEXT_PRIMARY,
        )
        self.search_entry.pack()
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        # Right: Notifications + Theme Toggle + User Profile Badge
        actions_frame = ctk.CTkFrame(inner_top, fg_color="transparent")
        actions_frame.pack(side="right")

        # Notification Bell Button
        self.btn_notifications = ctk.CTkButton(
            actions_frame,
            text="🔔",
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, 13, "bold"),
            command=self._open_notifications,
        )
        self.btn_notifications.pack(side="left", padx=(0, 10))

        # Theme Toggle Button
        is_dark = self.profile.get("theme", "dark") == "dark"
        self.btn_theme = ctk.CTkButton(
            actions_frame,
            text="🌙" if is_dark else "☀️",
            width=36,
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, 14),
            command=self._toggle_quick_theme,
        )
        self.btn_theme.pack(side="left", padx=(0, 10))

        # Profile Badge
        user_name = self.profile.get("name", "User")
        self.btn_profile = ctk.CTkButton(
            actions_frame,
            text=f"👤 {user_name}",
            font=(theme.FONT_FAMILY, 13, "bold"),
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=lambda: self._switch_tab("settings"),
        )
        self.btn_profile.pack(side="left")

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(
            self.body_frame,
            fg_color=theme.BG_SIDEBAR,
            corner_radius=0,
            width=180,
            border_width=1,
            border_color=theme.BORDER_COLOR,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        inner_side = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        inner_side.pack(fill="both", expand=True, padx=10, pady=16)

        nav_items = [
            ("matrix", "▦  Matrix View"),
            ("list", "☰  List View"),
            ("calendar", "📅  Calendar"),
            ("analytics", "📊 Analytics"),
            ("settings", "⚙️  Settings"),
        ]

        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        for tab_id, label in nav_items:
            btn = ctk.CTkButton(
                inner_side,
                text=label,
                font=(theme.FONT_FAMILY, 13, "bold"),
                height=40,
                corner_radius=8,
                anchor="w",
                fg_color="transparent",
                hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_SECONDARY,
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[tab_id] = btn

        self._highlight_nav_button("matrix")

    def _highlight_nav_button(self, active_tab: str) -> None:
        for tab_id, btn in self.nav_buttons.items():
            if tab_id == active_tab:
                btn.configure(
                    fg_color=theme.BG_INPUT,
                    text_color=theme.TEXT_PRIMARY,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=theme.TEXT_SECONDARY,
                )

    def _switch_tab(self, tab_id: str) -> None:
        self.current_tab = tab_id
        self._highlight_nav_button(tab_id)

        # Clear content area
        for child in self.content_frame.winfo_children():
            child.destroy()

        # Get filtered tasks based on search
        filtered_tasks = filter_tasks(self.all_tasks, search_query=self.search_query)

        if tab_id == "matrix":
            self.current_view = MatrixView(
                self.content_frame,
                tasks=filtered_tasks,
                on_toggle=self.toggle_task,
                on_edit=self.open_task_modal,
                on_move=self.move_task_quadrant,
                on_delete=self.delete_task,
                on_quick_add=self.open_quick_add,
                on_pomodoro=self.open_pomodoro_modal,
                on_schedule=self.open_schedule_modal,
            )
            self.current_view.pack(fill="both", expand=True)

        elif tab_id == "list":
            self.current_view = ListView(
                self.content_frame,
                tasks=filtered_tasks,
                on_toggle=self.toggle_task,
                on_edit=self.open_task_modal,
                on_move=self.move_task_quadrant,
                on_delete=self.delete_task,
                on_clear_completed=self.clear_completed,
                on_pomodoro=self.open_pomodoro_modal,
                on_schedule=self.open_schedule_modal,
            )
            self.current_view.pack(fill="both", expand=True)

        elif tab_id == "calendar":
            self.current_view = CalendarView(
                self.content_frame,
                tasks=filtered_tasks,
                on_toggle=self.toggle_task,
                on_edit=self.open_task_modal,
                on_move=self.move_task_quadrant,
                on_delete=self.delete_task,
                on_quick_add=self.open_quick_add_with_date,
                on_pomodoro=self.open_pomodoro_modal,
                on_schedule=self.open_schedule_modal,
            )
            self.current_view.pack(fill="both", expand=True)

        elif tab_id == "analytics":
            self.current_view = AnalyticsView(
                self.content_frame,
                tasks=self.all_tasks,
            )
            self.current_view.pack(fill="both", expand=True)

        elif tab_id == "settings":
            self.current_view = SettingsView(
                self.content_frame,
                profile=self.profile,
                on_profile_updated=self._on_profile_updated,
                on_data_cleared=self._load_and_refresh,
            )
            self.current_view.pack(fill="both", expand=True)

    def _load_and_refresh(self) -> None:
        """Reloads all tasks from SQLite, updates notification badges, and refreshes current active tab."""
        self.all_tasks = database.get_all_tasks()
        self._update_notification_badge()
        self._switch_tab(self.current_tab)

    def _update_notification_badge(self) -> None:
        """Updates the notification bell button badge and highlight state."""
        if not hasattr(self, "btn_notifications"):
            return
        notifs = get_task_notifications(self.all_tasks)
        total = notifs["total_count"]
        if total > 0:
            self.btn_notifications.configure(
                text=f"🔔 {total}",
                fg_color=("#FEE2E2", "#2A0A0A") if notifs["overdue_count"] > 0 else theme.BG_INPUT,
                text_color=("#B91C1C", "#F87171") if notifs["overdue_count"] > 0 else theme.TEXT_PRIMARY,
            )
        else:
            self.btn_notifications.configure(
                text="🔔",
                fg_color=theme.BG_INPUT,
                text_color=theme.TEXT_PRIMARY,
            )

    def _open_notifications(self) -> None:
        """Opens the notification & reminders modal dialog."""
        NotificationModal(
            self,
            tasks=self.all_tasks,
            on_toggle=self.toggle_task,
            on_edit=self.open_task_modal,
            on_schedule=self.open_schedule_modal,
            on_refresh=self._load_and_refresh,
        )

    def _on_search_key(self, _: Any) -> None:
        self.search_query = self.search_entry.get().strip()
        # Refresh current view
        filtered = filter_tasks(self.all_tasks, search_query=self.search_query)
        if hasattr(self, "current_view") and hasattr(self.current_view, "refresh_tasks"):
            self.current_view.refresh_tasks(filtered)

    def _toggle_quick_theme(self) -> None:
        current_mode = ctk.get_appearance_mode().lower()
        new_mode = "light" if current_mode == "dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        self.configure(fg_color=theme.BG_MAIN)
        database.update_profile(theme=new_mode)
        self.profile["theme"] = new_mode
        self.btn_theme.configure(text="🌙" if new_mode == "dark" else "☀️")
        if hasattr(self, "content_frame") and hasattr(self.content_frame, "redraw_pattern"):
            self.content_frame.redraw_pattern()
        self._load_and_refresh()

    def _on_profile_updated(self) -> None:
        self.profile = database.get_profile()
        self.btn_profile.configure(text=f"👤 {self.profile.get('name', 'User')}")
        if not bool(self.profile.get("onboarding_completed", 0)):
            self._check_onboarding_and_render()
        else:
            self._load_and_refresh()

    # ========================================================================
    # Task Operations
    # ========================================================================

    def open_task_modal(
        self,
        task: Optional[Dict[str, Any]] = None,
        default_quadrant: str = "Q1_DO",
        default_due_date: Optional[str] = None,
    ) -> None:
        """Opens Add/Edit Task Modal."""
        def handle_save(data: Dict[str, Any]) -> None:
            if task and "id" in task:
                database.update_task(
                    task_id=task["id"],
                    title=data["title"],
                    description=data["description"],
                    quadrant=data["quadrant"],
                    due_date=data["due_date"],
                    reminder_time=data.get("reminder_time"),
                )
            else:
                database.add_task(
                    title=data["title"],
                    description=data["description"],
                    quadrant=data["quadrant"],
                    due_date=data["due_date"],
                    reminder_time=data.get("reminder_time"),
                )
            self._load_and_refresh()

        TaskModal(
            self,
            on_save=handle_save,
            task=task,
            default_quadrant=default_quadrant,
            default_due_date=default_due_date,
        )

    def open_quick_add(self, quadrant: str) -> None:
        """Opens Add Task Modal pre-selected with specified quadrant."""
        self.open_task_modal(default_quadrant=quadrant)

    def open_quick_add_with_date(self, quadrant: str = "Q2_SCHEDULE", due_date: Optional[str] = None) -> None:
        """Opens Add Task Modal pre-selected with specified quadrant and due date."""
        self.open_task_modal(default_quadrant=quadrant, default_due_date=due_date)

    def toggle_task(self, task_id: int) -> None:
        """Toggles task completion status."""
        database.toggle_task_completion(task_id)
        self._load_and_refresh()

    def move_task_quadrant(self, task_id: int, new_quadrant: str) -> None:
        """Moves task to another Eisenhower quadrant."""
        database.update_task(task_id=task_id, quadrant=new_quadrant)
        self._load_and_refresh()

    def delete_task(self, task_id: int) -> None:
        """Deletes a task."""
        database.delete_task(task_id)
        self._load_and_refresh()

    def open_pomodoro_modal(self, task: Dict[str, Any]) -> None:
        """Opens the Pomodoro Focus timer modal for the selected task."""
        PomodoroModal(
            self,
            task=task,
            on_complete_task=self.toggle_task,
            on_edit_task=self.open_task_modal,
        )

    def open_schedule_modal(self, task: Dict[str, Any]) -> None:
        """Opens the dedicated Schedule & Reminder modal for the selected task."""
        def handle_save_schedule(task_id: int, due_date: Optional[str], reminder_time: Optional[str]) -> None:
            database.update_task(task_id=task_id, due_date=due_date, reminder_time=reminder_time)
            self._load_and_refresh()

        ScheduleModal(
            self,
            task=task,
            on_save_schedule=handle_save_schedule,
            on_complete_task=self.toggle_task,
            on_edit_task=self.open_task_modal,
        )

    def clear_completed(self) -> None:
        """Clears all completed tasks."""
        database.clear_completed_tasks()
        self._load_and_refresh()

    # ========================================================================
    # Window & System Tray Management
    # ========================================================================

    def _init_tray(self) -> None:
        """Initializes system tray in the background."""
        try:
            self.tray = TrayService(
                on_show_app=self.show_window,
                on_quick_add=self.show_and_quick_add,
                on_exit_app=self.quit_completely,
            )
            self.tray.start()
        except Exception:
            pass

    def show_window(self) -> None:
        """Restores and focuses the application window from tray."""
        self.after(0, self._restore_window)

    def _restore_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def show_and_quick_add(self) -> None:
        """Restores window and immediately opens Add Task modal."""
        self.show_window()
        self.after(100, lambda: self.open_task_modal())

    def _on_window_close(self) -> None:
        """Minimizes the window to the system tray instead of terminating."""
        self.withdraw()
        if not self.tray:
            self._init_tray()
        # Notify user on first minimize
        if hasattr(self, "tray") and self.tray:
            self.tray.notify(
                title="Prior is running in background",
                message="Click the system tray icon to reopen anytime.",
            )

    def quit_completely(self) -> None:
        """Terminates the application and cleans up tray icon."""
        try:
            self.after(0, self.destroy)
        except Exception:
            sys.exit(0)


def launch_app() -> None:
    """Entrypoint function to launch the Prior desktop GUI application."""
    app = PriorApp()
    app.mainloop()


if __name__ == "__main__":
    launch_app()
