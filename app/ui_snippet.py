import sys
import base64
from typing import Optional
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QByteArray, QBuffer, QIODevice
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QGuiApplication,
    QPixmap, QCursor, QPaintEvent, QMouseEvent, QKeyEvent
)
from app.i18n import tr


def pixmap_to_base64(pixmap: QPixmap) -> str:
    """Convert QPixmap to base64 PNG string in-memory."""
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return base64.b64encode(byte_array.data()).decode("utf-8")


class ScreenSnipper(QWidget):
    """
    High-DPI multi-monitor screen snippet overlay.
    Allows user to select any rectangular area on screen to capture.
    """
    snippet_captured = pyqtSignal(QPixmap)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.start_pos: Optional[QPoint] = None
        self.current_pos: Optional[QPoint] = None
        self.is_selecting = False
        self.selection_rect = QRect()

        # Capture the entire virtual desktop across all screens
        screens = QGuiApplication.screens()
        total_rect = QRect()
        for s in screens:
            total_rect = total_rect.united(s.geometry())

        self.total_rect = total_rect
        self.setGeometry(total_rect)

        # Composite individual screen grabs at native physical resolution
        self.screen_items = []
        for s in screens:
            geo = s.geometry()
            dpr = s.devicePixelRatio()
            pix = s.grabWindow(0)
            self.screen_items.append({
                "screen": s,
                "geo": geo,
                "dpr": dpr,
                "pixmap": pix
            })

        # Pre-render master virtual background pixmap for painting
        self.master_pixmap = QPixmap(total_rect.size())
        painter = QPainter(self.master_pixmap)
        for item in self.screen_items:
            geo = item["geo"]
            pix = item["pixmap"]
            # Paint scaled to logical coordinates
            painter.drawPixmap(
                geo.x() - total_rect.x(),
                geo.y() - total_rect.y(),
                geo.width(),
                geo.height(),
                pix
            )
        painter.end()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Draw base captured desktop
        painter.drawPixmap(0, 0, self.master_pixmap)

        # 2. Draw dimmed overlay
        dim_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), dim_color)

        # 3. If selecting, cut out and restore bright clean pixels in selection
        if self.is_selecting and self.selection_rect.isValid() and self.selection_rect.width() > 2:
            # Draw clear un-dimmed region from master
            painter.drawPixmap(
                self.selection_rect.topLeft(),
                self.master_pixmap,
                self.selection_rect
            )

            # Draw crisp blue bounding box
            pen = QPen(QColor(59, 130, 246), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

            # Draw corner accent marks
            r = self.selection_rect
            painter.setPen(QPen(QColor(147, 197, 253), 3))
            c_len = min(12, min(r.width() // 4, r.height() // 4))
            # Top-left
            painter.drawLine(r.left(), r.top(), r.left() + c_len, r.top())
            painter.drawLine(r.left(), r.top(), r.left(), r.top() + c_len)
            # Top-right
            painter.drawLine(r.right(), r.top(), r.right() - c_len, r.top())
            painter.drawLine(r.right(), r.top(), r.right(), r.top() + c_len)
            # Bottom-left
            painter.drawLine(r.left(), r.bottom(), r.left() + c_len, r.bottom())
            painter.drawLine(r.left(), r.bottom(), r.left(), r.bottom() - c_len)
            # Bottom-right
            painter.drawLine(r.right(), r.bottom(), r.right() - c_len, r.bottom())
            painter.drawLine(r.right(), r.bottom(), r.right(), r.bottom() - c_len)

            # Draw size indicator badge (e.g. "320 x 140")
            badge_text = f"{r.width()} × {r.height()}"
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            fm = painter.fontMetrics()
            bw = fm.horizontalAdvance(badge_text) + 14
            bh = 22
            bx = min(self.width() - bw - 10, max(10, r.right() - bw))
            by = r.bottom() + 6 if r.bottom() + bh + 10 < self.height() else r.top() - bh - 6

            badge_rect = QRect(bx, by, bw, bh)
            painter.setBrush(QColor(15, 23, 42, 230))
            painter.setPen(QColor(59, 130, 246))
            painter.drawRoundedRect(badge_rect, 5, 5)
            painter.setPen(QColor(241, 245, 249))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 4. Top Instruction Pill
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        hint_text = tr("ocr_tip_overlay")
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        hfm = painter.fontMetrics()
        hw = hfm.horizontalAdvance(hint_text) + 28
        hh = 36
        # Center in primary screen
        prim_geo = QGuiApplication.primaryScreen().geometry()
        hx = prim_geo.x() - self.total_rect.x() + (prim_geo.width() - hw) // 2
        hy = prim_geo.y() - self.total_rect.y() + 28

        hrect = QRect(hx, hy, hw, hh)
        painter.setBrush(QColor(15, 23, 42, 235))
        painter.setPen(QPen(QColor(59, 130, 246), 1))
        painter.drawRoundedRect(hrect, 10, 10)

        painter.setPen(QColor(248, 250, 252))
        painter.drawText(hrect, Qt.AlignmentFlag.AlignCenter, hint_text)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = self.start_pos
            self.selection_rect = QRect(self.start_pos, self.current_pos)
            self.is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_selecting:
            self.current_pos = event.pos()
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            r = self.selection_rect

            if r.width() > 10 and r.height() > 10:
                # Find which screen the selection is mostly in to extract high-DPI physical pixels
                cropped_pixmap = self._crop_high_dpi(r)
                self.snippet_captured.emit(cropped_pixmap)
                self.close()
            else:
                self.cancelled.emit()
                self.close()

    def _crop_high_dpi(self, r: QRect) -> QPixmap:
        """
        Crop high-DPI physical pixels from the appropriate screen pixmap
        so the vision LLM receives crisp, unscaled text.
        """
        # Map logical coordinate r into global coordinates
        gx = r.x() + self.total_rect.x()
        gy = r.y() + self.total_rect.y()

        # Find matching screen
        for item in self.screen_items:
            s_geo = item["geo"]
            if s_geo.contains(gx, gy):
                # Rel coords within this screen
                rx = gx - s_geo.x()
                ry = gy - s_geo.y()
                dpr = item["dpr"]
                phys_rect = QRect(
                    int(rx * dpr),
                    int(ry * dpr),
                    int(r.width() * dpr),
                    int(r.height() * dpr)
                )
                phys_rect = phys_rect.intersected(item["pixmap"].rect())
                return item["pixmap"].copy(phys_rect)

        # Fallback: crop from master logical pixmap
        return self.master_pixmap.copy(r)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.selection_rect.isValid() and self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                cropped = self._crop_high_dpi(self.selection_rect)
                self.snippet_captured.emit(cropped)
                self.close()
