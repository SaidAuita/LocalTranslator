import sys
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtGui import QColor, QFont, QCursor, QKeySequence, QShortcut
from app.config import config, LANGUAGES
from app.languages_data import ALL_CANONICAL_LANGS, get_sorted_languages
from app.translator_nllb import nllb_translator
from app.translator_lmstudio import lmstudio_translator
from app.hotkey_service import set_clipboard_text


class PopupTranslateWorker(QThread):
    finished = pyqtSignal(str, float, str, str)  # translated_text, latency_ms, engine_name, error

    def __init__(self, text: str, src_lang: str, tgt_lang: str, engine: str):
        super().__init__()
        self.text = text
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.engine = engine

    def run(self):
        try:
            if self.engine == "lmstudio":
                res, lat, model = lmstudio_translator.translate(self.text, self.src_lang, self.tgt_lang)
                self.finished.emit(res, lat, f"LM Studio ({model})", "")
            else:  # nllb
                res, lat = nllb_translator.translate(self.text, self.src_lang, self.tgt_lang)
                dev_str = f"NLLB 1.3B ({nllb_translator.device.upper()})"
                self.finished.emit(res, lat, dev_str, "")
        except Exception as e:
            self.finished.emit("", 0.0, "", str(e))


class FloatingPopup(QWidget):
    open_main_requested = pyqtSignal()
    replace_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

        self.original_text = ""
        self.translated_text = ""
        self.worker: PopupTranslateWorker = None
        self._drag_pos = QPoint()

        self.init_ui()
        self.init_shortcuts()

    def init_ui(self):
        self.setFixedSize(460, 320)

        # Outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Container card
        self.card = QWidget(self)
        self.card.setObjectName("popupCard")
        self.card.setStyleSheet("""
            #popupCard {
                background-color: #1a1c23;
                border: 1px solid #2d313e;
                border-radius: 12px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(8)

        title_lbl = QLabel("🌐 Быстрый перевод", self)
        title_lbl.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 12px;")
        header.addWidget(title_lbl)

        header.addStretch()

        # Engine pill
        self.engine_pill = QLabel("NLLB 1.3B", self)
        self.engine_pill.setStyleSheet("""
            background-color: #1e293b;
            color: #38bdf8;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid #0284c7;
        """)
        header.addWidget(self.engine_pill)

        # Target language combo
        self.lang_combo = QComboBox(self)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #242936;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #e2e8f0;
                selection-background-color: #3b82f6;
            }
        """)
        ui_lang = config.get("ui_language", "en")
        auto_label = "⚡ Автовыбор [auto]" if ui_lang == "ru" else "⚡ Auto Pair [auto]"
        self.lang_combo.addItem(auto_label, "auto")
        for item in get_sorted_languages(locale=ui_lang):
            disp_name = item["name"] if ui_lang == "ru" else item["en_name"]
            code_tag = f" [{item['code']}]" if item.get('code') else ""
            self.lang_combo.addItem(f"{disp_name}{code_tag}", item["key"])
        self.lang_combo.setCurrentIndex(0)  # Auto
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        header.addWidget(self.lang_combo)

        # Expand button
        expand_btn = QPushButton("↗", self)
        expand_btn.setFixedSize(24, 24)
        expand_btn.setToolTip("Открыть основное окно")
        expand_btn.setStyleSheet("""
            QPushButton {
                background-color: #242936;
                color: #94a3b8;
                border-radius: 6px;
                border: 1px solid #334155;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        expand_btn.clicked.connect(self.open_main)
        header.addWidget(expand_btn)

        # Close button
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        card_layout.addLayout(header)

        # Original snippet label
        self.orig_lbl = QLabel(self)
        self.orig_lbl.setStyleSheet("color: #64748b; font-size: 11px; padding: 2px 4px; font-style: italic;")
        self.orig_lbl.setWordWrap(True)
        self.orig_lbl.setMaximumHeight(36)
        card_layout.addWidget(self.orig_lbl)

        # Translation Text Area
        self.trans_text = QTextEdit(self)
        self.trans_text.setReadOnly(True)
        self.trans_text.setStyleSheet("""
            QTextEdit {
                background-color: #12141a;
                color: #f1f5f9;
                border: 1px solid #282d3b;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        card_layout.addWidget(self.trans_text)

        # Bottom Bar
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        # Latency label
        self.latency_lbl = QLabel("", self)
        self.latency_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        bottom.addWidget(self.latency_lbl)

        bottom.addStretch()

        # Replace button
        self.replace_btn = QPushButton("Вставить (Заменить)", self)
        self.replace_btn.setStyleSheet("""
            QPushButton {
                background-color: #242936;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        self.replace_btn.clicked.connect(self.replace_original)
        bottom.addWidget(self.replace_btn)

        # Copy button
        self.copy_btn = QPushButton("Копировать (Enter)", self)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_translation)
        bottom.addWidget(self.copy_btn)

        card_layout.addLayout(bottom)
        outer_layout.addWidget(self.card)

    def init_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.hide)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self.copy_translation)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self.copy_translation)

    def show_at_cursor(self, text: str):
        self.original_text = text
        snippet = text[:90] + ("..." if len(text) > 90 else "")
        self.orig_lbl.setText(f"Исходный: {snippet}")
        self.trans_text.setPlainText("⏳ Перевод...")
        self.latency_lbl.setText("")

        # Position near mouse cursor, preventing overflow off screen
        cursor_pos = QCursor.pos()
        screen_geom = QApplication.primaryScreen().geometry()
        x = min(max(10, cursor_pos.x() + 15), screen_geom.width() - self.width() - 10)
        y = min(max(10, cursor_pos.y() + 15), screen_geom.height() - self.height() - 10)
        self.move(x, y)

        self.show()
        self.raise_()
        self.activateWindow()

        self.start_translation()

    def start_translation(self):
        engine = config.get("engine", "nllb")
        if engine == "compare":
            engine = "nllb"  # popup displays primary engine for speed

        tgt_code = self.lang_combo.currentData() or "auto"
        src_code = config.get("source_lang", "auto")

        self.engine_pill.setText("LM Studio" if engine == "lmstudio" else "NLLB 1.3B")

        if self.worker and self.worker.isRunning():
            self.worker.terminate()

        self.worker = PopupTranslateWorker(self.original_text, src_code, tgt_code, engine)
        self.worker.finished.connect(self.on_translated)
        self.worker.start()

    def on_translated(self, res: str, lat: float, engine_str: str, err: str):
        if err:
            self.trans_text.setPlainText(f"❌ Ошибка перевода:\n{err}")
            self.latency_lbl.setText("")
        else:
            self.translated_text = res
            self.trans_text.setPlainText(res)
            self.latency_lbl.setText(f"⚡ {lat:.0f} ms")
            if engine_str:
                self.engine_pill.setText(engine_str.split("(")[0].strip())

    def on_lang_changed(self):
        if self.original_text:
            self.start_translation()

    def copy_translation(self):
        if self.translated_text:
            set_clipboard_text(self.translated_text)
            self.copy_btn.setText("Скопировано! ✓")
            if config.get("close_popup_on_copy", True):
                self.hide()

    def replace_original(self):
        if self.translated_text:
            self.replace_requested.emit(self.translated_text)
            self.hide()

    def open_main(self):
        self.hide()
        self.open_main_requested.emit()

    # Window drag support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
