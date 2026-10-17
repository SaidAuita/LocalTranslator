import json
import os
import socket
from typing import Dict, Any

from app.languages_data import LANGUAGES, get_nllb_code, get_language_info, get_display_name

DEFAULT_CONFIG: Dict[str, Any] = {
    "engine": "compare",  # "nllb" | "lmstudio" | "compare"
    "source_lang": "auto",
    "target_lang": "auto",
    "recent_source_langs": ["ru", "en"],
    "recent_target_langs": ["ru", "en"],
    "nllb_model_path": "models/nllb-200-distilled-1.3B-ct2-int8",
    "device": "auto",  # "cuda" | "cpu" | "auto"
    "compute_type": "int8_float16",  # "int8", "float16", "int8_float16"
    "lm_studio_url": "http://127.0.0.1:1234/v1",
    "lm_studio_model": "",
    "lm_studio_temperature": 0.2,
    "hotkey_translate": "<ctrl>+q",
    "hotkey_replace": "<ctrl>+<shift>+q",
    "hotkey_ocr": "<ctrl>+<shift>+s",
    "auto_copy_translation": False,
    "close_popup_on_copy": True,
    "proxy": "http://127.0.0.1:10808",
    "dark_mode": True,
    "ui_language": "en",  # "en" (default), "ru", "de", "fr", "es", "it", "zh", "ja", "uk", "tr", "pl", "pt"
    "start_minimized": False,
    "minimize_to_tray": True
}


import sys

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_port_listening(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a specific host and port is reachable."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def get_default_proxy() -> str:
    """Detect if local proxy (Happ / v2ray / clash) is active."""
    if is_port_listening("127.0.0.1", 10808):
        return "http://127.0.0.1:10808"
    if is_port_listening("127.0.0.1", 10809):
        return "http://127.0.0.1:10809"
    if is_port_listening("127.0.0.1", 7890):
        return "http://127.0.0.1:7890"
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""


class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        if not os.path.isabs(config_file):
            self.config_file = os.path.join(APP_DIR, config_file)
        else:
            self.config_file = os.path.abspath(config_file)
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        # Check auto proxy
        detected_proxy = get_default_proxy()
        if detected_proxy:
            self.data["proxy"] = detected_proxy
        self.load()

    def load(self) -> None:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading {self.config_file}: {e}")

    def save(self) -> None:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()


# Global singleton instance
config = ConfigManager()
