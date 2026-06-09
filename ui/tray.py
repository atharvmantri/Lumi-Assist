"""Lumi system tray + desktop overlay (pure PyQt6).

Lumi integrates with Windows via:
  - System tray icon (changes color based on state)
  - Bottom-center desktop overlay with animated particles
  - Windows toast notifications (for wake word, errors)

No floating windows. No overlays that block your work. Lumi lives in the
tray and feels like part of Windows, not a separate app.

Uses pure PyQt6 — no pystray conflicts with Qt event loop.

States:
  idle         → invisible overlay + grey mic icon in tray
  listening    → golden waveform at bottom center + red tray icon
  thinking     → blue glowing orb at bottom center + purple tray icon
  responding   → golden particle swirl + response text + green tray icon
  error        → toast notification + red tray icon

Thread-safe: commands pushed via queue from background thread.
"""
from __future__ import annotations

import io
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.config import PROJECT_ROOT


class TrayState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    RESPONDING = "responding"
    ERROR = "error"


@dataclass
class TrayCommand:
    """Thread-safe command from background thread → tray."""
    state: TrayState | None = None
    text: str = ""
    show_toast: bool = False
    shutdown: bool = False


# Generate simple colored icons for each state
_ICONS = {}


def _make_icon(color: str) -> bytes:
    """Create a 48x48 PNG icon with a circular mic symbol and waveform bars."""
    from PIL import Image, ImageDraw

    size = 48
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color_map = {
        "grey": (150, 150, 150, 255),
        "blue": (0, 180, 255, 255),
        "red": (255, 60, 60, 255),
        "purple": (124, 58, 237, 255),
        "green": (0, 220, 150, 255),
    }
    fill = color_map.get(color, (150, 150, 150, 255))

    # Background circle (slightly translucent)
    bg_color = (fill[0], fill[1], fill[2], 40)
    draw.ellipse([2, 2, size - 2, size - 2], fill=bg_color, outline=fill, width=2)

    # Microphone symbol
    cx, cy = size // 2, size // 2 - 2
    # Mic head (ellipse)
    draw.ellipse([cx - 8, cy - 12, cx + 8, cy + 4], fill=fill)
    # Mic stem
    draw.rectangle([cx - 2, cy + 4, cx + 2, cy + 12], fill=fill)
    # Mic base (arc)
    draw.arc([cx - 10, cy + 8, cx + 10, cy + 18], 0, 180, fill=fill, width=3)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _init_icons() -> None:
    global _ICONS
    _ICONS = {
        TrayState.IDLE: _make_icon("grey"),
        TrayState.LISTENING: _make_icon("red"),
        TrayState.THINKING: _make_icon("purple"),
        TrayState.RESPONDING: _make_icon("green"),
        TrayState.ERROR: _make_icon("red"),
    }


# Lazy overlay import
_overlay_module = None

def _get_overlay_module():
    global _overlay_module
    if _overlay_module is None:
        from ui import overlay as _overlay_module
    return _overlay_module


class TrayManager:
    """System tray icon + desktop overlay + Windows toast notifications.
    Pure PyQt6 implementation — no pystray conflicts."""

    _command_queue: queue.Queue[TrayCommand] = queue.Queue()
    _shutdown_event = threading.Event()
    _current_state: TrayState = TrayState.IDLE

    def __init__(self):
        _init_icons()
        self._tray_icon = None
        self._toaster = None
        self._app = None

    @classmethod
    def push_command(cls, cmd: TrayCommand) -> None:
        if cmd.shutdown:
            cls._shutdown_event.set()
        try:
            cls._command_queue.put_nowait(cmd)
        except queue.Full:
            pass

    @classmethod
    def drain_commands(cls) -> list[TrayCommand]:
        out: list[TrayCommand] = []
        while True:
            try:
                out.append(cls._command_queue.get_nowait())
            except queue.Empty:
                break
        return out

    def _send_toast(self, title: str, message: str, duration: int = 3) -> None:
        """Show a Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            if self._toaster is None:
                self._toaster = ToastNotifier()
            self._toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=True,
                icon_path=None,
            )
        except Exception:
            pass

    def _update_icon(self, state: TrayState) -> None:
        """Update the tray icon to match the current state."""
        if self._tray_icon is None:
            return
        from PyQt6.QtGui import QIcon
        import io
        from PIL import Image
        icon_bytes = _ICONS.get(state, _ICONS[TrayState.IDLE])
        icon_img = Image.open(io.BytesIO(icon_bytes))
        # Convert PIL Image to QPixmap
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import QByteArray
        data = QByteArray(icon_bytes)
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._tray_icon.setIcon(QIcon(pixmap))

    def _update_overlay(self, state: TrayState, text: str = "") -> None:
        """Update the desktop overlay to match the current state."""
        overlay_mod = _get_overlay_module()
        overlay_mod.set_state(
            overlay_mod.OverlayState(state.value),
            text,
        )

    def run(self) -> None:
        """Run the tray event loop in the main thread using pure PyQt6."""
        # Create QApplication for Qt widgets
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtCore import QByteArray

        self._app = QApplication.instance() or QApplication([])

        # Initialize the overlay
        overlay_mod = _get_overlay_module()
        overlay = overlay_mod.get_overlay()
        overlay.position_in_center()
        overlay.show()
        overlay.setWindowOpacity(0.0)

        # Create system tray icon
        icon_bytes = _ICONS[TrayState.IDLE]
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(icon_bytes))
        self._tray_icon = QSystemTrayIcon(QIcon(pixmap), self._app)
        self._tray_icon.setToolTip("Lumi — Voice Assistant")

        # Create menu
        menu = QMenu()

        # Status label (not clickable)
        status_action = menu.addAction("Lumi — Idle")
        status_action.setEnabled(False)

        menu.addSeparator()

        # Quick actions
        test_action = menu.addAction("Test Overlay")
        test_action.triggered.connect(lambda: self._test_overlay_cycle())

        menu.addSeparator()

        quit_action = menu.addAction("Quit Lumi")
        quit_action.triggered.connect(self._app.quit)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.show()

        # Store reference for status updates
        self._status_action = status_action

        # Timer to process commands at ~10 Hz
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(self._process_commands)
        timer.start(100)

        # Run Qt event loop
        try:
            self._app.exec()
        except KeyboardInterrupt:
            pass
        finally:
            overlay.hide()
            self._tray_icon.hide()

    def _test_overlay_cycle(self) -> None:
        """Cycle through all overlay states for a quick visual test."""
        overlay_mod = _get_overlay_module()
        states = [
            (overlay_mod.OverlayState.LISTENING, "Listening...", 2.0),
            (overlay_mod.OverlayState.THINKING, "Thinking...", 2.0),
            (overlay_mod.OverlayState.RESPONDING, "Hello! I'm Lumi.", 3.0),
            (overlay_mod.OverlayState.IDLE, "", 0),
        ]

        import threading
        def _cycle():
            for state, text, wait in states:
                overlay_mod.set_state(state, text)
                if wait > 0:
                    time.sleep(wait)
        t = threading.Thread(target=_cycle, daemon=True)
        t.start()

    def _process_commands(self) -> None:
        """Process pending commands from background thread."""
        for cmd in self.drain_commands():
            if cmd.state:
                self._current_state = cmd.state
                self._update_icon(cmd.state)
                self._update_overlay(cmd.state, cmd.text)
                # Update tray menu status label
                if hasattr(self, "_status_action"):
                    label = f"Lumi — {cmd.state.value.title()}"
                    if cmd.text:
                        label += f": {cmd.text[:30]}"
                    self._status_action.setText(label)
            if cmd.show_toast and cmd.text:
                title = "Lumi"
                if cmd.state == TrayState.LISTENING:
                    title = "Wake Word Detected"
                elif cmd.state == TrayState.ERROR:
                    title = "Error"
                self._send_toast(title, cmd.text)
            if cmd.shutdown:
                self._app.quit()
                return


# Module-level instance
_tray: TrayManager | None = None


def get_tray() -> TrayManager:
    global _tray
    if _tray is None:
        _tray = TrayManager()
    return _tray


def run_tray() -> None:
    """Start the tray manager in the current thread."""
    get_tray().run()


def set_state(state: TrayState, text: str = "", show_toast: bool = False) -> None:
    """Thread-safe state change."""
    TrayManager.push_command(TrayCommand(state=state, text=text, show_toast=show_toast))


def shutdown() -> None:
    """Request tray shutdown."""
    TrayManager.push_command(TrayCommand(shutdown=True))
