from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
import webbrowser
import winreg
from pathlib import Path
from typing import Optional

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import pystray
except ImportError:
    pystray = None

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

try:
    from PIL import Image
except ImportError:
    Image = None

import proxy.tg_ws_proxy as tg_ws_proxy

# --- ИМПОРТ НАШЕГО МОДУЛЯ HWID ---
try:
    from proxy.hwid_auth import get_hwid, generate_key, is_activated, save_key
except ImportError as _err:
    _err_msg = str(_err)
    def is_activated(): return False
    def get_hwid(): return f"ОШИБКА_ИМПОРТА: {_err_msg}"
    def generate_key(hwid): return "ERROR"
    def save_key(key): pass
# ---------------------------------

from utils.tray_common import (
    APP_NAME, DEFAULT_CONFIG, FIRST_RUN_MARKER, IS_FROZEN, LOG_FILE,
    acquire_lock, bootstrap, check_ipv6_warning, ctk_run_dialog,
    ensure_ctk_thread, ensure_dirs, load_config, load_icon, log,
    maybe_notify_update, quit_ctk, release_lock, restart_proxy,
    save_config, start_proxy, stop_proxy, tg_proxy_url,
)
from ui.ctk_tray_ui import (
    install_tray_config_buttons, install_tray_config_form,
    populate_first_run_window, tray_settings_scroll_and_footer,
    validate_config_form,
)
from ui.ctk_theme import (
    CONFIG_DIALOG_FRAME_PAD, CONFIG_DIALOG_SIZE, FIRST_RUN_SIZE,
    create_ctk_toplevel, ctk_theme_for_platform, main_content_frame,
)

_tray_icon: Optional[object] = None
_config: dict = {}
_exiting = False

ICON_PATH = str(Path(__file__).parent / "icon.ico")

# win32 dialogs

_u32 = ctypes.windll.user32
_u32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
_u32.MessageBoxW.restype = ctypes.c_int

_MB_OK_ERR = 0x10
_MB_OK_INFO = 0x40
_MB_YESNO_Q = 0x24
_IDYES = 6


def _show_error(text: str, title: str = "TG WS Proxy — Ошибка") -> None:
    _u32.MessageBoxW(None, text, title, _MB_OK_ERR)


def _show_info(text: str, title: str = "TG WS Proxy") -> None:
    _u32.MessageBoxW(None, text, title, _MB_OK_INFO)


def _ask_yes_no(text: str, title: str = "TG WS Proxy") -> bool:
    return _u32.MessageBoxW(None, text, title, _MB_YESNO_Q) == _IDYES


# autostart (registry)

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _supports_autostart() -> bool:
    return IS_FROZEN


def _autostart_command() -> str:
    return f'"{sys.executable}"'


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, APP_NAME)
        return str(val).strip() == _autostart_command().strip()
    except (FileNotFoundError, OSError):
        return False


def set_autostart_enabled(enabled: bool) -> None:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
