"""Windows settings and configuration tools."""
from __future__ import annotations

import subprocess
import ctypes
from pathlib import Path

from tools import tool


@tool(
    name="change_wallpaper",
    description="Change the desktop wallpaper to an image file.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the wallpaper image file",
            },
        },
        "required": ["image_path"],
    },
)
def change_wallpaper(image_path: str) -> str:
    p = Path(image_path)
    if not p.exists():
        return f"error: file not found: {image_path}"

    try:
        # Windows SPI_SETDESKWALLPAPER = 20
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            str(p),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        if result:
            return f"Wallpaper changed to: {p.name}"
        return f"error: SystemParametersInfo failed"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_settings",
    description="Open Windows Settings to a specific page. Pages: 'display', 'network', 'bluetooth', 'privacy', 'update', 'sound', 'apps', 'personalization', 'time', 'mouse'.",
    parameters={
        "type": "object",
        "properties": {
            "page": {
                "type": "string",
                "description": "Settings page to open",
                "enum": ["display", "network", "bluetooth", "privacy", "update", "sound", "apps", "personalization", "time", "mouse", "default"],
            },
        },
        "required": [],
    },
)
def open_settings(page: str = "default") -> str:
    pages = {
        "display": "ms-settings:display",
        "network": "ms-settings:network",
        "bluetooth": "ms-settings:bluetooth",
        "privacy": "ms-settings:privacy",
        "update": "ms-settings:windowsupdate",
        "sound": "ms-settings:sound",
        "apps": "ms-settings:appsfeatures",
        "personalization": "ms-settings:personalization",
        "time": "ms-settings:dateandtime",
        "mouse": "ms-settings:mousetouchpad",
    }

    uri = pages.get(page, "ms-settings:")

    try:
        subprocess.Popen(
            ["start", uri],
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Opened Windows Settings: {page}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_installed_apps",
    description="List installed applications on the system.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional filter by app name",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 50)",
            },
        },
        "required": [],
    },
)
def get_installed_apps(query: str = "", limit: int = 50) -> str:
    try:
        import winreg

        apps = []
        paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]

        for reg_path in paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    try:
                        subkey = winreg.OpenKey(key, subkey_name)
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                        publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                        apps.append({"name": name, "version": version, "publisher": publisher})
                    except (OSError, KeyError):
                        pass
            except OSError:
                pass

        if query:
            q_lower = query.lower()
            apps = [a for a in apps if q_lower in a["name"].lower()]

        apps = sorted(apps, key=lambda a: a["name"].lower())[:limit]

        lines = [f"Installed Applications ({len(apps)} shown):"]
        for a in apps:
            ver = f" v{a['version']}" if a.get("version") else ""
            pub = f" ({a['publisher']})" if a.get("publisher") else ""
            lines.append(f"  {a['name']}{ver}{pub}")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="change_display_brightness",
    description="Change screen brightness on Windows 10/11 laptops.",
    parameters={
        "type": "object",
        "properties": {
            "level": {
                "type": "integer",
                "description": "Brightness level 0-100",
                "minimum": 0,
                "maximum": 100,
            },
        },
        "required": ["level"],
    },
)
def change_display_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))

    try:
        ps_cmd = f'(Get-WmiObject -Namespace "root/wmi" -Class WmiMonitorBrightnessMethods).WmiSetBrightness(0, {level})'
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Display brightness set to {level}%"
        return f"error setting brightness: {result.stderr.strip()[:200]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_wifi_password",
    description="Show saved WiFi password for a known network.",
    parameters={
        "type": "object",
        "properties": {
            "network": {
                "type": "string",
                "description": "WiFi network name (SSID). Leave empty to list all saved networks.",
            },
        },
        "required": [],
    },
)
def get_wifi_password(network: str = "") -> str:
    try:
        if not network:
            # List all saved networks
            result = subprocess.run(
                ["netsh", "wlan", "show", "profiles"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = []
            for line in result.stdout.split("\n"):
                if "All User Profile" in line:
                    name = line.split(":", 1)[1].strip()
                    lines.append(f"  {name}")
            if lines:
                return "Saved WiFi networks:\n" + "\n".join(lines)
            return "No saved WiFi networks found."

        # Get password for specific network
        result = subprocess.run(
            ["netsh", "wlan", "show", "profile", "name=" + network, "key=clear"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.split("\n"):
            if "Key Content" in line:
                password = line.split(":", 1)[1].strip()
                return f"WiFi password for '{network}': {password}"

        return f"No saved password found for network '{network}'"
    except Exception as e:
        return f"error: {e}"
