from datetime import date, datetime
import os
from pathlib import Path
import sys
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
import customtkinter as ctk
from PIL import Image

import database
from project import calculate_drop_dead_time, filter_tasks, get_task_notifications, is_task_delayed
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


from ui.windows_integration import (
    apply_prior_icon,
    init_windows_integration,
    set_process_app_id,
)

# Set Windows AppUserModelID before Tkinter initializes
set_process_app_id()

# Hook CustomTkinter window classes globally so all windows & modals always show Prior's logo
ctk.CTk._windows_set_titlebar_icon = lambda self: apply_prior_icon(self)
ctk.CTkToplevel._windows_set_titlebar_icon = lambda self: apply_prior_icon(self)


class PriorApp(ctk.CTk):
    """
    Main desktop application window for Prior.
    """

    def __init__(self) -> None:
        # Fetch local user profile and configure appearance before constructing CTk root
        self.profile: Dict[str, Any] = database.get_profile()
        app_mode = self.profile.get("theme", "light")
        ctk.set_appearance_mode(app_mode)
        ctk.set_default_color_theme("blue")

        super().__init__()

        # Configure Window Properties (screen-adaptive to prevent cutoffs on smaller/scaled displays)
        self.title("Prior - Eisenhower Matrix Task Manager")
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            target_w = min(1120, max(880, screen_w - 60))
            target_h = min(740, max(540, screen_h - 90))
            start_x = max(10, (screen_w - target_w) // 2)
            start_y = max(10, (screen_h - target_h) // 2)
            self.geometry(f"{target_w}x{target_h}+{start_x}+{start_y}")
            self.minsize(min(920, max(750, screen_w - 80)), min(560, max(460, screen_h - 100)))
        except Exception:
            self.geometry("1120x740")
            self.minsize(980, 640)

        # Set Window Icon and Taskbar Identity
        self._set_app_icon()
        init_windows_integration(self)

        self.configure(fg_color=theme.BG_MAIN)

        # State Variables
        self.current_tab = "matrix"
        self.search_query = ""
        self.all_tasks: List[Dict[str, Any]] = []
        self.views: Dict[str, Any] = {}
        self.dismissed_notification_ids: Set[int] = set()
        self.notified_reminder_keys: Set[str] = set()
        self.active_notification_modal: Optional[Any] = None
        self.active_pomodoro_modal: Optional[Any] = None
        self.notification_queue: List[Tuple[str, str]] = []
        self._is_processing_notification_queue: bool = False
        self.task_last_notified: Dict[int, datetime] = {}
        self.task_renudge_counts: Dict[int, int] = {}

        # System Tray instance (active throughout app lifecycle)
        self.tray: Optional[TrayService] = None
        self._init_tray()

        # Intercept window close (X) to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Root container
        self.root_container = ctk.CTkFrame(self, fg_color="transparent")
        self.root_container.pack(fill="both", expand=True)

        # Restore saved zoom scaling if configured
        saved_zoom = float(self.profile.get("zoom_scale", 1.0) or 1.0)
        if abs(saved_zoom - 1.0) > 0.01:
            ctk.set_widget_scaling(saved_zoom)

        # Initialize global keyboard shortcuts & zoom adjustment
        self._init_zoom_shortcuts()

        self._check_onboarding_and_render()

        # Pre-seed delayed tasks on startup so zero old/delayed alerts pop up
        try:
            boot_now = datetime.now()
            boot_today = boot_now.strftime("%Y-%m-%d")
            all_boot_tasks = database.get_all_tasks()
            for t in all_boot_tasks:
                if is_task_delayed(t, current_dt=boot_now):
                    t_id = t.get("id")
                    rem_str = str(t.get("reminder_time") or "").strip()
                    self.notified_reminder_keys.add(f"q1_runway_warn_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"q1_runway_start_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"q1_runway_renudge_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"q1_deadline_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"headsup_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"time_{t_id}_{boot_today}_{rem_str}")
                    self.notified_reminder_keys.add(f"overdue_{t_id}_{boot_today}")
        except Exception:
            pass

        # Start periodic reminder checker for scheduled tasks
        self.after(3000, self._check_reminders)

        # Start IPC server for single-instance activation and notification click handling
        self._start_ipc_server()

        # If launched with --open-notifications flag or prior:// protocol, open notifications
        if "--open-notifications" in sys.argv or any("prior://" in arg.lower() for arg in sys.argv):
            self.after(600, self._open_notifications)

        # Check if started with --minimized flag (e.g. Windows startup)
        if "--minimized" in sys.argv:
            self.withdraw()
        else:
            # Bring window to front
            self.lift()
            self.attributes("-topmost", True)
            self.after(100, lambda: self.attributes("-topmost", False))
            self.focus_force()

    def _set_app_icon(self) -> None:
        """Configures the window titlebar, taskbar, and Alt-Tab switcher icon."""
        apply_prior_icon(self)

    def _check_onboarding_and_render(self) -> None:
        # Clear cached view references before resetting container
        self.views.clear()
        self.current_view = None
        self.current_tab = "matrix"

        # Clear existing container children
        for child in self.root_container.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

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
        # Ensure fresh state for all cached views
        self.views.clear()
        self.current_view = None
        self.current_tab = "matrix"
        self.search_query = ""

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
        self.all_tasks = database.get_all_tasks()
        self._switch_tab("matrix")
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
            width=36,
            height=36,
            corner_radius=8,
            fg_color=theme.BG_INPUT,
            hover_color=theme.BG_CARD_HOVER,
            text_color=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, 13, "bold"),
            command=self._open_notifications,
        )
        self.btn_notifications.pack(side="left", padx=(0, 8))

        # Theme Toggle Button
        is_dark = self.profile.get("theme", "light") == "dark"
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
        self.btn_theme.pack(side="left", padx=(0, 8))

        # Profile Badge
        user_name = self.profile.get("name", "User")
        self.btn_profile = ctk.CTkButton(
            actions_frame,
            text=f"  👤 {user_name}  ",
            font=(theme.FONT_FAMILY, 13, "bold"),
            width=0,
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

        # Always retrieve latest tasks from SQLite for instant freshness
        self.all_tasks = database.get_all_tasks()

        # Hide all other cached views safely
        for vid, vwidget in list(self.views.items()):
            if vid != tab_id:
                try:
                    if vwidget.winfo_exists():
                        vwidget.pack_forget()
                    else:
                        del self.views[vid]
                except Exception:
                    self.views.pop(vid, None)

        filtered_tasks = filter_tasks(self.all_tasks, search_query=self.search_query)

        # Ensure target view exists and is valid
        if tab_id in self.views:
            try:
                if not self.views[tab_id].winfo_exists():
                    del self.views[tab_id]
            except Exception:
                del self.views[tab_id]

        # Lazy initialize and cache view if not already created
        if tab_id not in self.views:
            if tab_id == "matrix":
                view = MatrixView(
                    self.content_frame,
                    tasks=filtered_tasks,
                    on_toggle=self.toggle_task,
                    on_edit=self.open_task_modal,
                    on_move=self.move_task_quadrant,
                    on_reorder=self.move_or_reorder_task,
                    on_delete=self.delete_task,
                    on_archive=self.archive_task,
                    on_quick_add=self.open_quick_add,
                    on_pomodoro=self.open_pomodoro_modal,
                    on_schedule=self.open_schedule_modal,
                )
            elif tab_id == "list":
                view = ListView(
                    self.content_frame,
                    tasks=filtered_tasks,
                    on_toggle=self.toggle_task,
                    on_edit=self.open_task_modal,
                    on_move=self.move_task_quadrant,
                    on_delete=self.delete_task,
                    on_archive=self.archive_task,
                    on_clear_completed=self.clear_completed,
                    on_pomodoro=self.open_pomodoro_modal,
                    on_schedule=self.open_schedule_modal,
                )
            elif tab_id == "calendar":
                view = CalendarView(
                    self.content_frame,
                    tasks=filtered_tasks,
                    on_toggle=self.toggle_task,
                    on_edit=self.open_task_modal,
                    on_move=self.move_task_quadrant,
                    on_delete=self.delete_task,
                    on_archive=self.archive_task,
                    on_quick_add=self.open_quick_add_with_date,
                    on_pomodoro=self.open_pomodoro_modal,
                    on_schedule=self.open_schedule_modal,
                )
            elif tab_id == "analytics":
                view = AnalyticsView(
                    self.content_frame,
                    tasks=self.all_tasks,
                )
            elif tab_id == "settings":
                view = SettingsView(
                    self.content_frame,
                    profile=self.profile,
                    on_profile_updated=self._on_profile_updated,
                    on_data_cleared=self._load_and_refresh,
                )
            else:
                return

            self.views[tab_id] = view

        # Show target view smoothly
        target_view = self.views.get(tab_id)
        if target_view is not None:
            try:
                target_view.pack(fill="both", expand=True)
                self.current_view = target_view
            except Exception:
                pass

            # Update view data without rebuilding widgets
            if hasattr(target_view, "refresh_tasks"):
                if tab_id == "analytics":
                    target_view.refresh_tasks(self.all_tasks)
                else:
                    target_view.refresh_tasks(filtered_tasks)

    def _load_and_refresh(self) -> None:
        """Reloads all tasks from SQLite, updates notification badges, and refreshes views."""
        self.all_tasks = database.get_all_tasks()
        self._update_notification_badge()

        # Refresh active notification modal if currently open
        if hasattr(self, "active_notification_modal") and self.active_notification_modal:
            try:
                if self.active_notification_modal.winfo_exists():
                    self.active_notification_modal.tasks = list(self.all_tasks)
                    self.active_notification_modal._build_ui()
            except Exception:
                self.active_notification_modal = None

        # Update current active view without rebuilding
        filtered_tasks = filter_tasks(self.all_tasks, search_query=self.search_query)
        if self.current_tab in self.views:
            active_view = self.views[self.current_tab]
            try:
                if not active_view.winfo_exists():
                    del self.views[self.current_tab]
                    self._switch_tab(self.current_tab)
                    return
            except Exception:
                del self.views[self.current_tab]
                self._switch_tab(self.current_tab)
                return

            if hasattr(active_view, "refresh_tasks"):
                if self.current_tab == "analytics":
                    active_view.refresh_tasks(self.all_tasks)
                else:
                    active_view.refresh_tasks(filtered_tasks)
        else:
            self._switch_tab(self.current_tab)

        # Trigger desktop reminder & deadline check promptly after tasks update
        self.after(300, self._check_reminders)

    def _update_notification_badge(self) -> None:
        """Updates the notification bell button badge and highlight state."""
        if not hasattr(self, "btn_notifications"):
            return
        active_tasks = [t for t in self.all_tasks if t.get("id") not in getattr(self, "dismissed_notification_ids", set())]
        notifs = get_task_notifications(active_tasks)
        total = notifs["total_count"]
        if total > 0:
            self.btn_notifications.configure(
                text=f"  🔔 {total}  ",
                width=0,
                fg_color=("#FEE2E2", "#2A0A0A") if notifs["overdue_count"] > 0 else theme.BG_INPUT,
                text_color=("#B91C1C", "#F87171") if notifs["overdue_count"] > 0 else theme.TEXT_PRIMARY,
            )
        else:
            self.btn_notifications.configure(
                text="🔔",
                width=36,
                fg_color=theme.BG_INPUT,
                text_color=theme.TEXT_PRIMARY,
            )

    def _open_notifications(self) -> None:
        """Opens the notification & reminders modal dialog."""
        if hasattr(self, "active_notification_modal") and self.active_notification_modal:
            try:
                if self.active_notification_modal.winfo_exists():
                    self.active_notification_modal.deiconify()
                    self.active_notification_modal.lift()
                    self.active_notification_modal.focus_force()
                    return
            except Exception:
                pass

        self.active_notification_modal = NotificationModal(
            self,
            tasks=self.all_tasks,
            on_toggle=self.toggle_task,
            on_edit=self.open_task_modal,
            on_schedule=self.open_schedule_modal,
            on_refresh=self._load_and_refresh,
            on_focus=self.open_pomodoro_modal,
        )

    def flash_window(self) -> None:
        """Gently pulses the Windows taskbar icon to draw the user's attention from background browsing."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.UINT),
                    ("hwnd", wintypes.HWND),
                    ("dwFlags", wintypes.DWORD),
                    ("uCount", wintypes.UINT),
                    ("dwTimeout", wintypes.DWORD),
                ]

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            fwi = FLASHWINFO(
                cbSize=ctypes.sizeof(FLASHWINFO),
                hwnd=hwnd,
                dwFlags=0x00000002 | 0x0000000C,  # FLASHW_TRAY | FLASHW_TIMERNOFG
                uCount=4,
                dwTimeout=0,
            )
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(fwi))
        except Exception:
            pass

    def notify_desktop(self, title: str, message: str) -> None:
        """Dispatches a native Windows desktop notification and pulses the taskbar icon."""
        self._queue_desktop_notification(title, message)

    def _queue_desktop_notification(self, title: str, message: str) -> None:
        """Enqueues a desktop notification to be dispatched with smooth pacing and taskbar pulse."""
        self.notification_queue.append((title, message))
        self.flash_window()
        if not self._is_processing_notification_queue:
            self._process_notification_queue()

    def _process_notification_queue(self) -> None:
        """Dispatches queued desktop notifications spaced 2.5 seconds apart so Windows renders each cleanly."""
        if not self.notification_queue:
            self._is_processing_notification_queue = False
            return

        if not (hasattr(self, "tray") and self.tray):
            # Tray instance not created yet, wait 300ms and retry
            self._is_processing_notification_queue = True
            self.after(300, self._process_notification_queue)
            return

        self._is_processing_notification_queue = True
        title, message = self.notification_queue.pop(0)
        try:
            self.tray.notify(title=title, message=message)
        except Exception:
            pass

        if self.notification_queue:
            self.after(2500, self._process_notification_queue)
        else:
            self._is_processing_notification_queue = False

    def _check_reminders(self) -> None:
        """Periodic background check for tasks reaching their scheduled reminder time and deadlines."""
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # 1. Timed Tasks on Today's Date (Scheduled Reminders)
            for task in self.all_tasks:
                if bool(task.get("is_completed", 0)):
                    continue
                due_date = task.get("due_date")
                reminder_time = task.get("reminder_time")
                if not due_date or not reminder_time:
                    continue

                if str(due_date).strip() == today_str:
                    rem_str = str(reminder_time).strip()
                    try:
                        rem_dt = datetime.strptime(rem_str, "%I:%M %p").time()
                    except ValueError:
                        try:
                            rem_dt = datetime.strptime(rem_str, "%H:%M").time()
                        except ValueError:
                            continue

                    task_id = task.get("id")
                    if task_id is None:
                        continue

                    quadrant = task.get("quadrant", "Q1_DO")
                    est_duration = int(task.get("estimated_duration") or 0)
                    title = task.get("title", "Task")

                    # STRICTLY DO NOT ALERT FOR DELAYED TASKS
                    if is_task_delayed(task, current_dt=now):
                        self.notified_reminder_keys.add(f"q1_runway_warn_{task_id}_{today_str}_{rem_str}")
                        self.notified_reminder_keys.add(f"q1_runway_start_{task_id}_{today_str}_{rem_str}")
                        self.notified_reminder_keys.add(f"q1_runway_renudge_{task_id}_{today_str}_{rem_str}")
                        self.notified_reminder_keys.add(f"q1_deadline_{task_id}_{today_str}_{rem_str}")
                        self.notified_reminder_keys.add(f"headsup_{task_id}_{today_str}_{rem_str}")
                        self.notified_reminder_keys.add(f"time_{task_id}_{today_str}_{rem_str}")
                        continue

                    # Special Runway Logic for Q1 (Do First / Critical Deadlines) with estimated duration
                    if quadrant == "Q1_DO" and est_duration > 0:
                        drop_info = calculate_drop_dead_time(rem_str, est_duration, today_str, reference_dt=now)
                        if drop_info:
                            mins_to_start = drop_info["mins_to_start"]
                            mins_to_deadline = drop_info["mins_to_deadline"]
                            drop_dead_str = drop_info["drop_dead_time_str"]
                            dur_text = drop_info["duration_text"]
                            sprints = drop_info["pomodoro_sprints"]

                            if est_duration < 60:
                                dur_phrase = f"{est_duration} minutes"
                            elif est_duration == 60:
                                dur_phrase = "1 hour"
                            elif est_duration % 60 == 0:
                                dur_phrase = f"{est_duration // 60} hours"
                            else:
                                dur_phrase = f"{est_duration // 60} hours {est_duration % 60} minutes"

                            # Milestone 1: 15-Minute Runway Heads-Up before Drop-Dead Start Time
                            if 0 < mins_to_start <= 15:
                                warn_key = f"q1_runway_warn_{task_id}_{today_str}_{rem_str}"
                                if warn_key not in self.notified_reminder_keys:
                                    self.notified_reminder_keys.add(warn_key)
                                    mins_int = max(1, int(round(mins_to_start)))
                                    time_label = "15m" if mins_int >= 13 else f"{mins_int}m"
                                    self._queue_desktop_notification(
                                        title=f"☕ Heads up, friend! {time_label} until {title}",
                                        message=f"Due at {rem_str} and needs about {dur_phrase}. Grab some water, close your extra tabs, and get set to start at {drop_dead_str}! 🚀",
                                    )

                            # Milestone 2: Drop-Dead Start Time Reached (only when occurring right now)
                            if -2.0 <= mins_to_start <= 0 and mins_to_deadline > 0:
                                start_key = f"q1_runway_start_{task_id}_{today_str}_{rem_str}"
                                if start_key not in self.notified_reminder_keys:
                                    self.notified_reminder_keys.add(start_key)
                                    self.task_last_notified[task_id] = now
                                    self.dismissed_notification_ids.discard(task_id)
                                    self._update_notification_badge()
                                    self._queue_desktop_notification(
                                        title=f"🎯 Game time! Let's start {title}",
                                        message=f"It's {drop_dead_str}! Starting now gets it finished before your {rem_str} deadline. You've got this, ready for a focus sprint? 🍅",
                                    )

                            # Milestone 2.5: Anti-Procrastination Friendly Re-Nudge (around 45m of inaction, well before deadline)
                            if -47.0 <= mins_to_start <= -45.0 and mins_to_deadline > 15:
                                renudge_key = f"q1_runway_renudge_{task_id}_{today_str}_{rem_str}"
                                if renudge_key not in self.notified_reminder_keys:
                                    self.notified_reminder_keys.add(renudge_key)
                                    self.task_last_notified[task_id] = now
                                    self.dismissed_notification_ids.discard(task_id)
                                    self._update_notification_badge()
                                    self._queue_desktop_notification(
                                        title=f"👀 Checking in on you: {title}",
                                        message=f"Don't let this turn into late night stress! We're dipping into your buffer before {rem_str}. Let's jump into a 25 min sprint together! 💪",
                                    )

                            # Milestone 3: Critical Deadline Reached (only when arriving right now)
                            if -1.5 <= mins_to_deadline <= 0:
                                deadline_key = f"q1_deadline_{task_id}_{today_str}_{rem_str}"
                                if deadline_key not in self.notified_reminder_keys:
                                    self.notified_reminder_keys.add(deadline_key)
                                    self.task_last_notified[task_id] = now
                                    self.dismissed_notification_ids.discard(task_id)
                                    self._update_notification_badge()
                                    self._queue_desktop_notification(
                                        title=f"🏁 Finish line: {title}!",
                                        message=f"It's {rem_str}! That's the deadline, wrap up your final touches and let's cross this off your list! 🎉",
                                    )
                    else:
                        # Standard Scheduled Task Logic
                        target_dt = datetime.combine(now.date(), rem_dt)
                        mins_diff = (target_dt - now).total_seconds() / 60.0

                        # Milestone 1: 30-Minute Heads-Up (between 1 and 30 minutes before)
                        if 0 < mins_diff <= 30:
                            headsup_key = f"headsup_{task_id}_{today_str}_{rem_str}"
                            if headsup_key not in self.notified_reminder_keys:
                                self.notified_reminder_keys.add(headsup_key)
                                title = task.get("title", "Scheduled Task")
                                mins_int = max(1, int(round(mins_diff)))
                                self._queue_desktop_notification(
                                    title=f"⏳ In {mins_int} Mins: {title}",
                                    message=f"Scheduled for {rem_str}. Wrap up your current work to focus.",
                                )

                        # Milestone 2: Exact Scheduled Time (only when arriving right now)
                        if -2.0 <= mins_diff <= 0:
                            reminder_key = f"time_{task_id}_{today_str}_{rem_str}"
                            if reminder_key not in self.notified_reminder_keys:
                                self.notified_reminder_keys.add(reminder_key)
                                self.task_last_notified[task_id] = now
                                self.dismissed_notification_ids.discard(task_id)
                                self._update_notification_badge()
                                title = task.get("title", "Task Reminder")
                                self._queue_desktop_notification(
                                    title=f"⏰ Scheduled Now: {title}",
                                    message=f"It's {rem_str}! Ready for a 25 min focus sprint? Click to begin.",
                                )

            # 2. Categorized deadline notifications for active tasks
            active_tasks = [t for t in self.all_tasks if t.get("id") not in getattr(self, "dismissed_notification_ids", set())]
            notifs = get_task_notifications(active_tasks, current_date_str=today_str)

            # A. Overdue Tasks (Carried over from past days) - Strictly DO NOT send desktop alerts for delayed tasks!
            overdue_pending = [
                t for t in notifs.get("overdue", [])
                if f"overdue_{t.get('id')}_{today_str}" not in self.notified_reminder_keys
            ]
            for t in overdue_pending:
                self.notified_reminder_keys.add(f"overdue_{t.get('id')}_{today_str}")

            # B. Untimed Tasks Due Today (Natural Checkpoints: Midday 12:30-14:00 & Evening 18:00-20:00)
            untimed_today = [
                t for t in notifs.get("today", [])
                if not (t.get("reminder_time") and str(t.get("reminder_time")).strip())
            ]
            if untimed_today:
                current_hour = now.hour
                current_min = now.minute

                # Midday Check-in (between 12:30 PM and 2:00 PM)
                if (current_hour == 12 and current_min >= 30) or current_hour == 13:
                    midday_key = f"midday_digest_{today_str}"
                    if midday_key not in self.notified_reminder_keys:
                        self.notified_reminder_keys.add(midday_key)
                        first_title = untimed_today[0].get("title", "Today's Task")
                        extra = f" and {len(untimed_today) - 1} more" if len(untimed_today) > 1 else ""
                        self._queue_desktop_notification(
                            title="📋 Midday Check-In",
                            message=f"{first_title}{extra} due today. Keep your momentum going!",
                        )

                # Evening Review (between 6:00 PM and 8:00 PM)
                elif 18 <= current_hour < 20:
                    evening_key = f"evening_digest_{today_str}"
                    if evening_key not in self.notified_reminder_keys:
                        self.notified_reminder_keys.add(evening_key)
                        first_title = untimed_today[0].get("title", "Today's Task")
                        extra = f" and {len(untimed_today) - 1} more" if len(untimed_today) > 1 else ""
                        self._queue_desktop_notification(
                            title="🌅 Evening Review",
                            message=f"{first_title}{extra} pending today. Wrap up before the day ends.",
                        )

            # C. Tasks Due Tomorrow (Evening Plan-Ahead Digest: 7:00 PM - 9:00 PM)
            tomorrow_tasks = notifs.get("tomorrow", [])
            if tomorrow_tasks and 19 <= now.hour < 21:
                tomorrow_key = f"tomorrow_digest_{today_str}"
                if tomorrow_key not in self.notified_reminder_keys:
                    self.notified_reminder_keys.add(tomorrow_key)
                    first_title = tomorrow_tasks[0].get("title", "Tomorrow's Task")
                    extra = f" and {len(tomorrow_tasks) - 1} more" if len(tomorrow_tasks) > 1 else ""
                    self._queue_desktop_notification(
                        title="⏳ Ahead for Tomorrow",
                        message=f"{first_title}{extra} due tomorrow. Plan ahead!",
                    )

            # D. Milestone 3: Gentle Anti-Procrastination Re-Nudge (Capped at 1x, 45m after reminder)
            for task in self.all_tasks:
                if bool(task.get("is_completed", 0)):
                    continue
                t_id = task.get("id")
                if not t_id or t_id in getattr(self, "dismissed_notification_ids", set()):
                    continue

                # NEVER alert or re-nudge for delayed tasks!
                if is_task_delayed(task, current_dt=now):
                    continue

                is_q1 = task.get("quadrant") == "Q1_DO"
                is_due_today = str(task.get("due_date", "")).strip() == today_str
                if not (is_q1 or is_due_today):
                    continue

                last_notif = self.task_last_notified.get(t_id)
                nudge_count = self.task_renudge_counts.get(t_id, 0)
                # Exactly 1 gentle follow-up so it never annoys the user
                if last_notif and nudge_count < 1:
                    elapsed_mins = (now - last_notif).total_seconds() / 60.0
                    # Re-nudge after 45 minutes of inaction
                    if elapsed_mins >= 45:
                        self.task_last_notified[t_id] = now
                        self.task_renudge_counts[t_id] = 1
                        title = task.get("title", "High-Priority Task")
                        est_duration = int(task.get("estimated_duration") or 0)
                        if is_q1 and est_duration > 0:
                            self._queue_desktop_notification(
                                title=f"🚨 Running Out of Runway: {title}",
                                message="You are cutting into your buffer before the deadline! Start a focus sprint now.",
                            )
                        else:
                            self._queue_desktop_notification(
                                title=f"🔥 Still Waiting: {title}",
                                message="Break the hesitation! Start a 25-min Pomodoro focus sprint now.",
                            )
        except Exception:
            pass
        finally:
            try:
                self.after(15000, self._check_reminders)
            except Exception:
                pass

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
        self.profile["theme"] = new_mode
        self.btn_theme.configure(text="🌙" if new_mode == "dark" else "☀️")
        if hasattr(self, "content_frame") and hasattr(self.content_frame, "redraw_pattern"):
            self.content_frame.redraw_pattern()

        # Persist theme preference asynchronously in background to eliminate UI blocking
        import threading
        threading.Thread(target=database.update_profile, kwargs={"theme": new_mode}, daemon=True).start()

    def _on_profile_updated(self) -> None:
        self.profile = database.get_profile()
        if hasattr(self, "btn_profile") and hasattr(self.btn_profile, "winfo_exists"):
            try:
                if self.btn_profile.winfo_exists():
                    self.btn_profile.configure(text=f"  👤 {self.profile.get('name', 'User')}  ")
            except Exception:
                pass
        if hasattr(self, "btn_theme") and hasattr(self.btn_theme, "winfo_exists"):
            try:
                current_mode = ctk.get_appearance_mode().lower()
                self.btn_theme.configure(text="🌙" if current_mode == "dark" else "☀️")
            except Exception:
                pass
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
                task_id = task["id"]
                database.update_task(
                    task_id=task_id,
                    title=data["title"],
                    description=data["description"],
                    quadrant=data["quadrant"],
                    due_date=data["due_date"],
                    reminder_time=data.get("reminder_time"),
                    estimated_duration=data.get("estimated_duration", 0),
                )
                self.dismissed_notification_ids.discard(task_id)
                self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
            else:
                new_id = database.add_task(
                    title=data["title"],
                    description=data["description"],
                    quadrant=data["quadrant"],
                    due_date=data["due_date"],
                    reminder_time=data.get("reminder_time"),
                    estimated_duration=data.get("estimated_duration", 0),
                )
                if new_id:
                    self.dismissed_notification_ids.discard(new_id)
                    self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{new_id}_" not in k}
            self._load_and_refresh()
            self.after(50, self._check_reminders)

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
        target_task = next((t for t in self.all_tasks if t.get("id") == task_id), None)
        if target_task and is_task_delayed(target_task):
            # Delayed / passed tasks cannot be completed without rescheduling
            return
        database.toggle_task_completion(task_id)
        self.dismissed_notification_ids.discard(task_id)
        self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
        self.task_last_notified.pop(task_id, None)
        self.task_renudge_counts.pop(task_id, None)
        self._load_and_refresh()

    def mark_task_completed(self, task_id: int) -> None:
        """Explicitly marks a task as completed (idempotent, does not toggle to incomplete)."""
        target_task = next((t for t in self.all_tasks if t.get("id") == task_id), None)
        if target_task and is_task_delayed(target_task):
            # Delayed / passed tasks cannot be completed without rescheduling
            return
        database.update_task(task_id, is_completed=1)
        self.dismissed_notification_ids.discard(task_id)
        self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
        self.task_last_notified.pop(task_id, None)
        self.task_renudge_counts.pop(task_id, None)
        self._load_and_refresh()

    def move_or_reorder_task(
        self,
        task_id: int,
        target_quadrant: str,
        target_index: int = 0,
    ) -> None:
        """
        Handles moving a task between quadrants or reordering within the same quadrant.
        """
        all_tasks = database.get_all_tasks()
        dragged_task = next((t for t in all_tasks if t.get("id") == task_id), None)
        if not dragged_task:
            return

        source_quadrant = dragged_task.get("quadrant", "Q1_DO")

        if source_quadrant == target_quadrant:
            # Reordering within the SAME quadrant
            quad_tasks = [t for t in all_tasks if t.get("quadrant") == source_quadrant]
            task_ids = [t["id"] for t in quad_tasks]
            if task_id in task_ids:
                old_idx = task_ids.index(task_id)
                task_ids.remove(task_id)
                insert_pos = max(0, min(len(task_ids), target_index))
                task_ids.insert(insert_pos, task_id)
                database.reorder_tasks(task_ids)
                self._load_and_refresh()
        else:
            # Moving to a DIFFERENT quadrant with target position
            target_quad_tasks = [t for t in all_tasks if t.get("quadrant") == target_quadrant]
            target_task_ids = [t["id"] for t in target_quad_tasks]
            insert_pos = max(0, min(len(target_task_ids), target_index))
            target_task_ids.insert(insert_pos, task_id)

            database.update_task(task_id=task_id, quadrant=target_quadrant)
            database.reorder_tasks(target_task_ids)
            self._load_and_refresh()

    def move_task_quadrant(self, task_id: int, new_quadrant: str) -> None:
        """Moves task to another Eisenhower quadrant."""
        self.move_or_reorder_task(task_id, new_quadrant, target_index=0)

    def delete_task(self, task_id: int) -> None:
        """Deletes a task."""
        database.delete_task(task_id)
        self.dismissed_notification_ids.discard(task_id)
        self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
        self.task_last_notified.pop(task_id, None)
        self.task_renudge_counts.pop(task_id, None)
        self._load_and_refresh()

    def archive_task(self, task_id: int) -> None:
        """Archives a completed task without deleting it or its analytics data."""
        database.archive_task(task_id)
        self.dismissed_notification_ids.discard(task_id)
        self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
        self.task_last_notified.pop(task_id, None)
        self.task_renudge_counts.pop(task_id, None)
        self._load_and_refresh()

    def open_pomodoro_modal(self, task: Dict[str, Any]) -> None:
        """Opens the Pomodoro Focus timer modal for the selected task."""
        if hasattr(self, "active_pomodoro_modal") and self.active_pomodoro_modal is not None:
            try:
                if self.active_pomodoro_modal.winfo_exists():
                    self.active_pomodoro_modal.lift()
                    self.active_pomodoro_modal.focus_force()
                    return
            except Exception:
                self.active_pomodoro_modal = None

        self.active_pomodoro_modal = PomodoroModal(
            self,
            task=task,
            on_complete_task=self.mark_task_completed,
            on_edit_task=self.open_task_modal,
            on_delete_task=self.delete_task,
        )

    def open_schedule_modal(self, task: Dict[str, Any]) -> None:
        """Opens the dedicated Schedule & Reminder modal for the selected task."""
        def handle_save_schedule(
            task_id: int,
            due_date: Optional[str],
            reminder_time: Optional[str],
            estimated_duration: int = 0,
        ) -> None:
            database.update_task(
                task_id=task_id,
                due_date=due_date,
                reminder_time=reminder_time,
                estimated_duration=estimated_duration,
            )
            self.dismissed_notification_ids.discard(task_id)
            self.notified_reminder_keys = {k for k in self.notified_reminder_keys if f"_{task_id}_" not in k}
            self._load_and_refresh()
            self.after(50, self._check_reminders)

        ScheduleModal(
            self,
            task=task,
            on_save_schedule=handle_save_schedule,
            on_complete_task=self.mark_task_completed,
            on_edit_task=self.open_task_modal,
            on_delete_task=self.delete_task,
        )

    def clear_completed(self) -> None:
        """Clears all completed tasks."""
        database.clear_completed_tasks()
        self._load_and_refresh()

    # ========================================================================
    # Interface Zoom & Display Scaling (Ctrl +, Ctrl -, Ctrl 0, Ctrl + MouseWheel)
    # ========================================================================

    def _init_zoom_shortcuts(self) -> None:
        """Binds Ctrl+, Ctrl-, Ctrl 0, and Ctrl+MouseWheel for app zoom adjustment."""
        # Zoom In shortcuts (Ctrl +, Ctrl =, Ctrl Numpad +)
        for seq in (
            "<Control-plus>",
            "<Control-equal>",
            "<Control-Shift-plus>",
            "<Control-Shift-equal>",
            "<Control-KP_Add>",
        ):
            self.bind_all(seq, self.zoom_in)

        # Zoom Out shortcuts (Ctrl -, Ctrl _, Ctrl Numpad -)
        for seq in (
            "<Control-minus>",
            "<Control-underscore>",
            "<Control-Shift-minus>",
            "<Control-Shift-underscore>",
            "<Control-KP_Subtract>",
        ):
            self.bind_all(seq, self.zoom_out)

        # Zoom Reset shortcuts (Ctrl 0, Ctrl Numpad 0)
        for seq in ("<Control-Key-0>", "<Control-0>", "<Control-KP_0>"):
            self.bind_all(seq, self.zoom_reset)

        # Ctrl + Mouse Wheel zoom
        self.bind_all("<Control-MouseWheel>", self._on_ctrl_mousewheel)

    def zoom_in(self, event: Any = None) -> str:
        """Increases UI widget scaling by 10% (up to 150%)."""
        curr = ctk.ScalingTracker.get_widget_scaling(self)
        new_scale = round(curr + 0.1, 2)
        if new_scale <= 1.501:
            self.set_zoom(new_scale)
        else:
            self.show_zoom_toast(int(round(curr * 100)))
        return "break"

    def zoom_out(self, event: Any = None) -> str:
        """Decreases UI widget scaling by 10% (down to 70%)."""
        curr = ctk.ScalingTracker.get_widget_scaling(self)
        new_scale = round(curr - 0.1, 2)
        if new_scale >= 0.699:
            self.set_zoom(new_scale)
        else:
            self.show_zoom_toast(int(round(curr * 100)))
        return "break"

    def zoom_reset(self, event: Any = None) -> str:
        """Resets UI widget scaling back to default 100%."""
        self.set_zoom(1.0)
        return "break"

    def set_zoom(self, new_scale: float) -> None:
        """Applies a new widget scaling factor and updates feedback indicators."""
        new_scale = round(max(0.7, min(1.5, new_scale)), 2)
        ctk.set_widget_scaling(new_scale)
        pct = int(round(new_scale * 100))
        self.show_zoom_toast(pct)

        # Persist zoom preference asynchronously
        import threading

        def _save_zoom():
            try:
                database.update_profile(zoom_scale=new_scale)
            except Exception:
                pass

        threading.Thread(target=_save_zoom, daemon=True).start()

        # If settings view is open, update its zoom label
        settings_view = self.views.get("settings")
        if settings_view and hasattr(settings_view, "update_zoom_display"):
            settings_view.update_zoom_display(pct)

    def _on_ctrl_mousewheel(self, event: Any) -> str:
        """Handles Ctrl + Mouse Wheel for smooth zooming with rate limiting."""
        import time
        now = time.time()
        if hasattr(self, "_last_wheel_zoom_time") and now - self._last_wheel_zoom_time < 0.08:
            return "break"
        self._last_wheel_zoom_time = now

        if event.delta > 0:
            self.zoom_in()
        elif event.delta < 0:
            self.zoom_out()
        return "break"

    def show_zoom_toast(self, percent: int) -> None:
        """Displays a sleek temporary HUD badge showing the current zoom percentage."""
        if hasattr(self, "_zoom_hud_timer") and self._zoom_hud_timer:
            try:
                self.after_cancel(self._zoom_hud_timer)
            except Exception:
                pass

        if not hasattr(self, "_zoom_hud") or self._zoom_hud is None:
            self._zoom_hud = ctk.CTkFrame(
                self,
                fg_color=theme.BG_CARD,
                border_width=1,
                border_color=theme.BORDER_COLOR,
                corner_radius=10,
            )
            self._zoom_hud_lbl = ctk.CTkLabel(
                self._zoom_hud,
                text="",
                font=(theme.FONT_DISPLAY, 12, "bold"),
                text_color=theme.TEXT_PRIMARY,
                padx=14,
                pady=6,
            )
            self._zoom_hud_lbl.pack()

        # Update styling & value
        self._zoom_hud.configure(
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_COLOR,
        )
        self._zoom_hud_lbl.configure(
            text=f"🔍  Zoom: {percent}%",
            text_color=theme.TEXT_PRIMARY,
        )

        # Show in bottom-right corner above status/footer
        self._zoom_hud.place(relx=0.96, rely=0.94, anchor="se")
        self._zoom_hud.lift()

        def _hide_hud():
            if hasattr(self, "_zoom_hud") and self._zoom_hud:
                try:
                    self._zoom_hud.place_forget()
                except Exception:
                    pass

        self._zoom_hud_timer = self.after(1200, _hide_hud)

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
                on_notification_click=self.show_and_open_notifications,
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
        # Temporarily force window topmost to bypass Windows OS background focus lock
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.focus_force()

    def _start_ipc_server(self) -> None:
        """Starts a lightweight local socket listener on 127.0.0.1:49281 to receive activation commands."""
        def _listen():
            import socket
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", 49281))
                server.listen(5)
                while True:
                    conn, _ = server.accept()
                    try:
                        data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
                        if "open_notifications" in data:
                            self.after(0, self.show_and_open_notifications)
                        else:
                            self.after(0, self.show_window)
                    except Exception:
                        pass
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass
            except Exception:
                pass

        threading.Thread(target=_listen, daemon=True).start()

    def show_and_open_notifications(self) -> None:
        """Restores window and opens notification modal when a desktop notification is clicked."""
        self.after(0, self._restore_and_open_notifications)

    def _restore_and_open_notifications(self) -> None:
        self._restore_window()
        self.after(120, self._open_notifications)

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
        if self.tray and self.tray.tray_icon:
            try:
                self.tray.tray_icon.stop()
            except Exception:
                pass
        try:
            self.after(0, self.destroy)
        except Exception:
            sys.exit(0)


def launch_app() -> None:
    """Entrypoint function to launch the Prior desktop GUI application."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    # Ensure profile theme and default color theme are configured before window instantiation
    profile = database.get_profile()
    initial_mode = profile.get("theme", "light")
    ctk.set_appearance_mode(initial_mode)
    ctk.set_default_color_theme("blue")

    app = PriorApp()
    app.mainloop()


if __name__ == "__main__":
    launch_app()
