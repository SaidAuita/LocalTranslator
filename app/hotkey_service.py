import time
import threading
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication
from pynput import keyboard
from pynput.keyboard import Controller, Key

# Win32 Constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# Configure Win32 prototypes once for 64-bit and 32-bit safety
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]

user32.CloseClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []

user32.EmptyClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []

user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]

user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]

kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]


def pynput_to_qt(pynput_str: str) -> str:
    """Convert pynput hotkey format (e.g. '<ctrl>+<shift>+q') to Qt string ('Ctrl+Shift+Q')."""
    if not pynput_str:
        return ""
    parts = pynput_str.split("+")
    qt_parts = []
    mod_map = {
        "<ctrl>": "Ctrl",
        "<shift>": "Shift",
        "<alt>": "Alt",
        "<cmd>": "Meta",
        "<space>": "Space",
        "<enter>": "Enter",
        "<tab>": "Tab",
        "<esc>": "Esc",
    }
    for p in parts:
        p_clean = p.strip()
        p_lower = p_clean.lower()
        if p_lower in mod_map:
            qt_parts.append(mod_map[p_lower])
        elif p_lower.startswith("<f") and p_lower.endswith(">") and p_lower[2:-1].isdigit():
            qt_parts.append(p_lower[1:-1].upper())
        else:
            qt_parts.append(p_clean.strip("<>").upper())
    return "+".join(qt_parts)


def qt_to_pynput(qt_str: str) -> str:
    """Convert Qt key sequence string (e.g. 'Ctrl+Shift+Q') to pynput string ('<ctrl>+<shift>+q')."""
    if not qt_str:
        return ""
    parts = qt_str.split("+")
    pynput_parts = []
    mod_map = {
        "ctrl": "<ctrl>",
        "control": "<ctrl>",
        "shift": "<shift>",
        "alt": "<alt>",
        "meta": "<cmd>",
        "cmd": "<cmd>",
        "win": "<cmd>",
    }
    for p in parts:
        p_clean = p.strip().lower()
        if not p_clean:
            continue
        if p_clean in mod_map:
            pynput_parts.append(mod_map[p_clean])
        elif p_clean.startswith("f") and p_clean[1:].isdigit():
            pynput_parts.append(f"<{p_clean}>")
        elif p_clean == "space":
            pynput_parts.append("<space>")
        elif p_clean in ("enter", "return"):
            pynput_parts.append("<enter>")
        elif p_clean == "tab":
            pynput_parts.append("<tab>")
        elif p_clean in ("esc", "escape"):
            pynput_parts.append("<esc>")
        else:
            pynput_parts.append(p_clean)
    return "+".join(pynput_parts)


def get_clipboard_text() -> str:
    """Read plain text from Windows clipboard safely."""
    # 1. Try Qt Clipboard if called on the GUI thread
    try:
        app = QApplication.instance()
        if app and QThread.currentThread() == app.thread():
            cb = app.clipboard()
            if cb:
                text = cb.text()
                if text:
                    return text
    except Exception:
        pass

    # 2. Native Win32 API with retry loop
    try:
        opened = False
        for _ in range(10):
            if user32.OpenClipboard(None):
                opened = True
                break
            time.sleep(0.02)

        if not opened:
            return ""

        try:
            if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return ""
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            text = ctypes.c_wchar_p(ptr).value or ""
            kernel32.GlobalUnlock(handle)
            return text
        finally:
            user32.CloseClipboard()
    except Exception as e:
        print(f"[Hotkey] Clipboard get error: {e}")
        return ""


def set_clipboard_text(text: str) -> bool:
    """Set plain text into Windows clipboard safely and reliably."""
    if text is None:
        text = ""

    # 1. Try Qt Clipboard if called on the GUI thread
    try:
        app = QApplication.instance()
        if app and QThread.currentThread() == app.thread():
            cb = app.clipboard()
            if cb:
                cb.setText(text)
                return True
    except Exception:
        pass

    # 2. Native Win32 API with proper 64-bit memory management and retry loop
    try:
        encoded = text.encode("utf-16le") + b"\x00\x00"
        opened = False
        for _ in range(10):
            if user32.OpenClipboard(None):
                opened = True
                break
            time.sleep(0.02)

        if opened:
            try:
                user32.EmptyClipboard()
                handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if handle:
                    ptr = kernel32.GlobalLock(handle)
                    if ptr:
                        ctypes.memmove(ptr, encoded, len(encoded))
                        kernel32.GlobalUnlock(handle)
                        user32.SetClipboardData(CF_UNICODETEXT, handle)
                        return True
            finally:
                user32.CloseClipboard()
    except Exception as e:
        print(f"[Hotkey] Clipboard set error: {e}")

    return False


class HotkeyService(QObject):
    # Signals sent to Qt Main Thread
    translate_requested = pyqtSignal(str)  # text to translate in popup
    replace_requested = pyqtSignal(str)    # text to translate & replace
    ocr_requested = pyqtSignal()           # trigger screen snippet OCR

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keyboard_controller = Controller()
        self.listener: keyboard.GlobalHotKeys = None
        self.is_running = False

    def start(
        self,
        hotkey_translate="<ctrl>+q",
        hotkey_replace="<ctrl>+<shift>+q",
        hotkey_ocr="<ctrl>+<shift>+s"
    ):
        if self.is_running:
            self.stop()

        hotkeys_dict = {}

        if hotkey_translate:
            try:
                keyboard.HotKey.parse(hotkey_translate)
                hotkeys_dict[hotkey_translate] = self._on_hotkey_translate
            except Exception as e:
                print(f"[Hotkey] Некорректная комбинация для перевода '{hotkey_translate}': {e}")

        if hotkey_replace:
            try:
                keyboard.HotKey.parse(hotkey_replace)
                hotkeys_dict[hotkey_replace] = self._on_hotkey_replace
            except Exception as e:
                print(f"[Hotkey] Некорректная комбинация для замены '{hotkey_replace}': {e}")

        if hotkey_ocr:
            try:
                keyboard.HotKey.parse(hotkey_ocr)
                hotkeys_dict[hotkey_ocr] = self._on_hotkey_ocr
            except Exception as e:
                print(f"[Hotkey] Некорректная комбинация для OCR '{hotkey_ocr}': {e}")

        if not hotkeys_dict:
            print("[Hotkey] Нет активных горячих клавиш для регистрации.")
            return

        try:
            self.listener = keyboard.GlobalHotKeys(hotkeys_dict)
            self.listener.daemon = True
            self.listener.start()
            self.is_running = True
            print(f"[Hotkey] Зарегистрированы глобальные хоткеи: {list(hotkeys_dict.keys())}")
        except Exception as e:
            print(f"[Hotkey] Ошибка регистрации хоткеев: {e}")

    def update_hotkeys(
        self,
        enabled: bool = True,
        hotkey_translate: str = "<ctrl>+q",
        hotkey_replace: str = "<ctrl>+<shift>+q",
        hotkey_ocr: str = "<ctrl>+<shift>+s"
    ):
        """Update hotkey configuration at runtime without application restart."""
        self.stop()
        if enabled:
            self.start(hotkey_translate, hotkey_replace, hotkey_ocr)
        else:
            print("[Hotkey] Глобальные хоткеи отключены.")

    def _on_hotkey_ocr(self):
        self.ocr_requested.emit()

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
        self.is_running = False

    def _copy_selection(self) -> str:
        """Simulate Ctrl+C and read grabbed text from clipboard."""
        old_clipboard = get_clipboard_text()

        # Release any stuck modifiers and press Ctrl+C
        time.sleep(0.05)
        self.keyboard_controller.press(Key.ctrl)
        self.keyboard_controller.press('c')
        time.sleep(0.02)
        self.keyboard_controller.release('c')
        self.keyboard_controller.release(Key.ctrl)

        # Wait up to 300ms for clipboard to update
        new_text = ""
        for _ in range(15):
            time.sleep(0.02)
            cur = get_clipboard_text()
            if cur and cur != old_clipboard:
                new_text = cur
                break
            elif cur:
                new_text = cur

        return new_text.strip()

    def _on_hotkey_translate(self):
        threading.Thread(target=self._worker_translate, daemon=True).start()

    def _worker_translate(self):
        text = self._copy_selection()
        if text:
            self.translate_requested.emit(text)

    def _on_hotkey_replace(self):
        threading.Thread(target=self._worker_replace, daemon=True).start()

    def _worker_replace(self):
        text = self._copy_selection()
        if text:
            self.replace_requested.emit(text)

    def paste_text(self, text: str):
        """Put text to clipboard and simulate Ctrl+V."""
        if not text:
            return
        set_clipboard_text(text)
        time.sleep(0.05)
        self.keyboard_controller.press(Key.ctrl)
        self.keyboard_controller.press('v')
        time.sleep(0.02)
        self.keyboard_controller.release('v')
        self.keyboard_controller.release(Key.ctrl)
