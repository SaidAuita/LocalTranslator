import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from app.config import config
from app.i18n import tr
from app.ui_main import MainWindow
from app.ui_popup import FloatingPopup
from app.ui_tray import SystemTrayService, create_tray_pixmap
from app.hotkey_service import HotkeyService
from app.translator_nllb import nllb_translator
from app.translator_lmstudio import lmstudio_translator


class ApplicationManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.app.setQuitOnLastWindowClosed(False)

        # 1. Main Window
        self.main_window = MainWindow()

        # 2. Floating Popup (QTranslate style)
        self.popup = FloatingPopup()

        # 3. Tray Service
        self.tray = SystemTrayService()
        self.tray.show()

        # 4. Global Hotkey Service
        self.hotkey_service = HotkeyService()

        # Connect Signals
        self.connect_signals()

        # Start Hotkeys
        hk_trans = config.get("hotkey_translate", "<ctrl>+q")
        hk_repl = config.get("hotkey_replace", "<ctrl>+<shift>+q")
        hk_ocr = config.get("hotkey_ocr", "<ctrl>+<shift>+s")
        self.hotkey_service.start(hk_trans, hk_repl, hk_ocr)

        # Show main window if not starting minimized or requested via args
        start_minimized = "--minimized" in sys.argv or "--tray" in sys.argv or config.get("start_minimized", False)
        if not start_minimized:
            self.main_window.show()

    def connect_signals(self):
        # Hotkey -> Popup & OCR
        self.hotkey_service.translate_requested.connect(self.on_hotkey_translate)
        self.hotkey_service.replace_requested.connect(self.on_hotkey_replace)
        self.hotkey_service.ocr_requested.connect(self.main_window.start_screen_ocr)

        # Popup -> Main Window
        self.popup.open_main_requested.connect(self.on_popup_open_main)
        self.popup.replace_requested.connect(self.hotkey_service.paste_text)

        # Main Window -> Tray
        self.main_window.ui_language_changed.connect(self.tray.retranslate)

        # Tray -> Actions
        self.tray.show_main_requested.connect(self.show_main)
        self.tray.ocr_requested.connect(self.main_window.start_screen_ocr)
        self.tray.open_settings_requested.connect(self.main_window.open_settings)
        self.tray.clear_cache_requested.connect(self.on_clear_cache)
        self.tray.exit_requested.connect(self.exit_app)

    def on_clear_cache(self):
        lmstudio_translator.clear_cache()
        nllb_translator.clear_cache()
        self.tray.notify("Local Translator", tr("tray_cache_cleared"))

    def on_hotkey_translate(self, text: str):
        self.popup.show_at_cursor(text)

    def on_hotkey_replace(self, text: str):
        # Translate and replace in place
        engine = config.get("engine", "nllb")
        try:
            if engine == "lmstudio":
                res, _, _ = lmstudio_translator.translate(text)
            else:
                res, _ = nllb_translator.translate(text)
            if res:
                self.hotkey_service.paste_text(res)
        except Exception as e:
            print(f"[Replace Error] {e}")

    def on_popup_open_main(self):
        text = self.popup.original_text
        self.main_window.showNormal()
        self.main_window.activateWindow()
        if text:
            self.main_window.set_source_text(text)

    def show_main(self):
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
        else:
            self.main_window.showNormal()
            self.main_window.activateWindow()

    def exit_app(self):
        self.hotkey_service.stop()
        self.app.quit()


_instance_mutex = None


def check_single_instance() -> bool:
    """Ensure only one instance of Local Translator runs at a time."""
    global _instance_mutex
    import ctypes
    mutex_name = "LocalTranslator_Global_Mutex_Instance_Unique"
    _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        return False
    return True


def main():
    if not check_single_instance():
        print("[Local Translator] Приложение уже запущено. Вторая копия не будет открыта.")
        sys.exit(0)

    # Windows high-DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName("Local Translator")
    app.setWindowIcon(QIcon(create_tray_pixmap()))

    manager = ApplicationManager(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

