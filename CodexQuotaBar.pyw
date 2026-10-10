"""Transparent two-line quota overlay anchored to MyDockFinder's top bar."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import traceback
from pathlib import Path
from tkinter import Menu, Tk

from PIL import Image, ImageDraw, ImageFont


APP_NAME = "CodexQuotaBar"
APP_VERSION = "1.10.2"
BAR_CLASS = "MyFinderApp"
POLL_SECONDS = 60
WIDGET_WIDTH = 94
WIDGET_HEIGHT = 30
SURFACE_CLASS = "CodexQuotaBarNativeSurface"
_ACTIVE_BAR = None
_SURFACE_WNDPROC = None
_INSTANCE_MUTEX = None


class _WindowClassEx(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("style", ctypes.wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ("hIconSm", ctypes.c_void_p),
    ]


def _surface_window_proc(hwnd, message, wparam, lparam):
    app = _ACTIVE_BAR
    if app is not None:
        try:
            result = app._native_window_message(hwnd, message, wparam, lparam)
            if result is not None:
                return result
        except Exception as exc:
            log_message(f"Native MyDockFinder surface input failed: {exc!r}")
    return ctypes.windll.user32.DefWindowProcW(hwnd, message, wparam, lparam)


def _register_surface_class(user32, kernel32) -> None:
    global _SURFACE_WNDPROC
    if _SURFACE_WNDPROC is not None:
        return
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )
    _SURFACE_WNDPROC = callback_type(_surface_window_proc)
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(_WindowClassEx)]
    user32.RegisterClassExW.restype = ctypes.wintypes.ATOM
    kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    user32.LoadCursorW.argtypes = [ctypes.c_void_p, ctypes.wintypes.LPCWSTR]
    user32.LoadCursorW.restype = ctypes.c_void_p
    window_class = _WindowClassEx()
    window_class.cbSize = ctypes.sizeof(_WindowClassEx)
    window_class.lpfnWndProc = ctypes.cast(_SURFACE_WNDPROC, ctypes.c_void_p).value
    window_class.hInstance = kernel32.GetModuleHandleW(None)
    window_class.hCursor = user32.LoadCursorW(
        None, ctypes.cast(ctypes.c_void_p(32512), ctypes.wintypes.LPCWSTR)
    )
    window_class.lpszClassName = SURFACE_CLASS
    atom = user32.RegisterClassExW(ctypes.byref(window_class))
    if not atom and ctypes.get_last_error() != 1410:  # ERROR_CLASS_ALREADY_EXISTS
        raise ctypes.WinError(ctypes.get_last_error())


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


class _MouseLlHookData(ctypes.Structure):
    _fields_ = [
        ("pt", _Point),
        ("mouseData", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _Size(ctypes.Structure):
    _fields_ = [("cx", ctypes.wintypes.LONG), ("cy", ctypes.wintypes.LONG)]


class _BlendFunction(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


class _RgbQuad(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class _BitmapInfo(ctypes.Structure):
    _fields_ = [("bmiHeader", _BitmapInfoHeader), ("bmiColors", _RgbQuad * 1)]


class LayeredSurface:
    """A transparent topmost window kept at a stable position over MyFinder."""

    def __init__(self, root: Tk):
        self.root = root
        self.width = WIDGET_WIDTH
        self.height = WIDGET_HEIGHT
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self.user32.SetWindowPos.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.UINT,
        ]
        self.user32.SetWindowPos.restype = ctypes.wintypes.BOOL
        self.user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindow.restype = ctypes.wintypes.BOOL
        self.user32.CreateWindowExW.argtypes = [
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.HWND,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.wintypes.LPVOID,
        ]
        self.user32.CreateWindowExW.restype = ctypes.wintypes.HWND
        self.user32.DestroyWindow.argtypes = [ctypes.wintypes.HWND]
        self.user32.DestroyWindow.restype = ctypes.wintypes.BOOL
        self.user32.SetCapture.argtypes = [ctypes.wintypes.HWND]
        self.user32.SetCapture.restype = ctypes.wintypes.HWND
        self.user32.ReleaseCapture.argtypes = []
        self.user32.ReleaseCapture.restype = ctypes.wintypes.BOOL
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(_Point)]
        self.user32.GetCursorPos.restype = ctypes.wintypes.BOOL
        self.user32.IsWindow.argtypes = [ctypes.wintypes.HWND]
        self.user32.IsWindow.restype = ctypes.wintypes.BOOL
        self.user32.GetDC.argtypes = [ctypes.wintypes.HWND]
        self.user32.GetDC.restype = ctypes.wintypes.HDC
        self.user32.ReleaseDC.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.HDC,
        ]
        self.user32.ReleaseDC.restype = ctypes.c_int
        self.user32.UpdateLayeredWindow.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.HDC,
            ctypes.POINTER(_Point),
            ctypes.POINTER(_Size),
            ctypes.wintypes.HDC,
            ctypes.POINTER(_Point),
            ctypes.wintypes.DWORD,
            ctypes.POINTER(_BlendFunction),
            ctypes.wintypes.DWORD,
        ]
        self.user32.UpdateLayeredWindow.restype = ctypes.wintypes.BOOL
        self.gdi32.CreateCompatibleDC.argtypes = [ctypes.wintypes.HDC]
        self.gdi32.CreateCompatibleDC.restype = ctypes.wintypes.HDC
        self.gdi32.CreateDIBSection.argtypes = [
            ctypes.wintypes.HDC,
            ctypes.POINTER(_BitmapInfo),
            ctypes.wintypes.UINT,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
        ]
        self.gdi32.CreateDIBSection.restype = ctypes.wintypes.HBITMAP
        self.gdi32.SelectObject.argtypes = [
            ctypes.wintypes.HDC,
            ctypes.wintypes.HGDIOBJ,
        ]
        self.gdi32.SelectObject.restype = ctypes.wintypes.HGDIOBJ
        self.gdi32.DeleteObject.argtypes = [ctypes.wintypes.HGDIOBJ]
        self.gdi32.DeleteObject.restype = ctypes.wintypes.BOOL
        self.gdi32.DeleteDC.argtypes = [ctypes.wintypes.HDC]
        self.gdi32.DeleteDC.restype = ctypes.wintypes.BOOL

        _register_surface_class(self.user32, self.kernel32)
        self.instance = self.kernel32.GetModuleHandleW(None)
        self.hwnd = None
        # This tracks MyFinder; the overlay itself remains a top-level window.
        self.parent_hwnd: int | None = None
        self.local_position = (0, 0)
        self.host_origin = (0, 0)
        self.screen_origin = (0, 0)
        self.window_shown = False
        self.last_pixels: bytes | bytearray | None = None

        screen_dc = self.user32.GetDC(None)
        if not screen_dc:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            self.memory_dc = self.gdi32.CreateCompatibleDC(screen_dc)
            info = _BitmapInfo()
            info.bmiHeader = _BitmapInfoHeader(
                ctypes.sizeof(_BitmapInfoHeader),
                self.width,
                -self.height,
                1,
                32,
                0,
                self.width * self.height * 4,
                0,
                0,
                0,
                0,
            )
            self.pixel_data = ctypes.c_void_p()
            self.bitmap = self.gdi32.CreateDIBSection(
                screen_dc,
                ctypes.byref(info),
                0,
                ctypes.byref(self.pixel_data),
                None,
                0,
            )
            if not self.memory_dc or not self.bitmap or not self.pixel_data.value:
                raise ctypes.WinError(ctypes.get_last_error())
            self.previous_bitmap = self.gdi32.SelectObject(self.memory_dc, self.bitmap)
        finally:
            self.user32.ReleaseDC(None, screen_dc)

    def attach_to_finder(
        self,
        parent_hwnd: int,
        local_x: int,
        local_y: int,
        host_left: int,
        host_top: int,
    ) -> None:
        if not self.user32.IsWindow(parent_hwnd):
            raise RuntimeError("MyDockFinder 顶栏窗口已关闭。")
        anchor_changed = self.parent_hwnd != parent_hwnd
        if self.hwnd and not self.user32.IsWindow(self.hwnd):
            self.hwnd = None
            self.window_shown = False
        if self.hwnd is None:
            self.hwnd = self.user32.CreateWindowExW(
                0x08000000 | 0x00080000 | 0x00000080 | 0x00000008,
                # WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
                SURFACE_CLASS,
                "Codex quota",
                0x80000000,  # WS_POPUP; initially hidden until its first frame is ready
                host_left + local_x,
                host_top + local_y,
                self.width,
                self.height,
                None,
                None,
                self.instance,
                None,
            )
            if not self.hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            self.parent_hwnd = parent_hwnd
            log_message(
                f"Created transparent topmost quota overlay {int(self.hwnd):#x}, "
                f"anchored to MyDockFinder HWND {parent_hwnd:#x}"
            )
        elif anchor_changed:
            self.parent_hwnd = parent_hwnd

        new_screen_origin = (host_left + local_x, host_top + local_y)
        position_changed = self.screen_origin != new_screen_origin
        self.local_position = (local_x, local_y)
        self.host_origin = (host_left, host_top)
        self.screen_origin = new_screen_origin
        if position_changed:
            ok = self.user32.SetWindowPos(
                self.hwnd,
                ctypes.wintypes.HWND(-1),  # HWND_TOPMOST
                *self.screen_origin,
                self.width,
                self.height,
                0x0010 | 0x0200 | 0x0400,  # NOACTIVATE | NOOWNERZORDER | NOSENDCHANGING
            )
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())
        if self.last_pixels is not None:
            self._update_pixels(self.last_pixels)

    def update(self, bgra_premultiplied: bytes | bytearray) -> None:
        self.last_pixels = bgra_premultiplied
        if self.hwnd and self.user32.IsWindow(self.hwnd):
            self._update_pixels(bgra_premultiplied)

    def show(self) -> None:
        if self.hwnd and not self.window_shown:
            self.user32.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
            self.window_shown = True

    def hide(self) -> None:
        if self.hwnd and self.window_shown:
            self.user32.ShowWindow(self.hwnd, 0)  # SW_HIDE
            self.window_shown = False

    def _update_pixels(self, bgra_premultiplied: bytes | bytearray) -> None:
        ctypes.memmove(self.pixel_data, bytes(bgra_premultiplied), self.width * self.height * 4)
        destination = _Point(*self.screen_origin)
        size = _Size(self.width, self.height)
        source = _Point(0, 0)
        blend = _BlendFunction(0, 0, 255, 1)
        ok = self.user32.UpdateLayeredWindow(
            self.hwnd,
            None,
            ctypes.byref(destination),
            ctypes.byref(size),
            self.memory_dc,
            ctypes.byref(source),
            0,
            ctypes.byref(blend),
            2,
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        self.detach()
        if getattr(self, "memory_dc", None):
            self.gdi32.SelectObject(self.memory_dc, self.previous_bitmap)
            self.gdi32.DeleteObject(self.bitmap)
            self.gdi32.DeleteDC(self.memory_dc)
            self.memory_dc = None

    def detach(self) -> None:
        if self.hwnd and self.user32.IsWindow(self.hwnd):
            self.user32.DestroyWindow(self.hwnd)
        self.hwnd = None
        self.parent_hwnd = None
        self.window_shown = False


def enable_per_monitor_dpi() -> None:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass


def settings_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


def log_message(message: str) -> None:
    try:
        log_path = settings_path().with_name("app.log")
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def acquire_single_instance() -> bool:
    """Keep repeated launches from creating duplicate overlays and mouse hooks."""
    global _INSTANCE_MUTEX
    if os.name != "nt":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.LPCWSTR,
    ]
    kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, "Local\\CodexQuotaBar.Singleton")
    if not handle:
        log_message(
            f"Could not create single-instance mutex: {ctypes.WinError(ctypes.get_last_error())!r}"
        )
        return True
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        log_message("Ignored duplicate launch; another instance is already running.")
        return False
    _INSTANCE_MUTEX = handle
    return True


def load_settings() -> dict:
    defaults = {"position_ratio": 0.572, "locked": False, "opacity": 0.94}
    try:
        raw = json.loads(settings_path().read_text(encoding="utf-8"))
        defaults.update(raw if isinstance(raw, dict) else {})
    except (OSError, ValueError):
        pass
    try:
        defaults["position_ratio"] = min(0.98, max(0.0, float(defaults["position_ratio"])))
        defaults["opacity"] = min(1.0, max(0.5, float(defaults["opacity"])))
    except (TypeError, ValueError):
        defaults["position_ratio"] = 0.572
        defaults["opacity"] = 0.94
    defaults["locked"] = bool(defaults["locked"])
    return defaults


def save_settings(settings: dict) -> None:
    try:
        settings_path().write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def find_codex_executable() -> str | None:
    found = shutil.which("codex.exe") or shutil.which("codex")
    if found:
        return found

    local = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    if local.is_dir():
        candidates = list(local.glob("*/codex.exe"))
        if candidates:
            return str(max(candidates, key=lambda item: item.stat().st_mtime))
    return None


class CodexAppServer:
    """Read quota through Codex's local app-server, without handling tokens here."""

    def __init__(self, executable: str):
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            [executable, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creation_flags,
        )
        self.messages: queue.Queue = queue.Queue()
        self.next_id = 0
        self.write_lock = threading.Lock()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

        try:
            init = self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "codex_quota_bar",
                        "title": "Codex Quota Bar",
                        "version": APP_VERSION,
                    },
                    "capabilities": {"experimentalApi": True},
                },
                timeout=20,
            )
            if "error" in init:
                raise RuntimeError(error_message(init["error"]))
            self.notify("initialized", {})
        except Exception:
            self.close()
            raise

    def _read_loop(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    continue
        finally:
            self.messages.put(None)

    def _send(self, message: dict) -> None:
        if self.process.poll() is not None or self.process.stdin is None:
            raise RuntimeError("Codex app-server 已退出。")
        line = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        with self.write_lock:
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()

    def notify(self, method: str, params: dict) -> None:
        self._send({"method": method, "params": params})

    def request(self, method: str, params: dict, timeout: int = 20) -> dict:
        self.next_id += 1
        request_id = self.next_id
        self._send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                message = self.messages.get(timeout=max(0.05, deadline - time.monotonic()))
            except queue.Empty:
                break
            if message is None:
                raise RuntimeError("Codex app-server 连接已关闭。")
            if message.get("id") == request_id:
                return message
        raise TimeoutError("等待 Codex app-server 响应超时。")

    def read_quota(self) -> tuple[int | None, int | None]:
        response = self.request("account/rateLimits/read", {})
        if "error" in response:
            raise RuntimeError(error_message(response["error"]))
        return parse_quota(response.get("result", {}))

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.terminate()
            except Exception:
                pass


def error_message(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("message") or value.get("code") or "Codex 请求失败")
    return str(value or "Codex 请求失败")


def get_number(mapping: dict, *names: str) -> float | None:
    for name in names:
        value = mapping.get(name)
        try:
            if value is not None:
                number = float(value)
                if number == number:
                    return number
        except (TypeError, ValueError):
            continue
    return None


def parse_quota(result: object) -> tuple[int | None, int | None]:
    if not isinstance(result, dict):
        raise RuntimeError("额度响应格式不正确。")

    snapshots = result.get("rateLimitsByLimitId") or result.get("rate_limits_by_limit_id")
    snapshot = None
    if isinstance(snapshots, dict):
        snapshot = snapshots.get("codex")

    if snapshot is None:
        legacy = result.get("rateLimits") or result.get("rate_limits")
        if isinstance(legacy, dict) and legacy.get("limitId", legacy.get("limit_id", "codex")) == "codex":
            snapshot = legacy
    if not isinstance(snapshot, dict):
        raise RuntimeError("响应中没有 Codex 额度数据。")

    windows = []
    for key in ("primary", "secondary", "primaryWindow", "secondaryWindow"):
        value = snapshot.get(key)
        if isinstance(value, dict):
            windows.append(value)

    five_hour = None
    week = None
    unknown_windows = []
    for window in windows:
        used = get_number(window, "usedPercent", "used_percent")
        duration_mins = get_number(window, "windowDurationMins", "window_duration_mins")
        if duration_mins is None:
            duration_seconds = get_number(
                window, "limitWindowSeconds", "limit_window_seconds"
            )
            if duration_seconds is not None:
                duration_mins = duration_seconds / 60.0
        if used is None:
            continue
        remaining = int(round(max(0.0, min(100.0, 100.0 - used))))

        if duration_mins is not None and 240 <= duration_mins <= 360:
            five_hour = remaining
        elif duration_mins is not None and duration_mins >= 6000:
            week = remaining
        else:
            unknown_windows.append(remaining)

    # Older payloads sometimes omit window duration; use the historical order only then.
    if unknown_windows:
        if five_hour is None:
            five_hour = unknown_windows[0]
        if len(unknown_windows) > 1 and week is None:
            week = unknown_windows[1]
    if five_hour is None and week is None:
        raise RuntimeError("额度响应中没有可用的时间窗口。")
    return five_hour, week


def find_mydock_bar() -> tuple[int, int, int, int, int] | None:
    if os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    enum_windows = user32.EnumWindows
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    enum_windows.argtypes = [callback_type, ctypes.wintypes.LPARAM]
    enum_windows.restype = ctypes.wintypes.BOOL
    is_visible = user32.IsWindowVisible
    get_class_name = user32.GetClassNameW
    get_window_rect = user32.GetWindowRect
    is_visible.argtypes = [ctypes.wintypes.HWND]
    is_visible.restype = ctypes.wintypes.BOOL
    get_class_name.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.LPWSTR,
        ctypes.c_int,
    ]
    get_class_name.restype = ctypes.c_int
    get_window_rect.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(ctypes.wintypes.RECT),
    ]
    get_window_rect.restype = ctypes.wintypes.BOOL

    class_name = ctypes.create_unicode_buffer(128)
    rect = ctypes.wintypes.RECT()
    found: list[tuple[int, int, int, int, int]] = []

    @callback_type
    def callback(hwnd, _lparam):
        if not is_visible(hwnd):
            return True
        class_name.value = ""
        get_class_name(hwnd, class_name, len(class_name))
        if class_name.value == BAR_CLASS and get_window_rect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width >= 1000 and 18 <= height <= 80:
                found.append((int(hwnd), rect.left, rect.top, width, height))
        return True

    enum_windows(callback, 0)
    return max(found, key=lambda item: item[3]) if found else None


class QuotaBar:
    def __init__(self):
        global _ACTIVE_BAR
        enable_per_monitor_dpi()
        _ACTIVE_BAR = self
        self.settings = load_settings()
        self.root = Tk()
        self.root.report_callback_exception = self._report_callback_exception
        self.root.title("Codex Quota Bar")
        self.root.overrideredirect(True)
        self.root.geometry(f"{WIDGET_WIDTH}x{WIDGET_HEIGHT}+0+0")
        self.layered = LayeredSurface(self.root)
        self.mouse_hook = None
        self.mouse_hook_callback = None
        self.text_rgb = (255, 255, 255)
        self.target_text_rgb = self.text_rgb
        self.has_color_sampled = False
        self.color_animation_id = None
        self.color_animation_from = self.text_rgb
        self.color_animation_started = 0.0
        self.color_animation_duration = 0.18
        self.five_value = "5h: --%"
        self.week_value = "Week: --%"
        font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeuib.ttf"
        try:
            self.font = ImageFont.truetype(str(font_path), 36)
        except OSError:
            self.font = ImageFont.load_default(size=36)

        self.drag_origin: tuple[int, int, int, int] | None = None
        self.bar_rect: tuple[int, int, int, int] | None = None
        self.is_visible = False
        self.confirmed_bar: tuple[int, int, int, int, int] | None = None
        self.pending_bar: tuple[int, int, int, int, int] | None = None
        self.pending_bar_count = 0
        self.missing_bar_count = 0
        self.wheel_delta_remainder = 0
        self.is_closing = False
        self.last_success = "等待首次同步"
        self.last_error = ""
        self.messages: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
        self.worker = threading.Thread(target=self._poll_loop, daemon=True)
        self.worker.start()

        self.context = Menu(self.root, tearoff=False)
        self.context.add_command(label="状态：等待同步", state="disabled")
        self.context.add_command(
            label="任意位置 Alt + 滚轮：左右移动额度标签",
            state="disabled",
        )
        self.context.add_separator()
        self.context.add_command(label="立即刷新", command=self._request_refresh)
        self.context.add_command(
            label="打开 ChatGPT", command=lambda: os.startfile("https://chatgpt.com")
        )
        self.context.add_separator()
        from tkinter import BooleanVar

        self.lock_var = BooleanVar(value=self.settings["locked"])
        self.context.add_checkbutton(
            label="锁定位置", variable=self.lock_var, command=self._toggle_lock
        )
        self.context.add_command(label="退出", command=self.close)

        self.root.bind("<ButtonPress-1>", self._drag_start)
        self.root.bind("<B1-Motion>", self._drag_motion)
        self.root.bind("<ButtonRelease-1>", self._drag_end)
        self.root.bind("<Button-3>", self._show_context)
        self.root.bind("<Enter>", self._show_tooltip)
        self.root.bind("<Leave>", self._hide_tooltip)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(250, self._process_messages)
        self.root.after(50, self._poll_text_color)
        self.root.after(500, self._follow_bar)
        self._install_mouse_wheel_hook()
        log_message(f"{APP_NAME} {APP_VERSION} started (pid={os.getpid()}).")

    @staticmethod
    def _report_callback_exception(exc_type, exc_value, exc_traceback) -> None:
        details = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        log_message(f"Unhandled Tk callback exception:\n{details}")

    def _install_mouse_wheel_hook(self) -> None:
        """Use Alt+wheel anywhere to move this quota label along the MyDockFinder bar."""
        if os.name != "nt":
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hook_proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        )
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            hook_proc_type,
            ctypes.c_void_p,
            ctypes.wintypes.DWORD,
        ]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        ]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        user32.IsWindow.argtypes = [ctypes.wintypes.HWND]
        user32.IsWindow.restype = ctypes.wintypes.BOOL
        def hook_proc(code, message, data_pointer):
            if code >= 0 and message == 0x020A:  # WM_MOUSEWHEEL
                try:
                    data = ctypes.cast(
                        data_pointer, ctypes.POINTER(_MouseLlHookData)
                    ).contents
                    if self._move_overlay_by_wheel(user32, data):
                        return 1  # Consume the vertical wheel event.
                except Exception as exc:
                    log_message(f"Alt+wheel overlay movement failed: {exc!r}")
            return user32.CallNextHookEx(
                self.mouse_hook, code, message, data_pointer
            )

        self.mouse_hook_callback = hook_proc_type(hook_proc)
        module = self.layered.kernel32.GetModuleHandleW(None)
        self.mouse_hook = user32.SetWindowsHookExW(
            14, self.mouse_hook_callback, module, 0  # WH_MOUSE_LL
        )
        if not self.mouse_hook:
            self.mouse_hook_callback = None
            log_message(
                f"Could not install mouse wheel hook: {ctypes.WinError(ctypes.get_last_error())!r}"
            )

    def _move_overlay_by_wheel(self, user32, data: _MouseLlHookData) -> bool:
        if not user32.GetAsyncKeyState(0x12) & 0x8000:  # VK_MENU (Alt)
            return False

        if self.settings["locked"]:
            return False
        bar = self.confirmed_bar
        if bar is None:
            return False
        parent_hwnd, _left, _top, _width, _height = bar
        if not user32.IsWindow(parent_hwnd):
            return False

        delta = ctypes.c_short((data.mouseData >> 16) & 0xFFFF).value
        if not delta:
            return False
        # The hook runs outside Tk's UI thread. Queue the wheel delta so the
        # quota overlay itself can be repositioned safely on the UI thread.
        self.messages.put(("move_by_wheel", delta))
        return True

    def _move_overlay(self, delta: int) -> None:
        if self.settings["locked"] or self.confirmed_bar is None or self.bar_rect is None:
            return

        accumulated = self.wheel_delta_remainder + delta
        notches = int(accumulated / 120)
        self.wheel_delta_remainder = accumulated - notches * 120
        if not notches:
            return

        parent_hwnd, left, top, width, _height = self.confirmed_bar
        max_x = max(0, width - WIDGET_WIDTH)
        x = max(0, min(max_x, self.layered.local_position[0] + notches * 24))
        y = self.layered.local_position[1]
        try:
            self.layered.attach_to_finder(parent_hwnd, x, y, left, top)
        except Exception as exc:
            log_message(f"Could not move quota overlay with Alt+wheel: {exc!r}")
            return

        self.settings["position_ratio"] = x / max(1, max_x)
        save_settings(self.settings)

    def _update_text_color(self) -> bool:
        """Choose readable text from the MyDockFinder pixels behind this transparent window."""
        if os.name != "nt":
            return False
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.GetDC.argtypes = [ctypes.wintypes.HWND]
        user32.GetDC.restype = ctypes.wintypes.HDC
        user32.ReleaseDC.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HDC]
        user32.ReleaseDC.restype = ctypes.c_int
        gdi32.GetPixel.argtypes = [
            ctypes.wintypes.HDC,
            ctypes.c_int,
            ctypes.c_int,
        ]
        gdi32.GetPixel.restype = ctypes.c_uint32

        x, y = self.layered.screen_origin
        hdc = user32.GetDC(0)
        if not hdc:
            return False
        luminances = []
        try:
            for sample_x in (x + 2, x + WIDGET_WIDTH - 3):
                for sample_y in (y + 3, y + WIDGET_HEIGHT // 2, y + WIDGET_HEIGHT - 4):
                    pixel = gdi32.GetPixel(hdc, sample_x, sample_y)
                    if pixel == 0xFFFFFFFF:
                        continue
                    red = pixel & 0xFF
                    green = (pixel >> 8) & 0xFF
                    blue = (pixel >> 16) & 0xFF
                    luminances.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        finally:
            user32.ReleaseDC(0, hdc)

        if not luminances:
            return False
        average = sum(luminances) / len(luminances)
        if not self.has_color_sampled:
            self.has_color_sampled = True
            target = (21, 21, 21) if average >= 128 else (255, 255, 255)
            self.target_text_rgb = target
            self.text_rgb = target
            return True

        # Decide from this sample directly. A small dead band keeps the color
        # stable around mid-gray without waiting for a smoothed value to catch up.
        if self.target_text_rgb == (255, 255, 255):
            target = (21, 21, 21) if average >= 128 else self.target_text_rgb
        else:
            target = (255, 255, 255) if average <= 112 else self.target_text_rgb
        if target != self.target_text_rgb:
            self.target_text_rgb = target
            self.color_animation_from = self.text_rgb
            self.color_animation_started = time.monotonic()
            self.color_animation_duration = 0.10 if target == (21, 21, 21) else 0.24
            if self.color_animation_id is None:
                self.color_animation_id = self.root.after(16, self._animate_text_color)
        return False

    def _poll_text_color(self) -> None:
        if self.is_visible and self._update_text_color():
            self._render_layered()
        self.root.after(50, self._poll_text_color)

    def _animate_text_color(self) -> None:
        self.color_animation_id = None
        progress = min(
            1.0,
            (time.monotonic() - self.color_animation_started)
            / self.color_animation_duration,
        )
        eased = progress * progress * (3.0 - 2.0 * progress)
        self.text_rgb = tuple(
            round(start + (target - start) * eased)
            for start, target in zip(self.color_animation_from, self.target_text_rgb)
        )
        self._render_layered()
        if progress < 1.0:
            self.color_animation_id = self.root.after(16, self._animate_text_color)

    def _render_layered(self) -> None:
        scale = 3
        image = Image.new(
            "RGBA", (WIDGET_WIDTH * scale, WIDGET_HEIGHT * scale), (0, 0, 0, 0)
        )
        draw = ImageDraw.Draw(image)
        draw.text(
            (WIDGET_WIDTH * scale / 2, 8.5 * scale),
            self.five_value,
            font=self.font,
            fill=self.text_rgb,
            anchor="mm",
        )
        draw.text(
            (WIDGET_WIDTH * scale / 2, 21.5 * scale),
            self.week_value,
            font=self.font,
            fill=self.text_rgb,
            anchor="mm",
        )
        image = image.resize((WIDGET_WIDTH, WIDGET_HEIGHT), Image.Resampling.LANCZOS)
        pixels = bytearray(image.tobytes("raw", "BGRA"))
        for offset in range(0, len(pixels), 4):
            alpha = pixels[offset + 3]
            pixels[offset] = (pixels[offset] * alpha + 127) // 255
            pixels[offset + 1] = (pixels[offset + 1] * alpha + 127) // 255
            pixels[offset + 2] = (pixels[offset + 2] * alpha + 127) // 255
        try:
            self.layered.update(pixels)
        except Exception as exc:
            log_message(f"Layered text rendering failed: {exc!r}")

    def _follow_bar(self) -> None:
        try:
            detected_bar = find_mydock_bar()
        except Exception as exc:
            log_message(f"MyDockFinder detection failed: {exc!r}")
            detected_bar = None

        # Ignore one-off geometry changes and missed enumerations. MyFinder can
        # briefly report an intermediate rect while opening menus/animating;
        # immediately following that rect made the label flash below the bar.
        if detected_bar is None:
            self.missing_bar_count += 1
            self.pending_bar = None
            self.pending_bar_count = 0
            if self.missing_bar_count >= 10:
                self.confirmed_bar = None
                self.bar_rect = None
                if self.is_visible:
                    log_message(
                        "Hiding quota overlay after MyDockFinder was not detected for 10 checks."
                    )
                    self.layered.hide()
                    self.is_visible = False
            self.root.after(500, self._follow_bar)
            return

        self.missing_bar_count = 0
        if detected_bar == self.confirmed_bar:
            stable_bar = self.confirmed_bar
            self.pending_bar = None
            self.pending_bar_count = 0
        else:
            if detected_bar == self.pending_bar:
                self.pending_bar_count += 1
            else:
                self.pending_bar = detected_bar
                self.pending_bar_count = 1
            if self.pending_bar_count < 2:
                self.root.after(300, self._follow_bar)
                return
            stable_bar = detected_bar
            self.confirmed_bar = stable_bar
            self.pending_bar = None
            self.pending_bar_count = 0

        parent_hwnd, left, top, width, height = stable_bar
        self.bar_rect = (0, 0, width, height)
        if self.drag_origin is None:
            x = round((width - WIDGET_WIDTH) * self.settings["position_ratio"])
            y = max(0, (height - WIDGET_HEIGHT) // 2)
        else:
            x, y = self.layered.local_position

        try:
            self.layered.attach_to_finder(parent_hwnd, x, y, left, top)
        except Exception as exc:
            log_message(f"Could not position quota overlay at MyDockFinder: {exc!r}")
            if self.is_visible:
                self.layered.hide()
                self.is_visible = False
            self.root.after(500, self._follow_bar)
            return

        appeared = not self.is_visible
        if appeared:
            self._update_text_color()
            self._render_layered()
            self.layered.show()
            self.is_visible = True
        self.root.after(300, self._follow_bar)

    def _native_window_message(self, hwnd, message, wparam, _lparam):
        if message not in (0x0201, 0x0200, 0x0202, 0x0205):
            return None
        point = _Point()
        if not self.layered.user32.GetCursorPos(ctypes.byref(point)):
            return None
        event = type("NativeMouseEvent", (), {})()
        event.x_root = point.x
        event.y_root = point.y
        if message == 0x0201:  # WM_LBUTTONDOWN
            self.layered.user32.SetCapture(hwnd)
            self._drag_start(event)
            return 0
        if message == 0x0200 and (wparam & 0x0001):  # WM_MOUSEMOVE + MK_LBUTTON
            self._drag_motion(event)
            return 0
        if message == 0x0202:  # WM_LBUTTONUP
            self.layered.user32.ReleaseCapture()
            self._drag_end(event)
            return 0
        if message == 0x0205:  # WM_RBUTTONUP
            self._show_context(event)
            return 0
        return None

    def _drag_start(self, event) -> None:
        if self.settings["locked"] or self.bar_rect is None:
            return
        self.drag_origin = (
            event.x_root,
            event.y_root,
            self.layered.local_position[0],
            self.layered.local_position[1],
        )

    def _drag_motion(self, event) -> None:
        if self.drag_origin is None or self.bar_rect is None:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        x = window_x + event.x_root - start_x
        y = window_y + event.y_root - start_y
        _left, _top, width, height = self.bar_rect
        x = max(0, min(width - WIDGET_WIDTH, x))
        y = max(0, min(height - WIDGET_HEIGHT, y))
        try:
            self.layered.attach_to_finder(
                self.layered.parent_hwnd,
                x,
                y,
                self.layered.host_origin[0],
                self.layered.host_origin[1],
            )
        except Exception as exc:
            log_message(f"Could not move quota overlay: {exc!r}")
            return
        self._render_layered()

    def _drag_end(self, _event) -> None:
        if self.drag_origin and self.bar_rect:
            width = self.bar_rect[2]
            ratio = self.layered.local_position[0] / max(1, width - WIDGET_WIDTH)
            self.settings["position_ratio"] = min(1.0, max(0.0, ratio))
            save_settings(self.settings)
        self.drag_origin = None

    def _show_context(self, event) -> None:
        try:
            self.context.tk_popup(event.x_root, event.y_root)
        finally:
            self.context.grab_release()

    def _toggle_lock(self) -> None:
        self.settings["locked"] = bool(self.lock_var.get())
        save_settings(self.settings)

    def _show_tooltip(self, _event) -> None:
        self.root.title(
            f"Codex 额度 · {self.last_success}"
            + (f" · {self.last_error}" if self.last_error else "")
        )

    def _hide_tooltip(self, _event) -> None:
        self.root.title("Codex Quota Bar")

    def _request_refresh(self) -> None:
        self.refresh_event.set()

    def _poll_loop(self) -> None:
        server = None
        while not self.stop_event.is_set():
            try:
                if server is None or server.process.poll() is not None:
                    executable = find_codex_executable()
                    if not executable:
                        raise RuntimeError("找不到 Codex 程序，请先安装 Codex 桌面版或 CLI。")
                    server = CodexAppServer(executable)
                five_hour, week = server.read_quota()
                self.messages.put(("quota", (five_hour, week)))
            except Exception as exc:
                log_message(f"Codex quota refresh failed: {exc!r}")
                self.messages.put(("error", str(exc)))
                if server is not None:
                    server.close()
                    server = None

            for _ in range(POLL_SECONDS):
                if self.stop_event.wait(1):
                    break
                if self.refresh_event.is_set():
                    self.refresh_event.clear()
                    break

        if server is not None:
            server.close()

    def _process_messages(self) -> None:
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "quota":
                    five_hour, week = value
                    self.five_value = "5h: N/A" if five_hour is None else f"5h: {five_hour}%"
                    self.week_value = "Week: N/A" if week is None else f"Week: {week}%"
                    self.last_success = time.strftime("%H:%M 更新")
                    self.last_error = ""
                    self.context.entryconfigure(0, label=f"状态：{self.last_success}")
                    self._render_layered()
                elif kind == "error":
                    self.last_error = value
                    summary = value if len(value) <= 72 else value[:69] + "..."
                    self.context.entryconfigure(0, label=f"状态：{summary}")
                    if self.last_success == "等待首次同步":
                        self.five_value = "5h: --%"
                        self.week_value = "Week: --%"
                        self._render_layered()
                elif kind == "move_by_wheel":
                    self._move_overlay(value)
        except queue.Empty:
            pass
        self.root.after(250, self._process_messages)

    def close(self) -> None:
        global _ACTIVE_BAR
        if self.is_closing:
            return
        self.is_closing = True
        log_message(f"{APP_NAME} {APP_VERSION} closing.")
        self.stop_event.set()
        if self.mouse_hook:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
            user32.UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL
            user32.UnhookWindowsHookEx(self.mouse_hook)
            self.mouse_hook = None
            self.mouse_hook_callback = None
        self.layered.close()
        _ACTIVE_BAR = None
        self.root.destroy()

    def run(self) -> None:
        self.root.withdraw()
        self.root.mainloop()


def main() -> None:
    if not acquire_single_instance():
        return
    try:
        QuotaBar().run()
    except Exception as exc:
        log_message(f"Fatal application error:\n{traceback.format_exc()}")
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror("Codex Quota Bar", str(exc))
        except Exception:
            pass


if __name__ == "__main__":
    main()
