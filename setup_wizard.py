"""Lumi Setup Wizard — interactive GUI installer."""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget, QGroupBox, QFormLayout, QRadioButton,
    QButtonGroup, QTextEdit, QCheckBox,
)

INSTALL_DIR = Path(os.environ.get("USERPROFILE", ".")) / "Lumi"


# Provider templates
PROVIDERS = {
    "HackClub (Free)": {
        "api_key_env": "HACKCLUB_API_KEY",
        "model": "openrouter/free",
        "base_url": "https://ai.hackclub.com/proxy/v1",
        "link": "https://ai.hackclub.com/",
        "link_text": "Get your free API key at ai.hackclub.com",
    },
    "OpenRouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "openrouter/auto",
        "base_url": "https://openrouter.ai/api/v1",
        "link": "https://openrouter.ai/keys",
        "link_text": "Get your key at openrouter.ai",
    },
    "OpenAI": {
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "link": "https://platform.openai.com/api-keys",
        "link_text": "Get your key at platform.openai.com",
    },
    "Anthropic (Claude)": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-20250514",
        "base_url": "https://api.anthropic.com/v1",
        "link": "https://console.anthropic.com/settings/keys",
        "link_text": "Get your key at console.anthropic.com",
    },
    "Google (Gemini)": {
        "api_key_env": "GOOGLE_API_KEY",
        "model": "gemini-2.5-pro",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "link": "https://aistudio.google.com/apikey",
        "link_text": "Get your key at aistudio.google.com",
    },
    "Custom": {
        "api_key_env": "CUSTOM_API_KEY",
        "model": "",
        "base_url": "",
        "link": "",
        "link_text": "",
    },
}


def _check_python() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["py", "-3.11", "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "Python 3.11 not found"
    except FileNotFoundError:
        return False, "Python launcher not found. Install Python 3.11 from python.org"


def _install_python() -> bool:
    try:
        result = subprocess.run(
            ["winget", "install", "--id", "Python.Python.3.11", "--silent",
             "--accept-source-agreements", "--accept-package-agreements", "--scope", "user"],
            capture_output=True, text=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _clone_repo() -> tuple[bool, str]:
    if INSTALL_DIR.exists():
        try:
            subprocess.run(
                ["git", "-C", str(INSTALL_DIR), "pull", "--quiet"],
                capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True, "Updated existing installation"
        except:
            pass
    try:
        subprocess.run(
            ["git", "clone", "--quiet", "https://github.com/atharvmantri/Lumi-Assist.git", str(INSTALL_DIR)],
            capture_output=True, text=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True, "Cloned to " + str(INSTALL_DIR)
    except Exception as e:
        return False, str(e)


def _setup_venv() -> tuple[bool, str]:
    venv_py = INSTALL_DIR / "venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        try:
            subprocess.run(
                ["py", "-3.11", "-m", "venv", "venv"],
                capture_output=True, text=True, timeout=60,
                cwd=str(INSTALL_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            return False, f"venv creation failed: {e}"
    try:
        result = subprocess.run(
            [str(venv_py), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            capture_output=True, text=True, timeout=600,
            cwd=str(INSTALL_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return False, f"pip install failed: {result.stderr[:200]}"
    except Exception as e:
        return False, str(e)
    return True, "Dependencies installed"


def _download_voice(voice: str) -> tuple[bool, str]:
    voice_dir = INSTALL_DIR / "models" / "piper"
    voice_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = voice_dir / f"{voice}.onnx"
    if onnx_path.exists():
        return True, "Voice already downloaded"
    venv_py = INSTALL_DIR / "venv" / "Scripts" / "python.exe"
    try:
        subprocess.run(
            [str(venv_py), "-m", "pip", "install", "-q", "huggingface-hub"],
            capture_output=True, text=True, timeout=60,
            cwd=str(INSTALL_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for ext in [".onnx", ".onnx.json"]:
            subprocess.run(
                [str(venv_py), "-c",
                 f"from huggingface_hub import hf_hub_download; "
                 f"hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/{voice}{ext}', "
                 f"local_dir='{voice_dir}', repo_type='model')"],
                capture_output=True, text=True, timeout=300,
                cwd=str(INSTALL_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        return True, "Voice model downloaded"
    except Exception as e:
        return False, str(e)


def _save_config(api_key: str, provider_name: str, voice: str, stt_model: str, device: str, sensitivity: float, speed: float, custom_model: str = "", custom_url: str = ""):
    import yaml

    provider = PROVIDERS.get(provider_name, PROVIDERS["HackClub (Free)"])
    env_var = provider["api_key_env"]
    model = custom_model if provider_name == "Custom" else provider["model"]
    base_url = custom_url if provider_name == "Custom" else provider["base_url"]

    config = {
        "lumi": {
            "wake_word": "hey lumi",
            "wake_word_sensitivity": sensitivity,
        },
        "stt": {
            "model": stt_model,
            "device": device,
            "compute_type": "float16" if device == "cuda" else "int8",
            "silence_threshold_ms": 1500,
            "language": None,
        },
        "llm": {
            "provider": provider_name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "api_key_env": env_var,
            "model": model,
            "base_url": base_url,
            "max_tokens": 2048,
            "temperature": 0.7,
            "system_prompt_path": "prompts/system.md",
            "history_turns": 20,
        },
        "tts": {
            "engine": "piper",
            "voice": voice,
            "device": "cpu",
            "speed": speed,
        },
        "ui": {
            "theme": "dark",
            "opacity": 0.88,
            "always_on_top": True,
            "show_transcript": True,
            "window_position": [80, 80],
        },
        "audio": {
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 16000,
        },
    }

    config_path = INSTALL_DIR / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    env_path = INSTALL_DIR / ".env"
    env_path.write_text(f"{env_var}={api_key}\n", encoding="utf-8")

    for d in ["data/conversations", "logs/learning", "logs/screenshots"]:
        (INSTALL_DIR / d).mkdir(parents=True, exist_ok=True)


def _create_shortcut():
    try:
        import win32com.client
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, "Lumi.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = str(INSTALL_DIR / "venv" / "Scripts" / "pythonw.exe")
        shortcut.Arguments = "lumi_app.py"
        shortcut.WorkingDirectory = str(INSTALL_DIR)
        shortcut.WindowStyle = 1
        shortcut.Save()
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "Lumi shortcut created on your desktop!", "Lumi Setup", 0x40)
    except Exception:
        pass


class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, api_key: str, provider: str, voice: str, stt_model: str, device: str, sensitivity: float, speed: float, custom_model: str = "", custom_url: str = ""):
        super().__init__()
        self.api_key = api_key
        self.provider = provider
        self.voice = voice
        self.stt_model = stt_model
        self.device = device
        self.sensitivity = sensitivity
        self.speed = speed
        self.custom_model = custom_model
        self.custom_url = custom_url

    def run(self):
        try:
            self.progress.emit(5, "Checking Python...")
            has_py, msg = _check_python()
            if not has_py:
                self.progress.emit(10, "Installing Python 3.11...")
                if not _install_python():
                    self.finished.emit(False, "Python 3.11 installation failed. Install manually from python.org")
                    return

            self.progress.emit(15, "Downloading Lumi...")
            ok, msg = _clone_repo()
            if not ok:
                self.finished.emit(False, f"Clone failed: {msg}")
                return

            self.progress.emit(30, "Installing dependencies...")
            ok, msg = _setup_venv()
            if not ok:
                self.finished.emit(False, f"Dependency install failed: {msg}")
                return

            self.progress.emit(70, f"Downloading voice model ({self.voice})...")
            ok, msg = _download_voice(self.voice)
            if not ok:
                self.progress.emit(75, f"Voice download failed (will retry on first run): {msg}")

            self.progress.emit(90, "Saving configuration...")
            _save_config(self.api_key, self.provider, self.voice, self.stt_model, self.device, self.sensitivity, self.speed, self.custom_model, self.custom_url)

            self.progress.emit(95, "Creating desktop shortcut...")
            _create_shortcut()

            self.progress.emit(100, "Done!")
            self.finished.emit(True, "Lumi is ready! Double-click the Lumi icon on your desktop to start.")

        except Exception as e:
            self.finished.emit(False, f"Setup failed: {e}")


class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addStretch()

        # Logo
        try:
            logo_pixmap = _create_logo_pixmap(180)
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
            layout.addSpacing(10)
        except:
            pass

        title = QLabel("Lumi Setup")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Your always-on AI voice assistant for Windows")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        features = QLabel(
            "• Voice-controlled — say \"hey lumi\" and talk\n"
            "• 260+ built-in tools — apps, files, web, media\n"
            "• Runs locally on your PC\n"
            "• Bottom-center animated overlay"
        )
        features.setFont(QFont("Segoe UI", 12))
        features.setStyleSheet("color: #aaa; line-height: 1.8;")
        layout.addWidget(features, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.next_btn = QPushButton("Next")
        self.next_btn.setMinimumHeight(40)
        self.next_btn.setFont(QFont("Segoe UI", 12))
        self.next_btn.setStyleSheet(
            "QPushButton { background: #f0a500; color: #1a1a2e; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }"
            "QPushButton:hover { background: #ffb722; }"
        )
        layout.addWidget(self.next_btn)
        layout.addSpacing(20)


class ConfigPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Configure Lumi")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0a500;")
        layout.addWidget(title)
        layout.addSpacing(15)

        form = QFormLayout()

        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumHeight(32)
        for name in PROVIDERS:
            self.provider_combo.addItem(name)
        form.addRow("Provider:", self.provider_combo)

        # API key
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("Enter your API key...")
        self.api_key.setMinimumHeight(32)
        self.api_key.setStyleSheet("QLineEdit { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; }")
        form.addRow("API Key:", self.api_key)

        self.api_hint = QLabel('<a href="https://ai.hackclub.com/" style="color: #f0a500;">Get your free API key at ai.hackclub.com</a>')
        self.api_hint.setOpenExternalLinks(True)
        form.addRow("", self.api_hint)

        # Custom model / URL (hidden by default)
        self.custom_model_label = QLabel("Model name:")
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("e.g. claude-sonnet-4-20250514")
        self.custom_model_edit.setMinimumHeight(32)
        self.custom_model_edit.setStyleSheet("QLineEdit { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; }")

        self.custom_url_label = QLabel("Base URL:")
        self.custom_url_edit = QLineEdit()
        self.custom_url_edit.setPlaceholderText("https://api.example.com/v1")
        self.custom_url_edit.setMinimumHeight(32)
        self.custom_url_edit.setStyleSheet("QLineEdit { background: #2d2d2d; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px; }")

        self.custom_model_label.setVisible(False)
        self.custom_model_edit.setVisible(False)
        self.custom_url_label.setVisible(False)
        self.custom_url_edit.setVisible(False)

        form.addRow(self.custom_model_label, self.custom_model_edit)
        form.addRow(self.custom_url_label, self.custom_url_edit)

        form.addRow("", QFrame())

        # Voice
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumHeight(32)
        for val, label in [
            ("en_GB-southern_english_female-low", "British Female (Southern)"),
            ("en_US-amy-medium", "American Female (Amy)"),
            ("en_GB-jenny_dioco-medium", "British Female (Jenny)"),
            ("en_US-lessac-medium", "American Female (Lessac)"),
        ]:
            self.voice_combo.addItem(label, val)
        form.addRow("Voice:", self.voice_combo)

        self.stt_combo = QComboBox()
        self.stt_combo.setMinimumHeight(32)
        self.stt_combo.addItems(["large-v3 (best accuracy)", "large-v3-turbo (faster)", "medium (balanced)"])
        form.addRow("Speech Recognition:", self.stt_combo)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(32)
        self.device_combo.addItems(["Auto (GPU if available)", "CPU only"])
        form.addRow("Compute:", self.device_combo)

        self.sensitivity = QComboBox()
        self.sensitivity.setMinimumHeight(32)
        self.sensitivity.addItems(["Low (fewer false triggers)", "Normal (recommended)", "High (very sensitive)"])
        self.sensitivity.setCurrentIndex(1)
        form.addRow("Wake Sensitivity:", self.sensitivity)

        layout.addLayout(form)
        layout.addStretch()

        nav = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setStyleSheet(
            "QPushButton { background: #555; color: white; border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background: #666; }"
        )
        nav.addWidget(self.back_btn)

        self.next_btn = QPushButton("Install")
        self.next_btn.setMinimumHeight(40)
        self.next_btn.setFont(QFont("Segoe UI", 12))
        self.next_btn.setStyleSheet(
            "QPushButton { background: #f0a500; color: #1a1a2e; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }"
            "QPushButton:hover { background: #ffb722; }"
        )
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)
        layout.addSpacing(10)

        # Connect provider change to show/hide custom fields
        self.provider_combo.currentTextChanged.connect(self._on_provider_change)

    def _on_provider_change(self, provider: str):
        is_custom = provider == "Custom"
        self.custom_model_label.setVisible(is_custom)
        self.custom_model_edit.setVisible(is_custom)
        self.custom_url_label.setVisible(is_custom)
        self.custom_url_edit.setVisible(is_custom)

        # Update hint link
        prov = PROVIDERS.get(provider, PROVIDERS["HackClub (Free)"])
        if prov["link"]:
            self.api_hint.setText(f'<a href="{prov["link"]}" style="color: #f0a500;">{prov["link_text"]}</a>')
            self.api_hint.setVisible(True)
            self.api_key.setPlaceholderText(f"Enter your {provider} API key...")
        else:
            self.api_hint.setVisible(False)
            self.api_key.setPlaceholderText("Enter your API key...")


class ProgressPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Installing Lumi")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0a500;")
        layout.addWidget(title)
        layout.addSpacing(15)

        self.progress = QProgressBar()
        self.progress.setMinimumHeight(8)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; background: #333; border-radius: 4px; }
            QProgressBar::chunk { background: #f0a500; border-radius: 4px; }
        """)
        layout.addWidget(self.progress)

        self.status = QLabel("Starting...")
        self.status.setFont(QFont("Segoe UI", 11))
        self.status.setStyleSheet("color: #aaa;")
        layout.addWidget(self.status)

        layout.addStretch()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setStyleSheet("background: #1a1a2e; color: #ccc; border: none; border-radius: 4px;")
        layout.addWidget(self.log)

        layout.addSpacing(10)
        self.finish_btn = QPushButton("Launch Lumi")
        self.finish_btn.setMinimumHeight(40)
        self.finish_btn.setFont(QFont("Segoe UI", 12))
        self.finish_btn.setStyleSheet(
            "QPushButton { background: #f0a500; color: #1a1a2e; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }"
            "QPushButton:hover { background: #ffb722; }"
        )
        self.finish_btn.setVisible(False)
        layout.addWidget(self.finish_btn)
        layout.addSpacing(10)


class SetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumi Setup")
        self.setMinimumSize(500, 480)
        self.resize(550, 520)

        # Try to set icon
        try:
            from PIL import Image, ImageDraw
            icon = _create_lumi_icon()
            self.setWindowIcon(icon)
        except:
            pass

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome = WelcomePage()
        self.config = ConfigPage()
        self.progress = ProgressPage()

        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.config)
        self.stack.addWidget(self.progress)

        self.welcome.next_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.config))
        self.config.back_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.welcome))
        self.config.next_btn.clicked.connect(self._start_install)

        self.setStyleSheet("""
            QMainWindow { background: #1a1a2e; }
            QWidget { background: #1a1a2e; color: #ddd; }
            QLabel { color: #ddd; }
            QComboBox {
                background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 4px; padding: 6px;
            }
            QFrame { border: none; }
        """)

    def _start_install(self):
        api_key = self.config.api_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please enter your API key.")
            return

        provider = self.config.provider_combo.currentText()
        voice = self.config.voice_combo.currentData()
        stt_idx = self.config.stt_combo.currentIndex()
        stt_model = ["large-v3", "large-v3-turbo", "medium"][stt_idx]
        device = "cuda" if self.config.device_combo.currentIndex() == 0 else "cpu"
        sensitivity = [0.5, 0.7, 0.9][self.config.sensitivity.currentIndex()]
        speed = 1.0
        custom_model = self.config.custom_model_edit.text().strip() if provider == "Custom" else ""
        custom_url = self.config.custom_url_edit.text().strip() if provider == "Custom" else ""

        self.stack.setCurrentWidget(self.progress)
        self.progress.log.append("Starting installation...")

        worker = InstallWorker(api_key, provider, voice, stt_model, device, sensitivity, speed, custom_model, custom_url)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.start()
        self._worker = worker

    def _on_progress(self, percent: int, msg: str):
        self.progress.progress.setValue(percent)
        self.progress.status.setText(msg)
        self.progress.log.append(msg)
        self.progress.log.moveCursor(self.progress.log.textCursor().MoveOperation.End)

    def _on_finished(self, success: bool, msg: str):
        if success:
            self.progress.finish_btn.setVisible(True)
            self.progress.finish_btn.clicked.connect(self._launch_lumi)
            self.progress.log.append("\n" + msg)
            self.progress.log.moveCursor(self.progress.log.textCursor().MoveOperation.End)
        else:
            QMessageBox.critical(self, "Installation Failed", msg)

    def _launch_lumi(self):
        venv_pyw = INSTALL_DIR / "venv" / "Scripts" / "pythonw.exe"
        if venv_pyw.exists():
            subprocess.Popen(
                [str(venv_pyw), "lumi_app.py"],
                cwd=str(INSTALL_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        self.close()


def _create_lumi_icon():
    """Create a Lumi icon (golden waveform burst on dark background)."""
    from PIL import Image, ImageDraw
    import io
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtCore import QByteArray

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded square background
    draw.rounded_rectangle([2, 2, size - 2, size - 2], radius=12, fill=(26, 26, 46, 255))

    # Golden waveform burst (sunburst / waveform hybrid)
    cx, cy = size // 2, size // 2
    rays = [
        (0, -18, 0, 14),       # top (long)
        (0, 14, 0, 8),          # bottom
        (-16, 0, 12, 0),        # left (long)
        (12, 0, 10, 0),         # right
        (-12, -12, 8, 8),       # top-left
        (10, -10, 7, 7),        # top-right
        (-10, 10, 7, 7),        # bottom-left
        (10, 10, 7, 7),         # bottom-right
        (-8, -16, 5, 12),       # near-top-left
        (8, -14, 5, 10),        # near-top-right
        (-8, 14, 5, 10),        # near-bottom-left
        (8, 14, 5, 10),         # near-bottom-right
        (-16, -8, 12, 5),       # near-left-top
        (-14, 8, 10, 5),        # near-left-bottom
        (14, -8, 10, 5),        # near-right-top
        (14, 8, 10, 5),         # near-right-bottom
    ]

    gold = (240, 165, 0, 255)
    gold_dim = (200, 140, 0, 180)

    for i, (x1, y1, x2, y2) in enumerate(rays):
        color = gold if i % 2 == 0 else gold_dim
        width = 3 if i < 4 else 2
        draw.line([cx + x1, cy + y1, cx + x2, cy + y2], fill=color, width=width)

    # Center dot
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=gold)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    pm = QPixmap()
    pm.loadFromData(QByteArray(buf.getvalue()))
    return QIcon(pm)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SetupWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
