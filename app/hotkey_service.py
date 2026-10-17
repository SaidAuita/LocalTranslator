import time
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard
from pynput.keyboard import Controller, Key
try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def get_clipboard_text() -> str:
    """Read plain text from Windows clipboard safely."""
    if HAS_WIN32:
        for _ in range(5):
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    return text or ""
                win32clipboard.CloseClipboard()
                return ""
            except Exception:
                time.sleep(0.02)
    # Fallback to tkinter or standard ctypes
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return ""
        CF_UNICODETEXT = 13
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            user32.CloseClipboard()
            return ""
        ptr = kernel32.GlobalLock(handle)
        text = ctypes.c_wchar_p(ptr).value or ""
        kernel32.GlobalUnlock(handle)
        user32.CloseClipboard()
        return text
    except Exception:
        return ""


def set_clipboard_text(text: str) -> None:
    """Set plain text into Windows clipboard safely."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return
        user32.EmptyClipboard()
        CF_UNICODETEXT = 13
        encoded = text.encode('utf-16le') + b'\x00\x00'
        handle = kernel32.GlobalAlloc(0x0002, len(encoded))  # GMEM_MOVEABLE
        ptr = kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        user32.SetClipboardData(CF_UNICODETEXT, handle)
        user32.CloseClipboard()
    except Exception as e:
        print(f"[Hotkey] Clipboard error: {e}")


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

        hotkeys_dict = {
            hotkey_translate: self._on_hotkey_translate,
            hotkey_replace: self._on_hotkey_replace,
            hotkey_ocr: self._on_hotkey_ocr
        }

        try:
            self.listener = keyboard.GlobalHotKeys(hotkeys_dict)
            self.listener.daemon = True
            self.listener.start()
            self.is_running = True
            print(f"[Hotkey] Зарегистрированы глобальные хоткеи: {hotkey_translate} (Popup), {hotkey_replace} (Replace), {hotkey_ocr} (OCR Snippet)")
        except Exception as e:
            print(f"[Hotkey] Ошибка регистрации хоткеев: {e}")

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

        # Wait up to 150ms for clipboard to update
        new_text = ""
        for _ in range(10):
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
        set_clipboard_text(text)
        time.sleep(0.05)
        self.keyboard_controller.press(Key.ctrl)
        self.keyboard_controller.press('v')
        time.sleep(0.02)
        self.keyboard_controller.release('v')
        self.keyboard_controller.release(Key.ctrl)
