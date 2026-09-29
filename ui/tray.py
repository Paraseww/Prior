"""
ui/tray.py
Windows System Tray background service for Prior using pystray.
Handles minimize-to-tray, quick action menu, and Windows startup registry management.
"""

import os
from pathlib import Path
import sys
import threading
from typing import Any, Callable, Optional
from PIL import Image
import pystray
from pystray import Menu, MenuItem

# Path to icon assets
BASE_DIR = Path(__file__).resolve().parent.parent
ICON_PNG = BASE_DIR / "assets" / "icon.png"
ICON_ICO = BASE_DIR / "assets" / "icon.ico"


def get_tray_image() -> Image.Image:
    """Loads the application icon for system tray, with dynamic fallback."""
    if ICON_PNG.exists():
        img = Image.open(ICON_PNG)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img
    elif ICON_ICO.exists():
        img = Image.open(ICON_ICO)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img
    else:
        # 32x32 Fallback icon
        img = Image.new("RGBA", (32, 32), (99, 102, 241, 255))
        return img


# ============================================================================
# Windows Startup Registry Integration (winreg)
# ============================================================================

def is_windows_startup_enabled() -> bool:
    """Checks if Prior is configured to launch on Windows startup."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        try:
            val, _ = winreg.QueryValueEx(key, "Prior")
            winreg.CloseKey(key)
            return bool(val)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def set_windows_startup(enable: bool) -> bool:
    """Enables or disables launch on Windows startup via HKCU Run registry key."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enable:
            exe_path = sys.executable
            # If running as python script or compiled exe
            if getattr(sys, "frozen", False):
                cmd = f'"{exe_path}"'
            else:
                script_path = str(BASE_DIR / "project.py")
                cmd = f'"{exe_path}" "{script_path}"'
            winreg.SetValueEx(key, "Prior", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "Prior")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ============================================================================
# Tray Service Manager
# ============================================================================

class TrayService:
    """
    Manages the background system tray icon and context menu.
    """

    def __init__(
        self,
        on_show_app: Callable[[], None],
        on_quick_add: Callable[[], None],
        on_exit_app: Callable[[], None],
    ) -> None:
        self.on_show_app = on_show_app
        self.on_quick_add = on_quick_add
        self.on_exit_app = on_exit_app

        self.tray_icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the system tray icon in a dedicated background daemon thread."""
        image = get_tray_image()

        def _toggle_startup(icon: Any, item: Any) -> None:
            new_state = not item.checked
            set_windows_startup(new_state)

        def _is_startup_checked(_: Any) -> bool:
            return is_windows_startup_enabled()

        menu = Menu(
            MenuItem("📌 Open Prior", lambda: self.on_show_app(), default=True),
            MenuItem("➕ Quick Add Task", lambda: self.on_quick_add()),
            Menu.SEPARATOR,
            MenuItem(
                "🚀 Launch on Startup",
                _toggle_startup,
                checked=_is_startup_checked,
            ),
            Menu.SEPARATOR,
            MenuItem("✕ Exit Prior", lambda: self.stop_and_exit()),
        )

        self.tray_icon = pystray.Icon("Prior", image, "Prior — Time Management", menu)
        self._thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self._thread.start()

    def stop_and_exit(self) -> None:
        """Stops tray icon and terminates the app."""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.on_exit_app()

    def notify(self, title: str, message: str) -> None:
        """Sends a desktop balloon notification via tray icon."""
        if self.tray_icon:
            try:
                self.tray_icon.notify(title=title, message=message)
            except Exception:
                pass
