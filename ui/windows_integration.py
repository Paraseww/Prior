"""
ui/windows_integration.py
Windows Shell & Taskbar integration for Prior.
Configures AppUserModelID, Window PropertyStore (RelaunchCommand, RelaunchIcon,
RelaunchDisplayName), Start Menu shortcut registration, and application icons
so that the Windows Taskbar and its right-click Jump List menu display 'Prior'
with Prior's custom logo instead of generic 'Python'.
"""

import ctypes
from ctypes import (
    byref,
    c_ubyte,
    c_ulong,
    c_ushort,
    c_void_p,
    POINTER,
    Structure,
    WINFUNCTYPE,
    HRESULT,
)
import os
from pathlib import Path
import sys
import threading
from typing import Any, Optional

APP_USER_MODEL_ID = "parami.prior.taskmanager.1.0"
APP_DISPLAY_NAME = "Prior"

# Assets and paths
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICO = ASSETS_DIR / "icon.ico"
SCRIPT_PATH = BASE_DIR / "project.py"

_CACHED_ICON_PHOTO = None
_CACHED_HICON_BIG = None
_CACHED_HICON_SMALL = None


if sys.platform == "win32":
    from ctypes import wintypes

    class GUID(Structure):
        _fields_ = [
            ("Data1", c_ulong),
            ("Data2", c_ushort),
            ("Data3", c_ushort),
            ("Data4", c_ubyte * 8),
        ]

    class PROPERTYKEY(Structure):
        _fields_ = [
            ("fmtid", GUID),
            ("pid", c_ulong),
        ]

    class PROPVARIANT(Structure):
        _fields_ = [
            ("vt", wintypes.USHORT),
            ("wReserved1", wintypes.USHORT),
            ("wReserved2", wintypes.USHORT),
            ("wReserved3", wintypes.USHORT),
            ("pwszVal", wintypes.LPWSTR),
            ("dummy", c_ulong * 2),
        ]

    class IPropertyStoreVtbl(Structure):
        pass

    class IPropertyStore(Structure):
        _fields_ = [("lpVtbl", POINTER(IPropertyStoreVtbl))]

    IPropertyStoreVtbl._fields_ = [
        ("QueryInterface", c_void_p),
        ("AddRef", c_void_p),
        ("Release", WINFUNCTYPE(c_ulong, POINTER(IPropertyStore))),
        ("GetCount", c_void_p),
        ("GetAt", c_void_p),
        ("GetValue", WINFUNCTYPE(HRESULT, POINTER(IPropertyStore), POINTER(PROPERTYKEY), POINTER(PROPVARIANT))),
        ("SetValue", WINFUNCTYPE(HRESULT, POINTER(IPropertyStore), POINTER(PROPERTYKEY), POINTER(PROPVARIANT))),
        ("Commit", WINFUNCTYPE(HRESULT, POINTER(IPropertyStore))),
    ]

    class IShellLinkWVtbl(Structure):
        pass

    class IShellLinkW(Structure):
        _fields_ = [("lpVtbl", POINTER(IShellLinkWVtbl))]

    IShellLinkWVtbl._fields_ = [
        ("QueryInterface", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), POINTER(GUID), POINTER(c_void_p))),
        ("AddRef", WINFUNCTYPE(c_ulong, POINTER(IShellLinkW))),
        ("Release", WINFUNCTYPE(c_ulong, POINTER(IShellLinkW))),
        ("GetPath", c_void_p),
        ("GetIDList", c_void_p),
        ("SetIDList", c_void_p),
        ("GetDescription", c_void_p),
        ("SetDescription", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), wintypes.LPCWSTR)),
        ("GetWorkingDirectory", c_void_p),
        ("SetWorkingDirectory", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), wintypes.LPCWSTR)),
        ("GetArguments", c_void_p),
        ("SetArguments", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), wintypes.LPCWSTR)),
        ("GetHotkey", c_void_p),
        ("SetHotkey", c_void_p),
        ("GetShowCmd", c_void_p),
        ("SetShowCmd", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), ctypes.c_int)),
        ("GetIconLocation", c_void_p),
        ("SetIconLocation", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), wintypes.LPCWSTR, ctypes.c_int)),
        ("SetRelativePath", c_void_p),
        ("Resolve", c_void_p),
        ("SetPath", WINFUNCTYPE(HRESULT, POINTER(IShellLinkW), wintypes.LPCWSTR)),
    ]

    class IPersistFileVtbl(Structure):
        pass

    class IPersistFile(Structure):
        _fields_ = [("lpVtbl", POINTER(IPersistFileVtbl))]

    IPersistFileVtbl._fields_ = [
        ("QueryInterface", c_void_p),
        ("AddRef", c_void_p),
        ("Release", WINFUNCTYPE(c_ulong, POINTER(IPersistFile))),
        ("GetClassID", c_void_p),
        ("IsDirty", c_void_p),
        ("Load", c_void_p),
        ("Save", WINFUNCTYPE(HRESULT, POINTER(IPersistFile), wintypes.LPCOLESTR, wintypes.BOOL)),
        ("SaveCompleted", c_void_p),
        ("GetCurFile", c_void_p),
    ]

    # GUIDs
    CLSID_ShellLink = GUID(0x00021401, 0, 0, (c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
    IID_IShellLinkW = GUID(0x000214F9, 0, 0, (c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
    IID_IPersistFile = GUID(0x0000010B, 0, 0, (c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
    IID_IPropertyStore = GUID(0x886D8EEB, 0x8CF2, 0x4446, (c_ubyte * 8)(0x8D, 0x02, 0xCD, 0xBA, 0x1D, 0xBD, 0xCF, 0x99))

    FMTID_AppUserModel = GUID(0x9F4C2855, 0x9F79, 0x4B39, (c_ubyte * 8)(0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3))
    PKEY_AppUserModel_RelaunchCommand = PROPERTYKEY(FMTID_AppUserModel, 2)
    PKEY_AppUserModel_RelaunchIconResource = PROPERTYKEY(FMTID_AppUserModel, 3)
    PKEY_AppUserModel_RelaunchDisplayNameResource = PROPERTYKEY(FMTID_AppUserModel, 4)
    PKEY_AppUserModel_ID = PROPERTYKEY(FMTID_AppUserModel, 5)


def set_process_app_id() -> None:
    """Sets the explicit AppUserModelID on the current Windows process."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def _get_python_launcher() -> Path:
    """Returns the best python executable path (prefers pythonw.exe to avoid console popup)."""
    if sys.platform == "win32":
        pyw = Path(sys.executable).parent / "pythonw.exe"
        if pyw.exists():
            return pyw
    return Path(sys.executable)


def ensure_start_menu_shortcut() -> None:
    """
    Creates or updates the Windows Start Menu shortcut 'Prior.lnk' with explicit
    AppUserModelID so Windows Taskbar pins and identifies Prior with its own name and logo.
    """
    if sys.platform != "win32":
        return

    try:
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)

        shell_link = POINTER(IShellLinkW)()
        hr = ole32.CoCreateInstance(
            byref(CLSID_ShellLink),
            None,
            1,
            byref(IID_IShellLinkW),
            byref(shell_link),
        )
        if hr != 0 or not shell_link:
            return

        py_exe = _get_python_launcher()
        shell_link.contents.lpVtbl.contents.SetPath(shell_link, str(py_exe))
        shell_link.contents.lpVtbl.contents.SetArguments(shell_link, f'"{SCRIPT_PATH}"')
        shell_link.contents.lpVtbl.contents.SetWorkingDirectory(shell_link, str(BASE_DIR))
        shell_link.contents.lpVtbl.contents.SetDescription(shell_link, "Prior - Eisenhower Matrix Task Manager")
        if ICON_ICO.exists():
            shell_link.contents.lpVtbl.contents.SetIconLocation(shell_link, str(ICON_ICO), 0)

        # Set AppUserModelID on the shortcut's property store
        prop_store_ptr = c_void_p()
        hr_prop = shell_link.contents.lpVtbl.contents.QueryInterface(
            shell_link,
            byref(IID_IPropertyStore),
            byref(prop_store_ptr),
        )
        if hr_prop == 0 and prop_store_ptr:
            prop_store = ctypes.cast(prop_store_ptr, POINTER(IPropertyStore))
            pv = PROPVARIANT()
            pv.vt = 31  # VT_LPWSTR
            pwsz = wintypes.LPWSTR()
            ctypes.windll.shlwapi.SHStrDupW(APP_USER_MODEL_ID, byref(pwsz))
            pv.pwszVal = pwsz
            prop_store.contents.lpVtbl.contents.SetValue(prop_store, byref(PKEY_AppUserModel_ID), byref(pv))
            prop_store.contents.lpVtbl.contents.Commit(prop_store)
            ctypes.windll.ole32.PropVariantClear(byref(pv))
            prop_store.contents.lpVtbl.contents.Release(prop_store)

        # Save shortcut to Start Menu Programs
        persist_file_ptr = c_void_p()
        hr_persist = shell_link.contents.lpVtbl.contents.QueryInterface(
            shell_link,
            byref(IID_IPersistFile),
            byref(persist_file_ptr),
        )
        if hr_persist == 0 and persist_file_ptr:
            persist_file = ctypes.cast(persist_file_ptr, POINTER(IPersistFile))
            programs_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            programs_dir.mkdir(parents=True, exist_ok=True)
            shortcut_path = programs_dir / "Prior.lnk"
            persist_file.contents.lpVtbl.contents.Save(persist_file, str(shortcut_path), True)
            persist_file.contents.lpVtbl.contents.Release(persist_file)

        shell_link.contents.lpVtbl.contents.Release(shell_link)
    except Exception:
        pass


def ensure_protocol_registration() -> None:
    """
    Registers the 'prior://' custom URI protocol in Windows Registry (HKCU).
    Allows desktop toast notifications and action buttons to activate the running
    Prior app when clicked, even from Windows Notification Center / Action Center.
    """
    if sys.platform != "win32":
        return
    try:
        import winreg
        py_exe = _get_python_launcher()
        command = f'"{py_exe}" "{SCRIPT_PATH}" --open-notifications "%1"'
        key_path = r"Software\Classes\prior"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Prior Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(key, r"shell\open\command") as cmd_key:
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
    except Exception:
        pass


def set_window_taskbar_properties(hwnd: int) -> None:
    """
    Sets AppUserModelID and Taskbar Jump List relaunch properties (DisplayName, Icon, Command)
    directly on the given HWND property store so Windows right-click menu shows 'Prior'.
    """
    if sys.platform != "win32" or not hwnd:
        return

    try:
        propstore = POINTER(IPropertyStore)()
        hr = ctypes.windll.shell32.SHGetPropertyStoreForWindow(
            hwnd,
            byref(IID_IPropertyStore),
            byref(propstore),
        )
        if hr != 0 or not propstore:
            return

        def _set_str_prop(key: PROPERTYKEY, val_str: str) -> None:
            pv = PROPVARIANT()
            pv.vt = 31  # VT_LPWSTR
            pwsz = wintypes.LPWSTR()
            ctypes.windll.shlwapi.SHStrDupW(val_str, byref(pwsz))
            pv.pwszVal = pwsz
            propstore.contents.lpVtbl.contents.SetValue(propstore, byref(key), byref(pv))
            ctypes.windll.ole32.PropVariantClear(byref(pv))

        py_exe = _get_python_launcher()
        relaunch_cmd = f'"{py_exe}" "{SCRIPT_PATH}"'
        relaunch_icon = f"{ICON_ICO},0" if ICON_ICO.exists() else ""

        _set_str_prop(PKEY_AppUserModel_ID, APP_USER_MODEL_ID)
        _set_str_prop(PKEY_AppUserModel_RelaunchDisplayNameResource, APP_DISPLAY_NAME)
        _set_str_prop(PKEY_AppUserModel_RelaunchCommand, relaunch_cmd)
        if relaunch_icon:
            _set_str_prop(PKEY_AppUserModel_RelaunchIconResource, relaunch_icon)

        propstore.contents.lpVtbl.contents.Commit(propstore)
        propstore.contents.lpVtbl.contents.Release(propstore)
    except Exception:
        pass


def apply_prior_icon(window: Any) -> None:
    """
    Applies the custom Prior application logo to any Tk/CTk/CTkToplevel window
    and registers Taskbar Jump List identity properties on the window handle.
    """
    global _CACHED_ICON_PHOTO, _CACHED_HICON_BIG, _CACHED_HICON_SMALL

    window._iconbitmap_method_called = True

    try:
        from PIL import Image, ImageTk

        if _CACHED_ICON_PHOTO is None and ICON_PNG.exists():
            base_img = Image.open(ICON_PNG).convert("RGBA")
            _CACHED_ICON_PHOTO = ImageTk.PhotoImage(base_img.resize((128, 128), Image.Resampling.LANCZOS))

        if _CACHED_ICON_PHOTO is not None:
            window.iconphoto(True, _CACHED_ICON_PHOTO)
            window._icon_photo = _CACHED_ICON_PHOTO

        if sys.platform == "win32" and ICON_ICO.exists():
            try:
                window.iconbitmap(str(ICON_ICO))
            except Exception:
                pass

            try:
                wid = window.winfo_id()
                if wid:
                    parent = ctypes.windll.user32.GetParent(wid) or wid

                    if _CACHED_HICON_BIG is None:
                        _CACHED_HICON_BIG = ctypes.windll.user32.LoadImageW(None, str(ICON_ICO), 1, 48, 48, 0x00000010)
                        _CACHED_HICON_SMALL = ctypes.windll.user32.LoadImageW(None, str(ICON_ICO), 1, 16, 16, 0x00000010)

                    for h in (wid, parent):
                        if _CACHED_HICON_BIG:
                            ctypes.windll.user32.SendMessageW(h, 0x0080, 1, _CACHED_HICON_BIG)
                        if _CACHED_HICON_SMALL:
                            ctypes.windll.user32.SendMessageW(h, 0x0080, 0, _CACHED_HICON_SMALL)
                        # Set Windows Taskbar Jump List properties on both window handles
                        set_window_taskbar_properties(h)
            except Exception:
                pass
    except Exception:
        pass


def init_windows_integration(window: Optional[Any] = None) -> None:
    """
    Complete Windows Taskbar initialization: sets AppUserModelID, generates
    Start Menu shortcut in the background, registers prior:// URI protocol,
    and applies icon & taskbar properties.
    """
    set_process_app_id()
    # Create / update Start Menu shortcut asynchronously to ensure fast window startup
    threading.Thread(target=ensure_start_menu_shortcut, daemon=True).start()
    threading.Thread(target=ensure_protocol_registration, daemon=True).start()
    if window is not None:
        apply_prior_icon(window)


# Initialize process AppUserModelID immediately upon import
set_process_app_id()
