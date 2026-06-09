"""Lumi — main GUI application.

Runs as a system tray app with a full settings window.
No terminal window. Double-click tray icon to open settings.
Right-click tray icon for quick actions.
"""
from __future__ import annotations

import io
import sys
import threading
import time
from enum import Enum

import numpy as np

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QAction, QFont, QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QSystemTrayIcon, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget, QCheckBox,
)

from core.config import PROJECT_ROOT, load_config, CONFIG_PATH
from core import executor
from core.llm import LLMClient, LLMError
from core.stt import STT
from core.tts import TTS
from core.wake_word import WakeWordDetector


class State(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    RESPONDING = "responding"
    ERROR = "error"


PROVIDERS = {
    "HackClub (Free)": {"base_url": "https://ai.hackclub.com/proxy/v1", "model": "openrouter/free", "link": "https://ai.hackclub.com/"},
    "OpenRouter": {"base_url": "https://openrouter.ai/api/v1", "model": "openrouter/auto", "link": "https://openrouter.ai/"},
    "OpenAI": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o", "link": "https://openai.com/"},
    "Anthropic (Claude)": {"base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-20250514", "link": "https://anthropic.com/"},
    "Google (Gemini)": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.5-pro", "link": "https://ai.google.dev/"},
}


def _make_icon(color: str) -> QIcon:
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = {
        "grey": (150, 150, 150, 255),
        "blue": (0, 180, 255, 255),
        "red": (255, 60, 60, 255),
        "purple": (124, 58, 237, 255),
        "green": (0, 220, 150, 255),
    }
    fill = colors.get(color, (150, 150, 150, 255))

    # Dark rounded background
    draw.rounded_rectangle([2, 2, 46, 46], radius=8, fill=(26, 26, 46, 220), outline=fill, width=2)

    # Golden waveform burst
    cx, cy = 24, 22
    rays = [(0, -14, 0, 10), (0, 10, 0, 6), (-12, 0, 8, 0), (8, 0, 6, 0),
            (-8, -8, 5, 5), (5, -8, 4, 4), (-8, 8, 5, 5), (5, 8, 4, 4)]
    for i, (x1, y1, x2, y2) in enumerate(rays):
        c = (240, 165, 0) if i % 2 == 0 else (200, 140, 0)
        draw.line([cx + x1, cy + y1, cx + x2, cy + y2], fill=c, width=2)
    draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=(240, 165, 0))

    from PyQt6.QtCore import QByteArray
    buf = io.BytesIO()
    img.save(buf, "PNG")
    pm = QPixmap()
    pm.loadFromData(QByteArray(buf.getvalue()))
    return QIcon(pm)


class VoiceEngine:
    def __init__(self, on_state_change, on_transcript, on_response):
        self.on_state_change = on_state_change
        self.on_transcript = on_transcript
        self.on_response = on_response
        self._stop = threading.Event()
        self._thread = None
        self._config = None

    def start(self, config: dict):
        self._config = config
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        cfg = self._config
        det = WakeWordDetector(cfg, verbose=False)
        det.start()
        stt = STT(cfg, verbose=False)
        llm = LLMClient(cfg)
        tts = TTS(cfg, verbose=False)
        self.on_state_change(State.IDLE)
        turn = 0
        while not self._stop.is_set():
            fired = det.wait(timeout=0.5)
            if not fired or self._stop.is_set():
                continue
            turn += 1
            det.pause()
            try:
                try:
                    import sounddevice as sd
                    t = np.linspace(0, 0.10, 2205, endpoint=False)
                    tone = (0.20 * np.sin(2 * np.pi * 760 * t) + 0.10 * np.sin(2 * np.pi * 1140 * t)).astype(np.float32)
                    sd.play(tone, 22050)
                except:
                    pass
                self.on_state_change(State.LISTENING)
                audio = stt.record_until_silence(show_meter=False)
                if audio.size == 0:
                    continue
                user_text, info = stt.transcribe(audio)
                self.on_transcript(user_text)
                if not user_text.strip() or len(user_text.split()) <= 1:
                    self.on_state_change(State.IDLE)
                    continue
                self.on_state_change(State.THINKING)
                full_reply = []
                tool_schemas = executor.get_schemas()
                def teed_stream():
                    for tok in llm.stream(user_text, pc_context=f"Current time: {time.strftime('%A, %B %d %Y, %H:%M:%S')}", tools=tool_schemas):
                        full_reply.append(tok)
                        yield tok
                self.on_state_change(State.RESPONDING)
                try:
                    tts.speak_token_stream(teed_stream())
                except LLMError:
                    tts.speak("Sorry, I lost contact with my brain.")
                    self.on_state_change(State.ERROR)
                    time.sleep(2)
                self.on_response("".join(full_reply))
                self.on_state_change(State.IDLE)
                time.sleep(0.35)
            finally:
                det.resume()
        det.stop()


class SettingsWindow(QMainWindow):
    def __init__(self, engine: VoiceEngine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("Lumi — Settings")
        self.setMinimumSize(600, 500)
        self.resize(650, 550)
        try:
            self.setWindowIcon(_make_icon("grey"))
        except:
            pass

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { background: #2d2d2d; color: #ccc; padding: 8px 16px; border: none; border-bottom: 2px solid #444; } QTabBar::tab:selected { background: #1a1a2e; color: #f0a500; border-bottom: 2px solid #f0a500; } QTabWidget::pane { border: 1px solid #444; }")
        layout.addWidget(tabs)

        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_voice_tab(), "Voice")
        self.log_tab = self._build_log_tab()
        tabs.addTab(self.log_tab, "Activity")

        self.status_label = QLabel("Lumi is idle")
        self.status_label.setStyleSheet("color: #888; padding: 4px;")
        layout.addWidget(self.status_label)

        try:
            cfg = load_config()
            self._load_config(cfg)
        except:
            pass

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setStyleSheet("QLabel { color: #ddd; } QLineEdit { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; } QComboBox { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; }")

        self.provider_combo = QComboBox()
        for name in PROVIDERS:
            self.provider_combo.addItem(name)
        self.provider_combo.addItem("Custom")
        layout.addRow("Provider:", self.provider_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        layout.addRow("API Key:", self.api_key_edit)

        self.api_hint = QLabel('<a href="https://ai.hackclub.com/" style="color: #f0a500;">Get your free API key at ai.hackclub.com</a>')
        self.api_hint.setOpenExternalLinks(True)
        layout.addRow("", self.api_hint)

        self.custom_model_label = QLabel("Model name:")
        self.custom_model_label.setVisible(False)
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("e.g. gpt-4o")
        self.custom_model_edit.setVisible(False)
        layout.addRow(self.custom_model_label, self.custom_model_edit)

        self.custom_url_label = QLabel("Base URL:")
        self.custom_url_label.setVisible(False)
        self.custom_url_edit = QLineEdit()
        self.custom_url_edit.setPlaceholderText("https://api.example.com/v1")
        self.custom_url_edit.setVisible(False)
        layout.addRow(self.custom_url_label, self.custom_url_edit)

        self.provider_combo.currentTextChanged.connect(self._on_provider_change)

        layout.addRow("", QFrame())

        self.wake_word_edit = QLineEdit()
        self.wake_word_edit.setPlaceholderText("hey lumi")
        layout.addRow("Wake word:", self.wake_word_edit)

        self.sensitivity_spin = QDoubleSpinBox()
        self.sensitivity_spin.setRange(0.1, 0.99)
        self.sensitivity_spin.setSingleStep(0.05)
        layout.addRow("Sensitivity:", self.sensitivity_spin)

        layout.addRow("", QLabel())

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("QPushButton { background: #f0a500; color: #1a1a2e; border: none; border-radius: 6px; padding: 8px; font-weight: bold; } QPushButton:hover { background: #ffb722; }")
        save_btn.clicked.connect(self._save_config)
        layout.addRow("", save_btn)

        return w

    def _build_voice_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setStyleSheet("QLabel { color: #ddd; } QComboBox { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; } QDoubleSpinBox { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; }")

        self.voice_combo = QComboBox()
        for val, label in [("en_GB-southern_english_female-low", "British Female (Southern)"), ("en_US-amy-medium", "American Female (Amy)"), ("en_GB-jenny_dioco-medium", "British Female (Jenny)"), ("en_US-lessac-medium", "American Female (Lessac)")]:
            self.voice_combo.addItem(label, val)
        layout.addRow("Voice:", self.voice_combo)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setSingleStep(0.1)
        layout.addRow("Speed:", self.speed_spin)

        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems(["large-v3", "large-v3-turbo", "medium", "small"])
        layout.addRow("STT Model:", self.stt_model_combo)

        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"])
        layout.addRow("STT Device:", self.device_combo)

        layout.addRow("", QLabel())

        test_btn = QPushButton("Test Voice")
        test_btn.setStyleSheet("QPushButton { background: #f0a500; color: #1a1a2e; border: none; border-radius: 6px; padding: 8px; font-weight: bold; } QPushButton:hover { background: #ffb722; }")
        test_btn.clicked.connect(self._test_voice)
        layout.addRow("", test_btn)

        return w

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("background: #1a1a2e; color: #ccc; border: none; border-radius: 4px;")
        layout.addWidget(self.log_text)
        clear_btn = QPushButton("Clear Log")
        clear_btn.setStyleSheet("QPushButton { background: #555; color: white; border: none; border-radius: 6px; padding: 8px; } QPushButton:hover { background: #666; }")
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)
        return w

    def _on_provider_change(self, provider: str):
        is_custom = provider == "Custom"
        self.custom_model_label.setVisible(is_custom)
        self.custom_model_edit.setVisible(is_custom)
        self.custom_url_label.setVisible(is_custom)
        self.custom_url_edit.setVisible(is_custom)
        prov = PROVIDERS.get(provider)
        if prov and not is_custom:
            self.api_hint.setText(f'<a href="{prov["link"]}" style="color: #f0a500;">{provider} docs</a>')
            self.api_hint.setVisible(True)
        elif is_custom:
            self.api_hint.setVisible(False)
        else:
            self.api_hint.setVisible(False)

    def _load_config(self, cfg: dict):
        jarvis = cfg.get("lumi", cfg.get("jarvis", {}))
        self.wake_word_edit.setText(jarvis.get("wake_word", "hey lumi"))
        self.sensitivity_spin.setValue(float(jarvis.get("wake_word_sensitivity", 0.7)))
        stt = cfg.get("stt", {})
        self.stt_model_combo.setCurrentText(stt.get("model", "large-v3"))
        self.device_combo.setCurrentText(stt.get("device", "cuda"))
        tts = cfg.get("tts", {})
        idx = self.voice_combo.findText(tts.get("voice", "en_GB-southern_english_female-low"))
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        self.speed_spin.setValue(float(tts.get("speed", 1.0)))
        llm = cfg.get("llm", {})
        base_url = llm.get("base_url", "")
        for name, prov in PROVIDERS.items():
            if prov["base_url"] == base_url:
                self.provider_combo.setCurrentText(name)
                break
        try:
            from dotenv import dotenv_values
            env = dotenv_values(str(PROJECT_ROOT / ".env"))
            for key in env:
                if key.endswith("_API_KEY"):
                    self.api_key_edit.setText(env[key])
                    break
        except:
            pass

    def _save_config(self):
        import yaml
        cfg = load_config()
        section = "lumi" if "lumi" in cfg else "jarvis"
        cfg[section]["wake_word"] = self.wake_word_edit.text()
        cfg[section]["wake_word_sensitivity"] = self.sensitivity_spin.value()
        cfg["stt"]["model"] = self.stt_model_combo.currentText()
        cfg["stt"]["device"] = self.device_combo.currentText()
        cfg["tts"]["voice"] = self.voice_combo.currentText()
        cfg["tts"]["speed"] = self.speed_spin.value()

        provider = self.provider_combo.currentText()
        prov = PROVIDERS.get(provider)
        model = self.custom_model_edit.text().strip() if provider == "Custom" else (prov["model"] if prov else "")
        base_url = self.custom_url_edit.text().strip() if provider == "Custom" else (prov["base_url"] if prov else "")
        cfg["llm"]["model"] = model
        cfg["llm"]["base_url"] = base_url

        with open(CONFIG_PATH, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False)

        env_path = PROJECT_ROOT / ".env"
        api_key = self.api_key_edit.text().strip()
        if api_key:
            env_key = "CUSTOM_API_KEY" if provider == "Custom" else (PROVIDERS.get(provider, {}).get("api_key_env", "HACKCLUB_API_KEY") if prov else "HACKCLUB_API_KEY")
            env_path.write_text(f"{env_key}={api_key}\n", encoding="utf-8")

        QMessageBox.information(self, "Saved", "Settings saved. Restart Lumi for changes to take effect.")

    def _test_voice(self):
        try:
            tts = TTS(verbose=False)
            tts.speak("Hello, this is a voice test.", blocking=False)
            self.log_append("Voice test playing...")
        except Exception as e:
            self.log_append(f"Voice test failed: {e}")

    def log_append(self, text: str):
        self.log_text.append(text)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)


class LumiApp:
    def __init__(self):
        self._app = QApplication.instance() or QApplication([])
        self._app.setStyle("Fusion")
        self._app.setStyleSheet("QToolTip { background: #1a1a2e; color: #f0a500; border: 1px solid #444; padding: 4px; }")
        self._state = State.IDLE
        self._tray = None
        self._window = None
        self._engine = None
        self._setup_tray()
        self._start_engine()

    def _setup_tray(self):
        menu = _build_tray_menu(self._on_open_settings, self._on_quit)
        self._tray = QSystemTrayIcon(_make_icon("grey"), self._app)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip("Lumi — Voice Assistant")
        self._tray.activated.connect(self._on_tray_click)
        self._tray.show()

    def _start_engine(self):
        self._engine = VoiceEngine(on_state_change=self._on_state, on_transcript=self._on_transcript, on_response=self._on_response)
        try:
            cfg = load_config()
            self._engine.start(cfg)
        except Exception as e:
            self._tray.showMessage("Lumi Error", str(e)[:200], QSystemTrayIcon.MessageIcon.Critical)

    def _on_state(self, state: State):
        self._state = state
        color_map = {State.IDLE: "grey", State.LISTENING: "red", State.THINKING: "purple", State.RESPONDING: "green", State.ERROR: "red"}
        self._tray.setIcon(_make_icon(color_map.get(state, "grey")))
        if self._window:
            self._window.status_label.setText(f"Lumi is {state.value}")
            if hasattr(self._window, "log_text"):
                self._window.log_append(f"[{time.strftime('%H:%M:%S')}] State: {state.value}")

    def _on_transcript(self, text: str):
        if self._window and hasattr(self._window, "log_text"):
            self._window.log_append(f"You: {text}")

    def _on_response(self, text: str):
        if self._window and hasattr(self._window, "log_text"):
            self._window.log_append(f"Lumi: {text[:200]}{'...' if len(text) > 200 else ''}")

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_open_settings()

    def _on_open_settings(self):
        if self._window is None:
            self._window = SettingsWindow(self._engine)
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _on_quit(self):
        if self._engine:
            self._engine.stop()
        self._tray.hide()
        self._app.quit()

    def run(self):
        return self._app.exec()


def _build_tray_menu(on_settings, on_quit):
    from PyQt6.QtWidgets import QMenu
    menu = QMenu()
    status = QAction("Lumi — Idle", menu)
    status.setEnabled(False)
    menu.addAction(status)
    menu.addSeparator()
    settings = QAction("Settings...", menu)
    settings.triggered.connect(on_settings)
    menu.addAction(settings)
    menu.addSeparator()
    quit_action = QAction("Quit Lumi", menu)
    quit_action.triggered.connect(on_quit)
    menu.addAction(quit_action)
    return menu


def main():
    app = LumiApp()
    raise SystemExit(app.run())


if __name__ == "__main__":
    main()
