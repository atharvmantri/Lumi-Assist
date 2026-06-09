"""JARVIS desktop overlay — bottom-center animated particles.

Design: JARVIS lives invisibly on the desktop and only appears at the bottom
center when active. No window chrome, click-through, elegant particle
animations with flowing golden waveforms.

States:
  idle       → invisible (no overlay shown)
  listening  → golden waveform bars at bottom center
  thinking   → blue glowing geometric orb (hexagonal pattern)
  responding → golden particle swirl with response text bubble

All rendering is via QPainter on a fully transparent frameless window.
Animations use QTimer at ~30 FPS with phase-based sine wave modulation.
"""
from __future__ import annotations

import math
import queue
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from PyQt6.QtCore import (
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QEasingCurve,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QLinearGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget


# ============================================================================
# State enum
# ============================================================================

class OverlayState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    RESPONDING = "responding"


@dataclass
class OverlayCommand:
    """Thread-safe command from background thread → overlay."""
    state: OverlayState | None = None
    text: str = ""
    amplitude: float = 1.0
    shutdown: bool = False


# ============================================================================
# Particle system
# ============================================================================

class Particle:
    """A golden particle with position, velocity, and lifetime.
    Particles flow upward along a waveform path with glow."""
    def __init__(self, x: float, y: float, *, flow_angle: float = 0, burst: bool = False):
        self.x = x
        self.y = y
        if burst:
            # Burst particles shoot outward from center
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 200)
        else:
            angle = flow_angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(25, 70)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 50 if not burst else math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.3, 0.9) if burst else random.uniform(0.4, 1.2)
        self.size = random.uniform(2, 7) if not burst else random.uniform(3, 10)
        # Warm golden palette
        self.color = random.choice([
            (255, 215, 60),   # gold
            (255, 200, 50),   # amber
            (255, 230, 100),  # light gold
            (255, 180, 70),   # deep gold
            (255, 240, 140),  # bright gold
        ])

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 20 * dt  # gentle gravity
        self.vx *= 0.98     # slight drag
        self.life -= self.decay * dt
        return self.life > 0


# ============================================================================
# Overlay widget
# ============================================================================

OVERLAY_WIDTH = 600       # Wider — more visible
OVERLAY_HEIGHT = 220      # Taller for more room
FADE_DURATION = 400       # ms


class DesktopOverlay(QWidget):
    """Bottom-center overlay — transparent, click-through, always-on-top."""

    _command_queue: queue.Queue[OverlayCommand] = queue.Queue()
    _shutdown_event = threading.Event()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = OverlayState.IDLE
        self._target_state = OverlayState.IDLE
        self._text = ""
        self._amplitude = 1.0
        self._phase = 0.0
        self._fade_opacity = 0.0
        self._particles: list[Particle] = []
        self._last_time = time.perf_counter()
        self._fade_anim = None
        self._pulse_phase = 0.0
        self._transition_alpha = 1.0  # for smooth state transitions
        self._transition_speed = 0.05

        # Window setup: frameless, transparent, click-through, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

        # Don't show initially — only show when state changes from IDLE
        self.setWindowOpacity(0.0)

        # Timer for animation ticks (~30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    # ---- Thread-safe command push ----

    @classmethod
    def push_command(cls, cmd: OverlayCommand) -> None:
        if cmd.shutdown:
            cls._shutdown_event.set()
        try:
            cls._command_queue.put_nowait(cmd)
        except queue.Full:
            pass

    @classmethod
    def drain_commands(cls) -> list[OverlayCommand]:
        out: list[OverlayCommand] = []
        while True:
            try:
                out.append(cls._command_queue.get_nowait())
            except queue.Empty:
                break
        return out

    # ---- Opacity property for fade ----

    def _get_fade_opacity(self) -> float:
        return self._fade_opacity

    def _set_fade_opacity(self, value: float) -> None:
        self._fade_opacity = value
        self.setWindowOpacity(max(0.0, min(1.0, value)))

    fade_opacity = pyqtProperty(float, _get_fade_opacity, _set_fade_opacity)

    # ---- Paint ----

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        opacity = self._fade_opacity
        if opacity < 0.01:
            return

        painter.save()
        painter.setOpacity(opacity)

        r = self.rect()
        cx = r.center().x()
        cy = r.bottom() - 35  # near bottom edge

        # Activation flash — bright golden burst on wake
        if self._transition_alpha < 0.8 and self._state != OverlayState.IDLE:
            flash_alpha = int((1.0 - self._transition_alpha / 0.8) * 80)
            flash_radius = 80 + 40 * self._transition_alpha
            flash = QRadialGradient(QPointF(cx, cy), flash_radius)
            flash.setColorAt(0, QColor(255, 230, 100, flash_alpha))
            flash.setColorAt(0.5, QColor(255, 200, 60, flash_alpha // 3))
            flash.setColorAt(1, QColor(255, 180, 40, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(flash)
            painter.drawEllipse(QPointF(cx, cy), flash_radius, flash_radius)

        if self._state == OverlayState.LISTENING:
            self._draw_waveform(painter, cx, cy, amplitude=self._amplitude)
        elif self._state == OverlayState.THINKING:
            self._draw_thinking_orb(painter, cx, cy)
        elif self._state == OverlayState.RESPONDING:
            self._draw_particles(painter, cx, cy)
            if self._text:
                self._draw_text_bubble(painter, cx, cy - 60, self._text)

        painter.restore()
        super().paintEvent(event)

    # ---- Drawing: Waveform ----

    def _draw_waveform(self, painter, cx, cy, amplitude=1.0):
        """Golden waveform bars — smooth, glowing, bottom-centered.
        Uses sine harmonics for organic motion with a soft glow envelope."""
        bar_count = 50
        bar_gap = 2
        total_w = OVERLAY_WIDTH * 0.6
        bar_w = max(3, (total_w - bar_count * bar_gap) / bar_count)
        max_bar_h = 45 * amplitude

        # Pre-compute the waveform envelope for smoothness
        for i in range(bar_count):
            x = cx + (i - bar_count / 2) * (bar_w + bar_gap)

            # Multi-harmonic sine blend for organic movement
            p1 = math.sin(i * 0.35 + self._phase * 3.5)
            p2 = math.sin(i * 0.9 + self._phase * 5.5)
            p3 = math.sin(i * 0.55 + self._phase * 2.5)
            p4 = math.sin(i * 1.3 + self._phase * 7.0)
            bar_h = (p1 * 0.35 + p2 * 0.25 + p3 * 0.20 + p4 * 0.20)
            bar_h = max(0.08, abs(bar_h)) * max_bar_h

            # Gaussian envelope — bars taper at edges
            t = (i / max(bar_count - 1, 1)) - 0.5
            envelope = math.exp(-t * t * 8)  # tight gaussian
            bar_h *= envelope

            y_top = cy - bar_h

            # Soft glow behind the bar
            glow_alpha = int(40 * envelope)
            glow_size = bar_w * 3
            glow = QColor(255, 200, 50, glow_alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(
                QPointF(x, cy - bar_h / 2),
                glow_size, glow_size * 0.6,
            )

            # Bar with gradient
            grad = QLinearGradient(QPointF(x, y_top), QPointF(x, cy))
            grad.setColorAt(0, QColor(255, 230, 90, 230))
            grad.setColorAt(0.5, QColor(255, 200, 60, 180))
            grad.setColorAt(1, QColor(255, 170, 40, 40))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                QRectF(x - bar_w / 2, y_top, bar_w, bar_h),
                bar_w / 2, bar_w / 2,
            )

        # Subtle waveform outline on top
        pen = QPen(QColor(255, 220, 100, 100), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        for i in range(60):
            t = i / 60
            x = cx + (t - 0.5) * total_w
            y = cy + math.sin(t * 10 + self._phase * 4) * 15 * amplitude
            gaussian = math.exp(-((t - 0.5) ** 2) * 8)
            y *= gaussian
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)

    # ---- Drawing: Thinking orb ----

    def _draw_thinking_orb(self, painter, cx, cy):
        """Blue glowing geometric orb — hexagonal pattern with concentric pulse rings."""
        base_radius = 25 + 4 * math.sin(self._phase * 2)

        # Outer ambient glow (large soft circle)
        ambient = QRadialGradient(QPointF(cx, cy), base_radius * 5)
        ambient.setColorAt(0, QColor(0, 180, 255, 60))
        ambient.setColorAt(0.3, QColor(0, 150, 255, 25))
        ambient.setColorAt(0.7, QColor(0, 120, 255, 8))
        ambient.setColorAt(1, QColor(0, 100, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ambient)
        painter.drawEllipse(QPointF(cx, cy), base_radius * 5, base_radius * 5)

        # Pulsing concentric rings
        for ring in range(3):
            ring_phase = self._phase * 1.2 + ring * 2.1
            ring_radius = base_radius * (1.5 + ring * 0.8) + 5 * math.sin(ring_phase)
            ring_alpha = int(80 - ring * 25)
            pen = QPen(QColor(0, 180 + ring * 20, 255, ring_alpha), 1.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), ring_radius, ring_radius)

        # Inner glow
        inner_glow = QRadialGradient(QPointF(cx, cy), base_radius * 2)
        inner_glow.setColorAt(0, QColor(0, 200, 255, 100))
        inner_glow.setColorAt(0.5, QColor(0, 160, 255, 30))
        inner_glow.setColorAt(1, QColor(0, 120, 255, 0))
        painter.setBrush(inner_glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), base_radius * 2, base_radius * 2)

        # Rotating hexagonal pattern (6 lines)
        pen = QPen(QColor(0, 210, 255, 220), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        for i in range(6):
            angle = (i / 6) * 2 * math.pi + self._phase * 1.5
            x1 = cx + base_radius * 0.3 * math.cos(angle)
            y1 = cy + base_radius * 0.3 * math.sin(angle)
            x2 = cx + base_radius * math.cos(angle + math.pi / 6)
            y2 = cy + base_radius * math.sin(angle + math.pi / 6)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Bright center dot
        center_glow = QRadialGradient(QPointF(cx, cy), 6)
        center_glow.setColorAt(0, QColor(100, 230, 255, 255))
        center_glow.setColorAt(1, QColor(0, 180, 255, 0))
        painter.setBrush(center_glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 6, 6)

        # Tiny orbiting dots
        for i in range(6):
            angle = (i / 6) * 2 * math.pi + self._phase * 2.0
            ox = cx + base_radius * 1.3 * math.cos(angle)
            oy = cy + base_radius * 1.3 * math.sin(angle)
            dot_alpha = int(150 + 50 * math.sin(self._phase * 3 + i))
            painter.setBrush(QColor(0, 200, 255, dot_alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(ox, oy), 2.5, 2.5)

    # ---- Drawing: Particles ----

    def _draw_particles(self, painter, cx, cy):
        """Golden particle swirl — flowing waveform shape with glow and sparkle."""
        dt = 0.033
        self._last_time = time.perf_counter()
        wave_width = 350

        # Spawn new particles along a waveform curve
        for _ in range(6):
            t = random.uniform(0, 1)
            # Waveform position
            wave_x = cx + (t - 0.5) * wave_width
            wave_y = cy + math.sin(t * 8 + self._phase * 4) * 22 * self._amplitude
            # Tight gaussian envelope
            gaussian = math.exp(-((t - 0.5) ** 2) * 6)
            wave_y *= gaussian
            # Spread particles around the waveform
            px = wave_x + random.uniform(-8, 8)
            py = wave_y + random.uniform(-6, 6)
            # Flow angle follows the waveform derivative
            flow_angle = math.cos(t * 8 + self._phase * 4) * 1.2 - math.pi / 2
            p = Particle(px, py, flow_angle=flow_angle)
            self._particles.append(p)

        # Update and draw particles
        alive = []
        for p in self._particles:
            if p.update(dt):
                alive.append(p)
                alpha = int(p.life * 200)
                # Outer glow — large, soft, warm
                glow_size = p.size * 3.0
                glow_color = QColor(p.color[0], p.color[1], p.color[2], alpha // 4)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_color)
                painter.drawEllipse(QPointF(p.x, p.y), glow_size, glow_size)

                # Mid layer — medium, brighter
                mid_size = p.size * 1.5
                mid_alpha = int(alpha * 0.6)
                mid_color = QColor(p.color[0], p.color[1], p.color[2], mid_alpha)
                painter.setBrush(mid_color)
                painter.drawEllipse(QPointF(p.x, p.y), mid_size, mid_size)

                # Core — small, intense, near-white
                core_alpha = alpha
                core_color = QColor(
                    min(255, p.color[0] + 30),
                    min(255, p.color[1] + 40),
                    min(255, p.color[2] + 60),
                    core_alpha,
                )
                painter.setBrush(core_color)
                painter.drawEllipse(QPointF(p.x, p.y), p.size * 0.5, p.size * 0.5)

        self._particles = alive

        # Limit particle count
        if len(self._particles) > 200:
            self._particles = self._particles[-160:]

        # Draw waveform outline (subtle golden line)
        pen = QPen(QColor(255, 210, 80, 90), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        for i in range(60):
            t = i / 60
            x = cx + (t - 0.5) * wave_width
            y = cy + math.sin(t * 8 + self._phase * 4) * 20 * self._amplitude
            gaussian = math.exp(-((t - 0.5) ** 2) * 6)
            y *= gaussian
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)

    # ---- Drawing: Text bubble ----

    def _draw_text_bubble(self, painter, cx, cy, text):
        """Semi-transparent dark bubble with response text."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 18, 25, 210))
        bubble = QRectF(cx - 160, cy - 18, 320, 36)
        painter.drawRoundedRect(bubble, 10, 10)

        # Subtle border glow
        pen = QPen(QColor(255, 200, 60, 60), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bubble, 10, 10)

        painter.setPen(QColor(225, 230, 235))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.drawText(bubble, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    # ---- Animation tick ----

    def _tick(self) -> None:
        # Drain commands from background thread
        for cmd in self.drain_commands():
            if cmd.state:
                if cmd.state != self._state:
                    old_state = self._state
                    self._state = cmd.state
                    self._target_state = cmd.state
                    self._phase = 0.0
                    self._pulse_phase = 0.0
                    self._transition_alpha = 0.0

                    # Activation burst — spawn particles from center on wake
                    if old_state == OverlayState.IDLE:
                        cx = self.rect().center().x()
                        cy = self.rect().bottom() - 35
                        for _ in range(40):
                            p = Particle(cx, cy, burst=True)
                            self._particles.append(p)
                    else:
                        self._particles.clear()

                    # Fade in/out
                    if cmd.state == OverlayState.IDLE:
                        self._fade_out()
                    else:
                        self._fade_in()
            if cmd.text:
                self._text = cmd.text
            if cmd.amplitude != 1.0:
                self._amplitude = cmd.amplitude
            if cmd.shutdown:
                QApplication.quit()
                return

        self._phase += 0.033
        self._pulse_phase += 0.033
        # Ramp up transition alpha for smooth state morphing
        if self._transition_alpha < 1.0:
            self._transition_alpha = min(1.0, self._transition_alpha + self._transition_speed)
        self.update()

    # ---- Fade in/out ----

    def _fade_in(self) -> None:
        self.show()
        from PyQt6.QtCore import QPropertyAnimation
        self._fade_anim = QPropertyAnimation(self, b"fade_opacity")
        self._fade_anim.setDuration(FADE_DURATION)
        self._fade_anim.setStartValue(self._fade_opacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_anim.start()

    def _fade_out(self) -> None:
        from PyQt6.QtCore import QPropertyAnimation
        self._fade_anim = QPropertyAnimation(self, b"fade_opacity")
        self._fade_anim.setDuration(FADE_DURATION)
        self._fade_anim.setStartValue(self._fade_opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    # ---- Position in bottom center ----

    def position_in_center(self) -> None:
        """Position at bottom center of primary screen, above taskbar."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - OVERLAY_WIDTH) // 2
        y = screen.bottom() - OVERLAY_HEIGHT - 50  # Above taskbar
        self.move(x, y)


# ============================================================================
# Module API
# ============================================================================

_overlay: DesktopOverlay | None = None


def get_overlay() -> DesktopOverlay:
    global _overlay
    if _overlay is None:
        _overlay = DesktopOverlay()
    return _overlay


def set_state(state: OverlayState, text: str = "", amplitude: float = 1.0) -> None:
    """Thread-safe state change."""
    DesktopOverlay.push_command(OverlayCommand(state=state, text=text, amplitude=amplitude))


def shutdown() -> None:
    """Request overlay shutdown."""
    DesktopOverlay.push_command(OverlayCommand(shutdown=True))
