"""
ui/tray.py
Windows System Tray background service for Prior using pystray.
Handles minimize-to-tray, quick action menu, and Windows startup registry management.
"""

import os
from pathlib import Path
import sys
import tempfile
import threading
from typing import Any, Callable, Optional

# Ensure temp directory points to workspace drive G: to prevent disk full error
_local_tmp = Path(__file__).resolve().parent.parent / ".tmp"
_local_tmp.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(_local_tmp)
os.environ["TMP"] = str(_local_tmp)
tempfile.tempdir = str(_local_tmp)

from PIL import Image
import pystray
from pystray import Menu, MenuItem

# Path to icon assets
BASE_DIR = Path(__file__).resolve().parent.parent
ICON_PNG = BASE_DIR / "assets" / "icon.png"


def get_tray_image() -> Image.Image:
    """Loads the application icon purely from PNG for system tray."""
    if ICON_PNG.exists():
        img = Image.open(ICON_PNG)
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
                cmd = f'"{exe_path}" --minimized'
            else:
                py_path = Path(exe_path)
                if py_path.name.lower() == "python.exe":
                    pyw_path = py_path.with_name("pythonw.exe")
                    if pyw_path.exists():
                        exe_path = str(pyw_path)
                script_path = str(BASE_DIR / "project.py")
                cmd = f'"{exe_path}" "{script_path}" --minimized'
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
# Windows Notification Click & Activation Hook
# ============================================================================

def _patch_pystray_win32_notification_click() -> None:
    """
    Hooks pystray's Win32 window message procedure so that clicking on a desktop
    notification balloon/toast (NIN_BALLOONUSERCLICK) or double-clicking the tray icon
    triggers the callback to bring the application to the foreground.
    """
    if sys.platform != "win32":
        return

    try:
        from pystray import _win32 as pystray_win32

        if getattr(pystray_win32, "_prior_notification_patched", False):
            return

        _orig_on_notify = pystray_win32.Icon._on_notify

        def _patched_on_notify(self: Any, wparam: Any, lparam: Any) -> Any:
            # 0x0405 = NIN_BALLOONUSERCLICK (User clicked the desktop balloon/toast notification)
            if lparam == 0x0405:
                balloon_cb = getattr(self, "_balloon_click_callback", None)
                if callable(balloon_cb):
                    try:
                        balloon_cb()
                    except Exception:
                        pass
                    return 0
                self()
                return 0

            # 514 = WM_LBUTTONUP, 515 = WM_LBUTTONDBLCLK, 1024 = NIN_SELECT, 1025 = NIN_KEYSELECT
            if lparam in (514, 515, 1024, 1025):
                self()
                return 0

            return _orig_on_notify(self, wparam, lparam)

        pystray_win32.Icon._on_notify = _patched_on_notify
        pystray_win32._prior_notification_patched = True
    except Exception:
        pass


_patch_pystray_win32_notification_click()


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
        on_notification_click: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_show_app = on_show_app
        self.on_quick_add = on_quick_add
        self.on_exit_app = on_exit_app
        self.on_notification_click = on_notification_click or on_show_app

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
            MenuItem("Open Prior", lambda: self.on_show_app(), default=True),
            MenuItem("Quick Add Task", lambda: self.on_quick_add()),
            Menu.SEPARATOR,
            MenuItem(
                "Launch on Startup",
                _toggle_startup,
                checked=_is_startup_checked,
            ),
            Menu.SEPARATOR,
            MenuItem("Exit Prior", lambda: self.stop_and_exit()),
        )

        self.tray_icon = pystray.Icon("Prior", image, "Prior", menu)
        # Attach notification click callback to icon instance
        self.tray_icon._balloon_click_callback = self.on_notification_click
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
        """Sends a native Windows Toast notification, with tray balloon fallback."""
        if sys.platform == "win32":
            threading.Thread(
                target=self._send_windows_toast,
                args=(title, message),
                daemon=True,
            ).start()
        elif self.tray_icon:
            try:
                self.tray_icon.notify(title=title, message=message)
            except Exception:
                pass

    def _send_windows_toast(self, title: str, message: str) -> None:
        """Delivers a native Windows 10/11 Toast notification with click-to-activate protocol."""
        try:
            import subprocess
            clean_title = (
                title.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            clean_message = (
                message.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            xml_str = (
                f'<toast activationType="protocol" launch="prior://open">'
                f'<visual><binding template="ToastGeneric">'
                f'<text>{clean_title}</text>'
                f'<text>{clean_message}</text>'
                f'</binding></visual>'
                f'<actions><action content="Open Prior" activationType="protocol" arguments="prior://open"/></actions>'
                f'</toast>'
            )
            safe_xml = xml_str.replace("'", "''")
            ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
$xml.LoadXml('{safe_xml}')
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('parami.prior.taskmanager.1.0').Show($toast)
"""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                creationflags=0x08000000,  # CREATE_NO_WINDOW
                timeout=5,
                check=False,
            )
            if res.returncode != 0 and self.tray_icon:
                try:
                    self.tray_icon.notify(title=title, message=message)
                except Exception:
                    pass
        except Exception:
            if self.tray_icon:
                try:
                    self.tray_icon.notify(title=title, message=message)
                except Exception:
                    pass
