from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import pyqtSignal


def create_tray_pixmap() -> QPixmap:
    """Generate a clean dark-mode tray icon with 'T' symbol."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Blue rounded square
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(QColor(59, 130, 246))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    # White 'T' text
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 32, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "T")  # AlignCenter
    painter.end()

    return pixmap


from app.i18n import tr


class SystemTrayService(QSystemTrayIcon):
    show_main_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    ocr_requested = pyqtSignal()
    clear_cache_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(create_tray_pixmap()))
        self.setToolTip("Local Translator (NLLB 1.3B & LM Studio)")

        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1e212b;
                color: #e2e8f0;
                border: 1px solid #333a4d;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
        """)

        self.open_action = self.menu.addAction("")
        self.open_action.triggered.connect(self.show_main_requested.emit)

        self.ocr_action = self.menu.addAction("")
        self.ocr_action.triggered.connect(self.ocr_requested.emit)

        self.menu.addSeparator()

        self.settings_action = self.menu.addAction("")
        self.settings_action.triggered.connect(self.open_settings_requested.emit)

        self.clear_action = self.menu.addAction("")
        self.clear_action.triggered.connect(self.clear_cache_requested.emit)

        self.menu.addSeparator()

        self.exit_action = self.menu.addAction("")
        self.exit_action.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(self.menu)
        self.activated.connect(self.on_activated)
        self.retranslate()

    def retranslate(self):
        self.open_action.setText(f"🌐 {tr('tray_open')}")
        self.ocr_action.setText(f"📷 {tr('tray_ocr')}")
        self.settings_action.setText(f"⚙ {tr('tray_settings')}")
        self.clear_action.setText(f"🧹 {tr('tray_clear_cache')}")
        self.exit_action.setText(f"❌ {tr('tray_exit')}")

    def on_activated(self, reason):
        # Single click or double click on tray icon toggles the main window
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_main_requested.emit()

    def notify(self, title: str, message: str, msec: int = 2500):
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, msec)

