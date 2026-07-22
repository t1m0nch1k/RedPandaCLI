"""Compact overlay window в стиле Perplexity Computer (PySide6).

Layout:
    ┌──────────────────────────────────────┐
    │  [ screenshot preview, rounded ]     │  ← сделан ПЕРЕД открытием
    ├──────────────────────────────────────┤
    │  Ask about what's on your screen...  │  ← QLineEdit + кнопка отправки
    ├──────────────────────────────────────┤
    │  Answer from agent...                │  ← QTextEdit (read-only)
    └──────────────────────────────────────┘

Frameless + translucent + stay-on-top. Анимация fade-in. Закрытие по Esc,
потере фокуса или Enter (Shift+Enter = перенос строки).

CursorPreviewOverlay — прозрачный полноэкранный слой для предпросмотра
действий с курсором (пульсирующий круг + таймер + отмена).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger("aios.overlay.window")


# ──────────────────────────────────────────────────────────  стиль (как в frontend)
BG = "#0f0f17"
BG_PANEL = "#15151f"
BG_INPUT = "#1c1c2a"
ACCENT = "#6366f1"
ACCENT_BRIGHT = "#818cf8"
TEXT_PRIMARY = "#e4e4e7"
TEXT_MUTED = "#71717a"
BORDER = "#27272f"
WIDTH = 620
PREVIEW_HEIGHT = 160


class OverlayWindow(QWidget):
    """Compact Perplexity-style overlay."""

    def __init__(
        self,
        on_submit: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_submit = on_submit
        self._closing = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # не показывать в таскбаре
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self.setFixedSize(WIDTH, 460)
        self._build_ui()
        self._apply_palette()

        # Анимация появления
        self._fade_anim: QPropertyAnimation | None = None
        self._scale = 0.96

        # Таймер для закрытия по потере фокуса (с задержкой, чтобы клик по полю не закрывал)
        self._focus_timer = QTimer(self)
        self._focus_timer.setSingleShot(True)
        self._focus_timer.setInterval(150)
        self._focus_timer.timeout.connect(self._maybe_close_on_focus_loss)

        self._think_timer = QTimer(self)
        self._think_timer.timeout.connect(self._on_think_tick)
        self._think_dots = 0

    # -------------------------------------------------------------- UI build

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(
            f"""
            QFrame#card {{
                background: {BG_PANEL};
                border-radius: 16px;
                border: 1px solid {BORDER};
            }}
            QLabel {{ color: {TEXT_PRIMARY}; background: transparent; border: none; }}
            QLabel#hint {{ color: {TEXT_MUTED}; font-size: 11px; }}
            QLabel#title {{ color: {TEXT_MUTED}; font-size: 12px;
                            font-weight: 600; letter-spacing: 0.5px; }}
            QLineEdit, QPlainTextEdit {{
                background: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 14px;
                selection-background-color: {ACCENT};
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {ACCENT_BRIGHT};
            }}
            QPushButton#send {{
                background: {ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#send:hover {{ background: {ACCENT_BRIGHT}; }}
            QPushButton#send:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}
            QPlainTextEdit#answer {{
                background: {BG};
                border: 1px solid {BORDER};
                border-radius: 10px;
                color: {TEXT_PRIMARY};
                font-size: 13px;
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 12)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        # Header
        title = QLabel("AIOS · SCREEN ASSISTANT")
        title.setObjectName("title")
        card_layout.addWidget(title)

        # Screenshot preview
        self._preview = QLabel()
        self._preview.setMinimumHeight(PREVIEW_HEIGHT)
        self._preview.setMaximumHeight(PREVIEW_HEIGHT)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            f"background: {BG}; border-radius: 10px; border: 1px solid {BORDER};"
        )
        self._preview.setText("☐ no screenshot")
        self._preview.setStyleSheet(
            f"background: {BG}; border-radius: 10px; border: 1px solid {BORDER}; "
            f"color: {TEXT_MUTED}; font-size: 12px;"
        )
        card_layout.addWidget(self._preview)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Спросите про то, что на экране…")
        self._input.returnPressed.connect(self._submit)
        self._send_btn = QPushButton("Ask")
        self._send_btn.setObjectName("send")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._submit)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._send_btn)
        card_layout.addLayout(input_row)

        # Answer area
        self._answer = QPlainTextEdit()
        self._answer.setObjectName("answer")
        self._answer.setReadOnly(True)
        self._answer.setPlaceholderText("Ответ агента появится здесь…")
        card_layout.addWidget(self._answer, 1)

        # Hint
        hint = QLabel("Enter — отправить · Esc — закрыть · клик вне окна — закрыть")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(hint)

        outer.addWidget(card)

    def _apply_palette(self) -> None:
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.setPalette(pal)

    # -------------------------------------------------------------- показ

    def show_with_screenshot(self, png_bytes: bytes) -> None:
        """Показать окно с заданным скриншотом (PNG bytes)."""
        pm = QPixmap()
        pm.loadFromData(png_bytes, "PNG")
        if not pm.isNull():
            # Скейлим с сохранением пропорций под ширину превью
            target_w = WIDTH - 64
            scaled = pm.scaledToWidth(
                target_w, Qt.SmoothTransformation
            )
            if scaled.height() > PREVIEW_HEIGHT - 8:
                scaled = scaled.scaled(
                    QSize(target_w, PREVIEW_HEIGHT - 8),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            self._preview.setPixmap(scaled)
            self._preview.setStyleSheet(
                f"background: {BG}; border-radius: 10px; border: 1px solid {BORDER};"
            )

        # Очистка предыдущего ответа, фокус на ввод
        self._answer.clear()
        self._input.clear()

        # Позиционирование по центру активного экрана
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

        # Анимация появления
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()

        import sys
        if sys.platform == "win32":
            import ctypes
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            ALT = 0x12
            user32.keybd_event(ALT, 0, 0, 0)
            user32.keybd_event(ALT, 0, 0x0002, 0)
            user32.SetForegroundWindow(hwnd)

        self._input.setFocus()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(160)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

    # -------------------------------------------------------------- ответы

    def _on_think_tick(self) -> None:
        self._think_dots = (self._think_dots + 1) % 4
        self._answer.setPlainText("Thinking" + "." * self._think_dots)

    def set_thinking(self) -> None:
        self._think_dots = 0
        self._answer.setPlainText("Thinking")
        self._think_timer.start(500)

    def append_answer(self, text: str) -> None:
        if self._think_timer.isActive():
            self._think_timer.stop()
        self._answer.setPlainText(text)

    # -------------------------------------------------------------- события

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        # Запускаем отложенную проверку — клик по input/send не должен закрывать
        self._focus_timer.start()

    def _maybe_close_on_focus_loss(self) -> None:
        # Если ни один виджет окна не в фокусе — закрываем
        if QApplication.focusWidget() is None:
            self.close_overlay()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Клик «мимо» (по прозрачной рамке) — закрытие
        rect = self.rect().adjusted(16, 16, -16, -16)
        if not rect.contains(event.position().toPoint()):
            self.close_overlay()
        super().mousePressEvent(event)

    def close_overlay(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._focus_timer.stop()
        self.hide()
        self._closing = False

    # -------------------------------------------------------------- submit

    def _submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._send_btn.setEnabled(False)
        self.set_thinking()
        try:
            self._on_submit(text)
        finally:
            self._send_btn.setEnabled(True)


# ───────────────────────────────────────────────────────  cursor preview overlay


class CursorPreviewOverlay(QWidget):
    """Полноэкранный прозрачный слой: пульсирующий круг в точке клика + отмена."""

    BG_OVERLAY = QColor(0, 0, 0, 80)
    RING_COLOR = QColor(99, 102, 241, 220)
    RING_COLOR_FADE = QColor(99, 102, 241, 60)
    TEXT_COLOR = QColor(228, 228, 231, 200)

    def __init__(
        self,
        action_id: str,
        target_x: int,
        target_y: int,
        on_cancel: Callable[[str], None],
        delay: float = 1.5,
    ) -> None:
        super().__init__()
        self._action_id = action_id
        self._target = QPoint(target_x, target_y)
        self._on_cancel = on_cancel
        self._delay = delay

        self._elapsed = 0.0
        self._pulse_phase = 0.0
        self._cancelled = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.showFullScreen()

        self._tick_timer = QTimer(self)
        self._tick_timer.setTimerType(Qt.PreciseTimer)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(16)

    # -------------------------------------------------------------- paint

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Полупрозрачный фон
        painter.fillRect(self.rect(), self.BG_OVERLAY)

        cx, cy = self._target.x(), self._target.y()

        # Пульсирующий радиус: 24 → 40 пикселей
        pulse = math.sin(self._pulse_phase * math.pi * 2) * 0.5 + 0.5
        radius = 24.0 + pulse * 16.0

        # Внешнее кольцо (пульсирующее)
        pen_outer = QPen(self.RING_COLOR_FADE, 3)
        painter.setPen(pen_outer)
        painter.drawEllipse(QPointF(cx, cy), radius + 8, radius + 8)

        # Внутреннее кольцо
        pen_inner = QPen(self.RING_COLOR, 2.5)
        painter.setPen(pen_inner)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Прогресс-арка (сколько осталось)
        remaining = max(0.0, self._delay - self._elapsed)
        progress = remaining / self._delay if self._delay > 0 else 0.0
        pen_arc = QPen(self.RING_COLOR, 3)
        painter.setPen(pen_arc)
        arc_rect = QRectF(cx - radius - 4, cy - radius - 4, (radius + 4) * 2, (radius + 4) * 2)
        span = int(360 * (1.0 - progress))
        painter.drawArc(arc_rect, 90 * 16, -span * 16)

        # Текст подсказки
        painter.setPen(self.TEXT_COLOR)
        painter.setFont(self.font())
        if self._cancelled:
            text = "Отменяется…"
        else:
            text = f"Отмена (щелчок) · {remaining:.1f}с"
        text_rect = QRectF(cx - 150, cy + radius + 20, 300, 30)
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def _tick(self) -> None:
        dt = 0.016
        self._elapsed += dt
        self._pulse_phase += dt * 2.5
        if self._pulse_phase >= 1.0:
            self._pulse_phase -= 1.0
        if self._elapsed >= self._delay and not self._cancelled:
            self._tick_timer.stop()
            self.close()
            return
        self.update()

    # -------------------------------------------------------------- cancel

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._cancelled:
            self._cancelled = True
            self._tick_timer.stop()
            self._on_cancel(self._action_id)
            self.close()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape and not self._cancelled:
            self._cancelled = True
            self._tick_timer.stop()
            self._on_cancel(self._action_id)
            self.close()
            return
        super().keyPressEvent(event)
