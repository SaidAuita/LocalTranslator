import os
import sys
import time
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QEvent, QObject
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QSplitter, QFrame, QDialog, QProgressBar,
    QMessageBox, QLineEdit, QCheckBox, QTabWidget, QGroupBox, QStatusBar,
    QCompleter, QSizePolicy, QScrollArea
)
from PyQt6.QtGui import QFont, QIcon, QColor, QKeySequence, QShortcut
from app.config import config, LANGUAGES, is_port_listening
from app.languages_data import (
    ALL_CANONICAL_LANGS, get_language_info, get_display_name,
    get_nllb_code, get_sorted_languages
)
from app.i18n import tr, UI_LANGUAGES
from app.translator_nllb import nllb_translator
from app.translator_lmstudio import lmstudio_translator
from app.model_downloader import ModelDownloader
from app.hotkey_service import set_clipboard_text, get_clipboard_text
from app.ui_snippet import ScreenSnipper, pixmap_to_base64


# --- Worker Threads ---

class DownloadWorker(QThread):
    progress = pyqtSignal(int, int, float, float, str)
    completed = pyqtSignal(bool, str)

    def __init__(self, target_dir=None, proxy=None):
        super().__init__()
        self.downloader = ModelDownloader(target_dir, proxy)

    def run(self):
        try:
            success = self.downloader.download_all(self._on_progress)
            self.completed.emit(success, "" if success else "Загрузка была отменена.")
        except Exception as e:
            self.completed.emit(False, str(e))

    def _on_progress(self, cur, total, speed, eta, status):
        self.progress.emit(cur, total, speed, eta, status)

    def cancel(self):
        self.downloader.cancel()


class NllbWorker(QThread):
    finished = pyqtSignal(int, str, float, str)  # req_id, text, lat, error

    def __init__(self, req_id: int, text: str, src: str, tgt: str):
        super().__init__()
        self.req_id = req_id
        self.text = text
        self.src = src
        self.tgt = tgt

    def run(self):
        try:
            res, lat = nllb_translator.translate(self.text, self.src, self.tgt)
            self.finished.emit(self.req_id, res, lat, "")
        except Exception as e:
            self.finished.emit(self.req_id, "", 0.0, str(e))


class LmsWorker(QThread):
    finished = pyqtSignal(int, str, float, str, str)  # req_id, text, lat, model, error

    def __init__(self, req_id: int, text: str, src: str, tgt: str):
        super().__init__()
        self.req_id = req_id
        self.text = text
        self.src = src
        self.tgt = tgt

    def run(self):
        try:
            res, lat, model = lmstudio_translator.translate(self.text, self.src, self.tgt)
            self.finished.emit(self.req_id, res, lat, model, "")
        except Exception as e:
            self.finished.emit(self.req_id, "", 0.0, "", str(e))


class OcrWorker(QThread):
    finished = pyqtSignal(int, str, float, str, str)  # req_id, text, lat, model, error

    def __init__(self, req_id: int, image_base64: str):
        super().__init__()
        self.req_id = req_id
        self.image_base64 = image_base64

    def run(self):
        try:
            res, lat, model = lmstudio_translator.recognize_image(self.image_base64)
            self.finished.emit(self.req_id, res, lat, model, "")
        except Exception as e:
            self.finished.emit(self.req_id, "", 0.0, "", str(e))


# --- Settings Dialog ---

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings_title"))
        self.resize(560, 680)
        self.setMinimumSize(500, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #16181f;
                color: #e2e8f0;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #212530;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3b82f6;
            }
            QGroupBox {
                border: 1px solid #2d3748;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #94a3b8;
                padding-top: 12px;
                padding-bottom: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(16, 16, 16, 16)
        dialog_layout.setSpacing(12)

        # Scroll Area for comfortable viewing on any screen resolution/scaling
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #11131a;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # 1. UI Language Group
        self.lang_group = QGroupBox(tr("settings_ui_lang"), self)
        lang_layout = QHBoxLayout(self.lang_group)
        lang_layout.setContentsMargins(12, 10, 12, 10)
        self.ui_lang_combo = QComboBox(self)
        self.ui_lang_combo.setMinimumHeight(34)
        for code, name in UI_LANGUAGES:
            self.ui_lang_combo.addItem(name, code)
        cur_ui_lang = config.get("ui_language", "en")
        idx = self.ui_lang_combo.findData(cur_ui_lang)
        if idx >= 0:
            self.ui_lang_combo.setCurrentIndex(idx)
        self.ui_lang_combo.currentIndexChanged.connect(self.on_ui_lang_changed)
        lang_layout.addWidget(self.ui_lang_combo)
        layout.addWidget(self.lang_group)

        # 2. LM Studio Group
        self.lms_group = QGroupBox(tr("settings_lms_group"), self)
        lms_layout = QVBoxLayout(self.lms_group)
        lms_layout.setContentsMargins(12, 10, 12, 10)
        lms_layout.setSpacing(8)

        self.lms_url_lbl = QLabel(tr("settings_lms_url"), self)
        lms_layout.addWidget(self.lms_url_lbl)
        self.lms_url = QLineEdit(config.get("lm_studio_url", "http://127.0.0.1:1234/v1"))
        self.lms_url.setMinimumHeight(34)
        lms_layout.addWidget(self.lms_url)

        h_lms = QHBoxLayout()
        h_lms.setSpacing(10)
        self.test_lms_btn = QPushButton(f"🔍 {tr('settings_test_btn')}", self)
        self.test_lms_btn.setMinimumHeight(34)
        self.test_lms_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_lms_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0c4a6e;
                color: #ffffff;
            }
        """)
        self.test_lms_btn.clicked.connect(self.test_lms)
        h_lms.addWidget(self.test_lms_btn)

        self.start_lms_btn = QPushButton(tr("settings_start_lms_btn"), self)
        self.start_lms_btn.setMinimumHeight(34)
        self.start_lms_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_lms_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #10b981;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #064e3b;
                color: #ffffff;
            }
        """)
        self.start_lms_btn.clicked.connect(self.start_lms)
        h_lms.addWidget(self.start_lms_btn)
        lms_layout.addLayout(h_lms)

        self.lms_status_lbl = QLabel("", self)
        self.lms_status_lbl.setWordWrap(True)
        lms_layout.addWidget(self.lms_status_lbl)
        layout.addWidget(self.lms_group)

        # 3. Local Engine Group
        self.nllb_group = QGroupBox(tr("settings_nllb_group"), self)
        nllb_layout = QVBoxLayout(self.nllb_group)
        nllb_layout.setContentsMargins(12, 10, 12, 10)
        nllb_layout.setSpacing(8)

        h_dev = QHBoxLayout()
        self.dev_lbl = QLabel(tr("settings_device"), self)
        h_dev.addWidget(self.dev_lbl)
        self.device_combo = QComboBox(self)
        self.device_combo.setMinimumHeight(34)
        self.device_combo.addItem(tr("settings_dev_auto"), "auto")
        self.device_combo.addItem(tr("settings_dev_cuda"), "cuda")
        self.device_combo.addItem(tr("settings_dev_cpu"), "cpu")
        cur_dev = config.get("device", "auto")
        idx = self.device_combo.findData(cur_dev)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
        h_dev.addWidget(self.device_combo)
        nllb_layout.addLayout(h_dev)

        h_proxy = QHBoxLayout()
        self.proxy_lbl = QLabel(tr("settings_proxy"), self)
        h_proxy.addWidget(self.proxy_lbl)
        self.proxy_edit = QLineEdit(config.get("proxy", "http://127.0.0.1:10808"))
        self.proxy_edit.setMinimumHeight(34)
        h_proxy.addWidget(self.proxy_edit)
        nllb_layout.addLayout(h_proxy)

        layout.addWidget(self.nllb_group)

        # 4. Hotkeys Group
        self.hk_group = QGroupBox(tr("settings_hk_group"), self)
        hk_layout = QVBoxLayout(self.hk_group)
        hk_layout.setContentsMargins(12, 10, 12, 10)
        self.hk_info = QLabel(tr("settings_hk_info"), self)
        self.hk_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hk_layout.addWidget(self.hk_info)
        layout.addWidget(self.hk_group)

        # 5. Tray & Startup Group
        self.tray_group = QGroupBox(tr("settings_tray_group"), self)
        tray_layout = QVBoxLayout(self.tray_group)
        tray_layout.setContentsMargins(12, 10, 12, 10)
        tray_layout.setSpacing(6)
        self.min_to_tray_cb = QCheckBox(tr("settings_min_to_tray"), self)
        self.min_to_tray_cb.setChecked(config.get("minimize_to_tray", True))
        self.min_to_tray_cb.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        tray_layout.addWidget(self.min_to_tray_cb)

        self.start_min_cb = QCheckBox(tr("settings_start_min"), self)
        self.start_min_cb.setChecked(config.get("start_minimized", False))
        self.start_min_cb.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        tray_layout.addWidget(self.start_min_cb)
        layout.addWidget(self.tray_group)

        layout.addStretch()

        scroll.setWidget(scroll_widget)
        dialog_layout.addWidget(scroll, 1)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.cancel_btn = QPushButton(tr("settings_cancel"), self)
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #cbd5e1;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #475569;
                color: #ffffff;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(tr("settings_save"), self)
        self.save_btn.setMinimumHeight(36)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        btns.addWidget(self.save_btn)
        dialog_layout.addLayout(btns)

    def on_ui_lang_changed(self):
        new_lang = self.ui_lang_combo.currentData()
        if new_lang:
            config.set("ui_language", new_lang)
            self.retranslate_ui()
            if self.parent() and hasattr(self.parent(), "retranslate_ui"):
                self.parent().retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(tr("settings_title"))
        self.lang_group.setTitle(tr("settings_ui_lang"))
        self.lms_group.setTitle(tr("settings_lms_group"))
        self.lms_url_lbl.setText(tr("settings_lms_url"))
        self.test_lms_btn.setText(f"🔍 {tr('settings_test_btn')}")
        self.start_lms_btn.setText(tr("settings_start_lms_btn"))
        self.nllb_group.setTitle(tr("settings_nllb_group"))
        self.dev_lbl.setText(tr("settings_device"))
        self.proxy_lbl.setText(tr("settings_proxy"))
        self.hk_group.setTitle(tr("settings_hk_group"))
        self.hk_info.setText(tr("settings_hk_info"))
        self.tray_group.setTitle(tr("settings_tray_group"))
        self.min_to_tray_cb.setText(tr("settings_min_to_tray"))
        self.start_min_cb.setText(tr("settings_start_min"))
        self.cancel_btn.setText(tr("settings_cancel"))
        self.save_btn.setText(tr("settings_save"))

    def test_lms(self):
        url = self.lms_url.text().strip()
        lmstudio_translator.base_url = url
        is_on, model, models = lmstudio_translator.check_connection()
        if is_on:
            self.lms_status_lbl.setText(f"✓ Подключено! Загруженная модель: {model}")
            self.lms_status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lms_status_lbl.setText("✕ Сервер LM Studio недоступен.")
            self.lms_status_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")

    def start_lms(self):
        self.lms_status_lbl.setText("Запуск сервера через lms CLI...")
        self.lms_status_lbl.setStyleSheet("color: #38bdf8;")
        QApplication.processEvents()
        ok, msg = lmstudio_translator.start_server_via_lms()
        if ok:
            self.lms_status_lbl.setText("✓ " + msg)
            self.lms_status_lbl.setStyleSheet("color: #10b981;")
            self.test_lms()
        else:
            self.lms_status_lbl.setText("✕ " + msg)
            self.lms_status_lbl.setStyleSheet("color: #ef4444;")

    def save_settings(self):
        config.set("lm_studio_url", self.lms_url.text().strip())
        old_dev = config.get("device", "auto")
        new_dev = self.device_combo.currentData()
        config.set("device", new_dev)
        config.set("proxy", self.proxy_edit.text().strip())
        config.set("minimize_to_tray", self.min_to_tray_cb.isChecked())
        config.set("start_minimized", self.start_min_cb.isChecked())
        config.set("ui_language", self.ui_lang_combo.currentData() or "en")
        if old_dev != new_dev:
            nllb_translator.reload_model()
        self.accept()


# --- Download Dialog ---

class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка модели NLLB-200 1.3B INT8")
        self.setFixedSize(480, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #16181f;
                color: #e2e8f0;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #212530;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: white;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #334155;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.title_lbl = QLabel("Загрузка модели Meta NLLB-200 1.3B (~1.38 ГБ)...", self)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #f8fafc;")
        layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel("Подготовка к загрузке...", self)
        layout.addWidget(self.status_lbl)

        self.pbar = QProgressBar(self)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        layout.addWidget(self.pbar)

        self.info_lbl = QLabel("", self)
        self.info_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.info_lbl)

        layout.addStretch()

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        self.cancel_btn = QPushButton("Отмена", self)
        self.cancel_btn.clicked.connect(self.cancel_download)
        h_btn.addWidget(self.cancel_btn)
        layout.addLayout(h_btn)

        self.worker: DownloadWorker = None

    def start(self):
        proxy = config.get("proxy", "")
        self.worker = DownloadWorker(proxy=proxy)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.start()
        self.exec()

    def on_progress(self, cur, total, speed, eta, status):
        pct = int(cur / total * 100) if total > 0 else 0
        self.pbar.setValue(pct)
        self.status_lbl.setText(status)
        cur_mb = cur / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        self.info_lbl.setText(f"{cur_mb:.1f} / {tot_mb:.1f} МБ  •  Скорость: {speed:.2f} МБ/с  •  Осталось: ~{eta:.0f} сек")

    def on_completed(self, success, err):
        if success:
            QMessageBox.information(self, "Успех", "Модель NLLB 1.3B успешно загружена и готова к работе!")
            self.accept()
        else:
            if err:
                QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить модель:\n{err}")
            self.reject()

    def cancel_download(self):
        if self.worker:
            self.worker.cancel()
        self.reject()


# --- Searchable Language ComboBox Component ---

class SearchableLanguageComboBox(QComboBox):
    def __init__(self, is_source: bool = True, parent=None):
        super().__init__(parent)
        self.is_source = is_source
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMaxVisibleItems(18)

        le = self.lineEdit()
        le.setPlaceholderText(tr("search_src_tip") if is_source else tr("search_tgt_tip"))
        le.setClearButtonEnabled(True)
        le.returnPressed.connect(self._on_return_pressed)
        le.installEventFilter(self)

        # Autocompleter configured for substring match
        self.completer = QCompleter(self.model(), self)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self.completer)
        self.completer.activated.connect(self._on_completer_activated)

        comp_popup = self.completer.popup()
        comp_popup.setStyleSheet("""
            QListView {
                background-color: #161922;
                color: #e2e8f0;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 4px;
                outline: none;
                font-size: 12px;
            }
            QListView::item {
                min-height: 24px;
                padding: 3px 8px;
                border-radius: 4px;
            }
            QListView::item:hover {
                background-color: #212636;
            }
            QListView::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
        """)

        self.populate_items()

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == QEvent.Type.FocusIn:
                QTimer.singleShot(0, self.lineEdit().selectAll)
            elif event.type() == QEvent.Type.FocusOut:
                self._on_return_pressed()
        return super().eventFilter(obj, event)

    def populate_items(self, selected_code: Optional[str] = None):
        curr = selected_code if selected_code is not None else (self.currentData() or "auto")
        self.blockSignals(True)
        self.clear()

        # 1. Auto detect / auto target
        if self.is_source:
            self.addItem(tr("auto_detect"), "auto")
        else:
            self.addItem(tr("auto_pair"), "auto")

        ui_lang = config.get("ui_language", "en")

        # 2. Recent languages
        cfg_key = "recent_source_langs" if self.is_source else "recent_target_langs"
        recents = config.get(cfg_key, ["ru", "en"])
        if not isinstance(recents, list):
            recents = ["ru", "en"]

        valid_recents = [c for c in recents if c and c != "auto" and c in LANGUAGES]
        if valid_recents:
            self.insertSeparator(self.count())
            for code in valid_recents:
                info = get_language_info(code)
                disp = get_display_name(code, locale=ui_lang)
                self.addItem(f"⭐ {disp}", info["key"])

        # 3. All 202 languages sorted alphabetically according to UI locale
        self.insertSeparator(self.count())
        for item in get_sorted_languages(locale=ui_lang):
            disp = get_display_name(item["key"], locale=ui_lang)
            self.addItem(disp, item["key"])

        # Restore selection
        idx = self.findData(curr)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)

        self.blockSignals(False)

    def select_code(self, code: str, record: bool = True):
        idx = self.findData(code)
        if idx < 0:
            info = get_language_info(code)
            idx = self.findData(info.get("key", code))
        if idx >= 0:
            self.setCurrentIndex(idx)
        if record and code != "auto":
            self.record_recent(code)

    def record_recent(self, code: str):
        if not code or code == "auto":
            return
        info = get_language_info(code)
        key = info.get("key", code)
        cfg_key = "recent_source_langs" if self.is_source else "recent_target_langs"
        recents = config.get(cfg_key, ["ru", "en"])
        if not isinstance(recents, list):
            recents = ["ru", "en"]
        recents = [c for c in recents if c and c != "auto"]
        if key in recents:
            recents.remove(key)
        recents.insert(0, key)
        recents = recents[:6]  # keep top 6
        config.set(cfg_key, recents)

    def showPopup(self):
        curr = self.currentData() or "auto"
        self.populate_items(curr)
        super().showPopup()

    def _on_return_pressed(self):
        text = self.lineEdit().text().strip().lower()
        if not text:
            idx = self.findData("auto")
            if idx >= 0:
                self.setCurrentIndex(idx)
            return
        # 1. Exact match with itemText or itemData
        for i in range(self.count()):
            d = self.itemData(i)
            if not d:
                continue
            if text == self.itemText(i).lower() or text == str(d).lower():
                self.setCurrentIndex(i)
                self.lineEdit().clearFocus()
                return
        # 2. Substring match
        for i in range(self.count()):
            d = self.itemData(i)
            if not d:
                continue
            if text in self.itemText(i).lower() or text in str(d).lower():
                self.setCurrentIndex(i)
                self.lineEdit().clearFocus()
                return
        # 3. Fallback: revert to current valid item text
        self.setEditText(self.itemText(self.currentIndex()))

    def _on_completer_activated(self, text: str):
        for i in range(self.count()):
            if self.itemText(i) == text:
                self.setCurrentIndex(i)
                self.lineEdit().clearFocus()
                break

    def retranslate(self):
        self.lineEdit().setPlaceholderText(tr("search_src_tip") if self.is_source else tr("search_tgt_tip"))
        curr = self.currentData() or "auto"
        self.populate_items(curr)


# --- Main Window ---

class MainWindow(QMainWindow):
    ui_language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.resize(980, 680)
        self.setMinimumSize(700, 480)

        self.current_req_id = 0
        self.nllb_worker: Optional[NllbWorker] = None
        self.lms_worker: Optional[LmsWorker] = None
        self.ocr_worker: Optional[OcrWorker] = None
        self.snipper: Optional[ScreenSnipper] = None
        self.active_workers_count = 0
        self.downloader_checker = ModelDownloader()

        self.apply_theme()
        self.init_ui()
        self.update_lang_buttons_ui()
        self.check_backends_status()

    def closeEvent(self, event):
        if config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
        else:
            event.accept()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1117;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            QFrame#card {
                background-color: #171923;
                border: 1px solid #262a36;
                border-radius: 10px;
            }
            QTextEdit {
                background-color: #10121a;
                color: #f1f5f9;
                border: 1px solid #262a36;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 1px solid #3b82f6;
            }
            QComboBox {
                background-color: #1a1d27;
                color: #f1f5f9;
                border: 1px solid #33394b;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox:hover {
                border-color: #475569;
            }
            QComboBox:focus, QComboBox:focus-within {
                border: 1px solid #3b82f6;
            }
            QComboBox QLineEdit {
                background: transparent;
                color: #f1f5f9;
                border: none;
                font-size: 12px;
                font-weight: 500;
                padding: 2px 4px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: none;
            }
            QComboBox::down-arrow {
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #94a3b8;
                margin-right: 6px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #f1f5f9;
            }
            QComboBox QAbstractItemView {
                background-color: #161922;
                color: #e2e8f0;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                border: 1px solid #3b82f6;
                padding: 4px;
                outline: none;
                font-size: 12px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 2px 8px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #212636;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::separator {
                height: 1px;
                background-color: #2d3345;
                margin: 4px 2px;
            }
            QPushButton#actionBtn {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton#actionBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#toolBtn {
                background-color: #1f2330;
                color: #cbd5e1;
                border: 1px solid #33394b;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton#toolBtn:hover {
                background-color: #2d3345;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #12141c;
                color: #94a3b8;
                border-top: 1px solid #202431;
            }
        """)

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # 1. Top Bar: Title, Engine Tabs, Settings Button
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        title_lbl = QLabel("🌐 Local Translator", self)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        top_bar.addWidget(title_lbl)

        top_bar.addSpacing(10)

        # Engine mode tabs (3 buttons)
        self.btn_mode_nllb = QPushButton(tr("mode_nllb"), self)
        self.btn_mode_lms = QPushButton(tr("mode_lms"), self)
        self.btn_mode_compare = QPushButton(tr("mode_compare"), self)

        for btn in (self.btn_mode_nllb, self.btn_mode_lms, self.btn_mode_compare):
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1d27;
                    color: #94a3b8;
                    border: 1px solid #2b3142;
                    border-radius: 7px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:checked {
                    background-color: #2563eb;
                    color: white;
                    border: 1px solid #3b82f6;
                }
                QPushButton:hover:!checked {
                    background-color: #242938;
                    color: #cbd5e1;
                }
            """)

        self.btn_mode_nllb.clicked.connect(lambda: self.set_engine_mode("nllb"))
        self.btn_mode_lms.clicked.connect(lambda: self.set_engine_mode("lmstudio"))
        self.btn_mode_compare.clicked.connect(lambda: self.set_engine_mode("compare"))

        top_bar.addWidget(self.btn_mode_nllb)
        top_bar.addWidget(self.btn_mode_lms)
        top_bar.addWidget(self.btn_mode_compare)

        top_bar.addStretch()

        # Primary Translate button moved to Top Bar next to Settings
        self.translate_btn = QPushButton(tr("translate_btn"), self)
        self.translate_btn.setObjectName("actionBtn")
        self.translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.translate_btn.clicked.connect(self.trigger_translation)
        top_bar.addWidget(self.translate_btn)

        # Settings button: clean gear icon without text
        self.settings_btn = QPushButton("⚙", self)
        self.settings_btn.setObjectName("toolBtn")
        self.settings_btn.setFixedSize(36, 32)
        self.settings_btn.setToolTip(tr("settings_btn_tip"))
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(self.settings_btn)

        main_layout.addLayout(top_bar)

        # 2. Status / Download Banner
        self.banner_frame = QFrame(self)
        self.banner_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1b4b;
                border: 1px solid #4338ca;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        banner_layout = QHBoxLayout(self.banner_frame)
        banner_layout.setContentsMargins(10, 4, 10, 4)

        self.banner_icon = QLabel("⚠️", self)
        banner_layout.addWidget(self.banner_icon)

        self.banner_text = QLabel(tr("banner_missing"), self)
        self.banner_text.setStyleSheet("color: #c7d2fe; font-size: 12px; font-weight: 500;")
        banner_layout.addWidget(self.banner_text)

        banner_layout.addStretch()

        self.banner_btn = QPushButton(tr("banner_download"), self)
        self.banner_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4338ca; }
        """)
        self.banner_btn.clicked.connect(self.open_downloader)
        banner_layout.addWidget(self.banner_btn)

        main_layout.addWidget(self.banner_frame)

        # 3. Language Bar
        lang_bar = QHBoxLayout()
        lang_bar.setSpacing(8)

        # Source quick buttons
        src_btn_layout = QHBoxLayout()
        src_btn_layout.setSpacing(3)

        self.src_btn_auto = QPushButton(tr("btn_auto"), self)
        self.src_btn_auto.setObjectName("langQuickBtn")
        self.src_btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.src_btn_auto.clicked.connect(lambda: self.set_src_lang("auto"))
        src_btn_layout.addWidget(self.src_btn_auto)

        self.src_btn_ru = QPushButton("RU", self)
        self.src_btn_ru.setObjectName("langQuickBtn")
        self.src_btn_ru.setCursor(Qt.CursorShape.PointingHandCursor)
        self.src_btn_ru.clicked.connect(lambda: self.set_src_lang("ru"))
        src_btn_layout.addWidget(self.src_btn_ru)

        self.src_btn_en = QPushButton("EN", self)
        self.src_btn_en.setObjectName("langQuickBtn")
        self.src_btn_en.setCursor(Qt.CursorShape.PointingHandCursor)
        self.src_btn_en.clicked.connect(lambda: self.set_src_lang("en"))
        src_btn_layout.addWidget(self.src_btn_en)

        lang_bar.addLayout(src_btn_layout)

        self.src_combo = SearchableLanguageComboBox(is_source=True, parent=self)
        self.src_combo.currentIndexChanged.connect(self.on_src_combo_changed)
        lang_bar.addWidget(self.src_combo, 1)

        # Swap button
        self.swap_btn = QPushButton("⇄", self)
        self.swap_btn.setObjectName("toolBtn")
        self.swap_btn.setFixedSize(36, 32)
        self.swap_btn.setToolTip(tr("swap_tip"))
        self.swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.swap_btn.clicked.connect(self.swap_languages)
        lang_bar.addWidget(self.swap_btn)

        # Target quick buttons
        tgt_btn_layout = QHBoxLayout()
        tgt_btn_layout.setSpacing(3)

        self.tgt_btn_ru = QPushButton("RU", self)
        self.tgt_btn_ru.setObjectName("langQuickBtn")
        self.tgt_btn_ru.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tgt_btn_ru.clicked.connect(lambda: self.set_tgt_lang("ru"))
        tgt_btn_layout.addWidget(self.tgt_btn_ru)

        self.tgt_btn_en = QPushButton("EN", self)
        self.tgt_btn_en.setObjectName("langQuickBtn")
        self.tgt_btn_en.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tgt_btn_en.clicked.connect(lambda: self.set_tgt_lang("en"))
        tgt_btn_layout.addWidget(self.tgt_btn_en)

        self.tgt_btn_auto = QPushButton(tr("btn_auto"), self)
        self.tgt_btn_auto.setObjectName("langQuickBtn")
        self.tgt_btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tgt_btn_auto.clicked.connect(lambda: self.set_tgt_lang("auto"))
        tgt_btn_layout.addWidget(self.tgt_btn_auto)

        lang_bar.addLayout(tgt_btn_layout)

        self.tgt_combo = SearchableLanguageComboBox(is_source=False, parent=self)
        self.tgt_combo.currentIndexChanged.connect(self.on_tgt_combo_changed)
        lang_bar.addWidget(self.tgt_combo, 1)

        lang_bar.addSpacing(6)

        # Auto-translate checkbox
        self.auto_trans_cb = QCheckBox(tr("translate_on_type"), self)
        self.auto_trans_cb.setChecked(False)
        self.auto_trans_cb.setStyleSheet("color: #94a3b8; font-size: 12px;")
        lang_bar.addWidget(self.auto_trans_cb)

        main_layout.addLayout(lang_bar)

        # 4. Central Splitter Area
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #262a36;
                width: 4px;
                border-radius: 2px;
            }
        """)

        # Left: Source Card
        src_card = QFrame(self)
        src_card.setObjectName("card")
        src_layout = QVBoxLayout(src_card)
        src_layout.setContentsMargins(12, 10, 12, 10)
        src_layout.setSpacing(8)

        src_header = QHBoxLayout()
        self.src_title_lbl = QLabel(tr("source_title"), self)
        src_header.addWidget(self.src_title_lbl)
        src_header.addStretch()

        self.char_count_lbl = QLabel(tr("chars_words").format(chars=0, words=0), self)
        self.char_count_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        src_header.addWidget(self.char_count_lbl)

        self.paste_btn = QPushButton(tr("paste_btn"), self)
        self.paste_btn.setObjectName("toolBtn")
        self.paste_btn.clicked.connect(self.paste_source)
        src_header.addWidget(self.paste_btn)

        self.ocr_btn = QPushButton(f"📷 {tr('ocr_btn')}", self)
        self.ocr_btn.setObjectName("toolBtn")
        self.ocr_btn.setToolTip(tr("ocr_btn_tip"))
        self.ocr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ocr_btn.clicked.connect(self.start_screen_ocr)
        src_header.addWidget(self.ocr_btn)

        self.clear_btn = QPushButton(tr("clear_btn"), self)
        self.clear_btn.setObjectName("toolBtn")
        self.clear_btn.clicked.connect(self.clear_source)
        src_header.addWidget(self.clear_btn)

        src_layout.addLayout(src_header)

        self.src_text = QTextEdit(self)
        self.src_text.setPlaceholderText(tr("source_placeholder"))
        self.src_text.textChanged.connect(self.on_source_text_changed)
        src_layout.addWidget(self.src_text)

        self.splitter.addWidget(src_card)

        # Right: Target Area (Dynamic: Single or Compare)
        self.target_container = QWidget(self)
        self.target_layout = QVBoxLayout(self.target_container)
        self.target_layout.setContentsMargins(0, 0, 0, 0)

        # Single Mode Card
        self.single_card = QFrame(self)
        self.single_card.setObjectName("card")
        single_layout = QVBoxLayout(self.single_card)
        single_layout.setContentsMargins(12, 10, 12, 10)
        single_layout.setSpacing(8)

        single_header = QHBoxLayout()
        self.single_title_lbl = QLabel(f"{tr('mode_nllb')}:", self)
        single_header.addWidget(self.single_title_lbl)

        single_header.addStretch()

        self.single_lat_lbl = QLabel("", self)
        self.single_lat_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        single_header.addWidget(self.single_lat_lbl)

        self.single_copy_btn = QPushButton(tr("copy_btn"), self)
        self.single_copy_btn.setObjectName("toolBtn")
        self.single_copy_btn.clicked.connect(lambda: self.copy_text(self.single_text.toPlainText()))
        single_header.addWidget(self.single_copy_btn)

        single_layout.addLayout(single_header)

        self.single_text = QTextEdit(self)
        self.single_text.setReadOnly(True)
        self.single_text.setPlaceholderText(tr("single_placeholder"))
        single_layout.addWidget(self.single_text)

        self.target_layout.addWidget(self.single_card)

        # Compare Mode Splitter (NLLB Card vs LM Studio Card)
        self.compare_widget = QWidget(self)
        compare_layout = QHBoxLayout(self.compare_widget)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(10)

        # Compare Card 1: NLLB 1.3B
        nllb_card = QFrame(self)
        nllb_card.setObjectName("card")
        nllb_card_layout = QVBoxLayout(nllb_card)
        nllb_card_layout.setContentsMargins(10, 8, 10, 8)

        nllb_h = QHBoxLayout()
        self.compare_nllb_title = QLabel(tr("mode_nllb"), self)
        nllb_h.addWidget(self.compare_nllb_title)
        nllb_h.addStretch()
        self.compare_nllb_lat = QLabel("", self)
        self.compare_nllb_lat.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        nllb_h.addWidget(self.compare_nllb_lat)
        self.compare_nllb_copy_btn = QPushButton(tr("copy_btn"), self)
        self.compare_nllb_copy_btn.setObjectName("toolBtn")
        self.compare_nllb_copy_btn.clicked.connect(lambda: self.copy_text(self.compare_nllb_text.toPlainText()))
        nllb_h.addWidget(self.compare_nllb_copy_btn)
        nllb_card_layout.addLayout(nllb_h)

        self.compare_nllb_text = QTextEdit(self)
        self.compare_nllb_text.setReadOnly(True)
        self.compare_nllb_text.setPlaceholderText(tr("nllb_result_placeholder"))
        nllb_card_layout.addWidget(self.compare_nllb_text)

        compare_layout.addWidget(nllb_card)

        # Compare Card 2: LM Studio
        lms_card = QFrame(self)
        lms_card.setObjectName("card")
        lms_card_layout = QVBoxLayout(lms_card)
        lms_card_layout.setContentsMargins(10, 8, 10, 8)

        lms_h = QHBoxLayout()
        self.compare_lms_title = QLabel("🤖 LM Studio", self)
        lms_h.addWidget(self.compare_lms_title)
        lms_h.addStretch()
        self.compare_lms_lat = QLabel("", self)
        self.compare_lms_lat.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        lms_h.addWidget(self.compare_lms_lat)
        self.compare_lms_copy_btn = QPushButton(tr("copy_btn"), self)
        self.compare_lms_copy_btn.setObjectName("toolBtn")
        self.compare_lms_copy_btn.clicked.connect(lambda: self.copy_text(self.compare_lms_text.toPlainText()))
        lms_h.addWidget(self.compare_lms_copy_btn)
        lms_card_layout.addLayout(lms_h)

        self.compare_lms_text = QTextEdit(self)
        self.compare_lms_text.setReadOnly(True)
        self.compare_lms_text.setPlaceholderText(tr("lms_result_placeholder"))
        lms_card_layout.addWidget(self.compare_lms_text)

        compare_layout.addWidget(lms_card)

        self.target_layout.addWidget(self.compare_widget)
        self.splitter.addWidget(self.target_container)

        self.splitter.setSizes([450, 500])
        main_layout.addWidget(self.splitter, 1)

        # Status Bar
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.status_nllb_lbl = QLabel(" NLLB: проверка... ", self)
        self.status_lms_lbl = QLabel(" LM Studio: проверка... ", self)
        self.statusBar.addPermanentWidget(self.status_nllb_lbl)
        self.statusBar.addPermanentWidget(self.status_lms_lbl)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self, self.trigger_translation)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.trigger_translation)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.start_screen_ocr)

        # Input typing debounce timer
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(600)
        self.debounce_timer.timeout.connect(self.on_debounce_translate)

        # Restore engine mode
        init_mode = config.get("engine", "compare")
        self.set_engine_mode(init_mode)

        # Restore saved source and target languages
        init_src = config.get("source_lang", "auto")
        init_tgt = config.get("target_lang", "auto")
        self.src_combo.select_code(init_src, record=False)
        self.tgt_combo.select_code(init_tgt, record=False)
        self.update_lang_buttons_ui()

    def check_backends_status(self):
        # 1. Check local NLLB model completeness
        complete = self.downloader_checker.is_model_complete()
        if complete:
            self.banner_frame.hide()
            dev_str = "CUDA (RTX 3080 Ti)" if nllb_translator.check_cuda_available() else "CPU"
            self.status_nllb_lbl.setText(tr("status_nllb_ready").format(dev=dev_str))
            self.status_nllb_lbl.setStyleSheet("color: #10b981; font-weight: 500;")
        else:
            self.banner_frame.show()
            self.status_nllb_lbl.setText(tr("status_nllb_missing"))
            self.status_nllb_lbl.setStyleSheet("color: #f59e0b; font-weight: 500;")

        # 2. Check LM Studio
        is_on, model, _ = lmstudio_translator.check_connection()
        if is_on:
            self.status_lms_lbl.setText(tr("status_lms_ready").format(model=model))
            self.status_lms_lbl.setStyleSheet("color: #10b981; font-weight: 500;")
            self.compare_lms_title.setText(f"🤖 LM Studio ({model})")
        else:
            self.status_lms_lbl.setText(tr("status_lms_offline"))
            self.status_lms_lbl.setStyleSheet("color: #94a3b8;")

    def retranslate_ui(self):
        self.setWindowTitle(tr("app_title"))
        self.btn_mode_nllb.setText(tr("mode_nllb"))
        self.btn_mode_lms.setText(tr("mode_lms"))
        self.btn_mode_compare.setText(tr("mode_compare"))
        self.settings_btn.setToolTip(tr("settings_btn_tip"))
        self.translate_btn.setText(tr("translate_btn"))

        self.banner_text.setText(tr("banner_missing"))
        self.banner_btn.setText(tr("banner_download"))

        self.src_btn_auto.setText(tr("btn_auto"))
        self.tgt_btn_auto.setText(tr("btn_auto"))
        self.swap_btn.setToolTip(tr("swap_tip"))
        self.auto_trans_cb.setText(tr("translate_on_type"))

        self.src_combo.retranslate()
        self.tgt_combo.retranslate()

        self.src_title_lbl.setText(tr("source_title"))
        self.paste_btn.setText(tr("paste_btn"))
        self.ocr_btn.setText(f"📷 {tr('ocr_btn')}")
        self.ocr_btn.setToolTip(tr("ocr_btn_tip"))
        self.clear_btn.setText(tr("clear_btn"))
        self.src_text.setPlaceholderText(tr("source_placeholder"))

        mode = config.get("engine", "compare")
        if mode == "nllb":
            self.single_title_lbl.setText(f"{tr('mode_nllb')}:")
        elif mode == "lmstudio":
            self.single_title_lbl.setText(f"{tr('mode_lms')}:")
        else:
            self.single_title_lbl.setText(f"{tr('mode_nllb')}:")

        self.single_copy_btn.setText(tr("copy_btn"))
        self.single_text.setPlaceholderText(tr("single_placeholder"))

        self.compare_nllb_title.setText(tr("mode_nllb"))
        self.compare_nllb_copy_btn.setText(tr("copy_btn"))
        self.compare_nllb_text.setPlaceholderText(tr("nllb_result_placeholder"))

        self.compare_lms_copy_btn.setText(tr("copy_btn"))
        self.compare_lms_text.setPlaceholderText(tr("lms_result_placeholder"))

        self.update_char_count()
        self.check_backends_status()
        self.ui_language_changed.emit()

    def set_engine_mode(self, mode: str):
        config.set("engine", mode)
        self.btn_mode_nllb.setChecked(mode == "nllb")
        self.btn_mode_lms.setChecked(mode == "lmstudio")
        self.btn_mode_compare.setChecked(mode == "compare")

        if mode == "compare":
            self.single_card.hide()
            self.compare_widget.show()
        else:
            self.compare_widget.hide()
            self.single_card.show()
            self.single_title_lbl.setText(f"{tr('mode_nllb')}:" if mode == "nllb" else f"{tr('mode_lms')}:")

    def swap_languages(self):
        s_code = self.src_combo.currentData() or "auto"
        t_code = self.tgt_combo.currentData() or "auto"
        self.src_combo.select_code(t_code)
        self.tgt_combo.select_code(s_code)
        config.set("source_lang", t_code)
        config.set("target_lang", s_code)
        self.update_lang_buttons_ui()
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def set_src_lang(self, code: str):
        self.src_combo.select_code(code)
        config.set("source_lang", code)
        self.update_lang_buttons_ui()
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def set_tgt_lang(self, code: str):
        self.tgt_combo.select_code(code)
        config.set("target_lang", code)
        self.update_lang_buttons_ui()
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def on_src_combo_changed(self):
        code = self.src_combo.currentData() or "auto"
        self.src_combo.record_recent(code)
        config.set("source_lang", code)
        self.update_lang_buttons_ui()
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def on_tgt_combo_changed(self):
        code = self.tgt_combo.currentData() or "auto"
        self.tgt_combo.record_recent(code)
        config.set("target_lang", code)
        self.update_lang_buttons_ui()
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def update_lang_buttons_ui(self):
        src = self.src_combo.currentData() or "auto"
        tgt = self.tgt_combo.currentData() or "auto"

        self._style_quick_btn(self.src_btn_auto, src == "auto")
        self._style_quick_btn(self.src_btn_ru, src == "ru")
        self._style_quick_btn(self.src_btn_en, src == "en")

        self._style_quick_btn(self.tgt_btn_ru, tgt == "ru")
        self._style_quick_btn(self.tgt_btn_en, tgt == "en")
        self._style_quick_btn(self.tgt_btn_auto, tgt == "auto")

    def _style_quick_btn(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet("""
                QPushButton#langQuickBtn {
                    background-color: #1e3a8a;
                    color: #93c5fd;
                    border: 1px solid #3b82f6;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton#langQuickBtn {
                    background-color: #171a23;
                    color: #94a3b8;
                    border: 1px solid #2d3345;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton#langQuickBtn:hover {
                    background-color: #212636;
                    color: #f1f5f9;
                    border-color: #3e475f;
                }
            """)

    def paste_source(self):
        from PyQt6.QtWidgets import QApplication
        cb = QApplication.clipboard()
        mime = cb.mimeData()
        if mime and mime.hasImage():
            pix = cb.pixmap()
            if not pix.isNull():
                self.on_snippet_captured(pix)
                return
        text = get_clipboard_text()
        if text:
            self.src_text.setPlainText(text)

    def clear_source(self):
        self.src_text.clear()
        self.single_text.clear()
        self.compare_nllb_text.clear()
        self.compare_lms_text.clear()
        self.single_lat_lbl.setText("")
        self.compare_nllb_lat.setText("")
        self.compare_lms_lat.setText("")
        self.current_req_id += 1

    def copy_text(self, text: str):
        if text:
            set_clipboard_text(text)
            self.statusBar.showMessage(tr("copied_tip"), 2500)

    def update_char_count(self):
        text = self.src_text.toPlainText()
        chars = len(text)
        words = len(text.split())
        self.char_count_lbl.setText(tr("chars_words").format(chars=chars, words=words))

    def on_source_text_changed(self):
        self.update_char_count()
        if self.auto_trans_cb.isChecked() and len(self.src_text.toPlainText()) > 1:
            self.debounce_timer.start()

    def on_debounce_translate(self):
        if self.src_text.toPlainText().strip():
            self.trigger_translation()

    def trigger_translation(self):
        if not self.translate_btn.isEnabled():
            return
        text = self.src_text.toPlainText().strip()
        if not text:
            return

        mode = config.get("engine", "compare")
        src = self.src_combo.currentData() or "auto"
        tgt = self.tgt_combo.currentData() or "auto"

        self.current_req_id += 1
        req_id = self.current_req_id
        self.translate_btn.setEnabled(False)

        if mode == "compare":
            self.compare_nllb_text.setPlainText(tr("translating_nllb"))
            self.compare_lms_text.setPlainText(tr("translating_lms"))
            self.compare_nllb_lat.setText("")
            self.compare_lms_lat.setText("")
            self.active_workers_count = 2

            self.nllb_worker = NllbWorker(req_id, text, src, tgt)
            self.nllb_worker.finished.connect(self.on_nllb_finished)
            self.nllb_worker.start()

            self.lms_worker = LmsWorker(req_id, text, src, tgt)
            self.lms_worker.finished.connect(self.on_lms_finished)
            self.lms_worker.start()

        elif mode == "nllb":
            self.single_text.setPlainText(tr("translating_nllb"))
            self.single_lat_lbl.setText("")
            self.active_workers_count = 1

            self.nllb_worker = NllbWorker(req_id, text, src, tgt)
            self.nllb_worker.finished.connect(self.on_single_nllb_finished)
            self.nllb_worker.start()

        elif mode == "lmstudio":
            self.single_text.setPlainText(tr("translating_lms"))
            self.single_lat_lbl.setText("")
            self.active_workers_count = 1

            self.lms_worker = LmsWorker(req_id, text, src, tgt)
            self.lms_worker.finished.connect(self.on_single_lms_finished)
            self.lms_worker.start()

    def _decrement_active_workers(self):
        self.active_workers_count -= 1
        if self.active_workers_count <= 0:
            self.translate_btn.setEnabled(True)
            self.check_backends_status()

    def on_nllb_finished(self, req_id: int, res: str, lat: float, err: str):
        if req_id != self.current_req_id:
            return
        if err:
            self.compare_nllb_text.setPlainText(f"❌ Ошибка NLLB:\n{err}")
            self.compare_nllb_lat.setText("")
        else:
            self.compare_nllb_text.setPlainText(res)
            self.compare_nllb_lat.setText(f"⚡ {lat:.0f} ms" if lat > 0 else "⚡ Кэш")
        self._decrement_active_workers()

    def on_lms_finished(self, req_id: int, res: str, lat: float, model: str, err: str):
        if req_id != self.current_req_id:
            return
        if err:
            self.compare_lms_text.setPlainText(f"❌ Ошибка LM Studio:\n{err}")
            self.compare_lms_lat.setText("")
        else:
            self.compare_lms_text.setPlainText(res)
            self.compare_lms_lat.setText(f"⚡ {lat:.0f} ms" if lat > 0 else "⚡ Кэш")
            if model:
                self.compare_lms_title.setText(f"🤖 LM Studio ({model})")
        self._decrement_active_workers()

    def on_single_nllb_finished(self, req_id: int, res: str, lat: float, err: str):
        if req_id != self.current_req_id:
            return
        if err:
            self.single_text.setPlainText(f"❌ Ошибка NLLB:\n{err}")
            self.single_lat_lbl.setText("")
        else:
            self.single_text.setPlainText(res)
            self.single_lat_lbl.setText(f"⚡ {lat:.0f} ms" if lat > 0 else "⚡ Кэш")
        self._decrement_active_workers()

    def on_single_lms_finished(self, req_id: int, res: str, lat: float, model: str, err: str):
        if req_id != self.current_req_id:
            return
        if err:
            self.single_text.setPlainText(f"❌ Ошибка LM Studio:\n{err}")
            self.single_lat_lbl.setText("")
        else:
            self.single_text.setPlainText(res)
            self.single_lat_lbl.setText(f"⚡ {lat:.0f} ms" if lat > 0 else "⚡ Кэш")
        self._decrement_active_workers()

    def set_source_text(self, text: str):
        self.src_text.setPlainText(text)
        self.trigger_translation()

    def open_downloader(self):
        dlg = DownloadDialog(self)
        dlg.start()
        self.check_backends_status()

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.check_backends_status()

    # --- OCR / Snippet Capture Methods ---

    def start_screen_ocr(self):
        """Hides the main window briefly if visible, then displays the screen snipper overlay."""
        if self.snipper is not None:
            try:
                self.snipper.close()
            except Exception:
                pass
            self.snipper = None

        was_visible = self.isVisible()
        if was_visible:
            self.hide()
            # 160ms delay allows the OS window manager to cleanly un-draw this window
            QTimer.singleShot(160, self._launch_snipper)
        else:
            self._launch_snipper()

    def _launch_snipper(self):
        self.snipper = ScreenSnipper()
        self.snipper.snippet_captured.connect(self.on_snippet_captured)
        self.snipper.cancelled.connect(self.on_snipper_cancelled)
        self.snipper.show()
        self.snipper.activateWindow()

    def on_snipper_cancelled(self):
        self.snipper = None
        self.show()
        self.activateWindow()
        self.raise_()

    def on_snippet_captured(self, pixmap):
        self.snipper = None
        self.show()
        self.activateWindow()
        self.raise_()

        b64 = pixmap_to_base64(pixmap)
        if not b64:
            return

        self.current_req_id += 1
        req_id = self.current_req_id
        self.src_text.setPlainText(f"⏳ {tr('ocr_recognizing')}")
        self.translate_btn.setEnabled(False)

        self.ocr_worker = OcrWorker(req_id, b64)
        self.ocr_worker.finished.connect(self.on_ocr_finished)
        self.ocr_worker.start()

    def on_ocr_finished(self, req_id: int, res: str, lat: float, model: str, err: str):
        if req_id != self.current_req_id:
            return
        self.translate_btn.setEnabled(True)

        if err:
            err_msg = (
                f"❌ OCR: {err}\n\n"
                f"💡 {tr('ocr_vision_hint')}"
            )
            self.src_text.setPlainText(err_msg)
            self.statusBar.showMessage(f"OCR: {err[:60]}", 4000)
            return

        clean_text = res.strip()
        if not clean_text:
            self.src_text.setPlainText("")
            self.statusBar.showMessage("OCR: текст не обнаружен", 3000)
            return

        # Place recognized text into the first window (Source Text) so the user can copy/edit it
        self.src_text.setPlainText(clean_text)
        lat_str = f"⚡ {lat:.0f} ms" if lat > 0 else ""
        model_str = f" ({model})" if model else ""
        self.statusBar.showMessage(f"📷 OCR{model_str}: {len(clean_text)} символов {lat_str}".strip(), 4000)

        # Trigger translation into target language(s)
        self.trigger_translation()

