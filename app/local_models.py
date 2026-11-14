import os
import sys
import shutil
import subprocess
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from app.config import is_port_listening

# Avoid popping up black command prompt windows on Windows
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def find_lms_cli() -> Optional[str]:
    """Find LM Studio CLI executable (lms / lms.exe)."""
    # 1. In PATH
    w = shutil.which("lms") or shutil.which("lms.exe")
    if w and os.path.isfile(w):
        return w

    # 2. In user profile ~/.lmstudio/bin
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".lmstudio", "bin", "lms.exe"),
        os.path.join(home, ".lmstudio", "bin", "lms"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\resources\app\.webpack\bin\lms.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\LM Studio\resources\app\.webpack\bin\lms.exe")
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def find_ollama_cli() -> Optional[str]:
    """Find Ollama CLI executable (ollama / ollama.exe)."""
    # 1. In PATH
    w = shutil.which("ollama") or shutil.which("ollama.exe")
    if w and os.path.isfile(w):
        return w

    # 2. In local appdata
    cand = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if os.path.isfile(cand):
        return cand
    return None


def get_lmstudio_models_dir() -> str:
    """Get the default directory where LM Studio stores downloaded models."""
    home = os.path.expanduser("~")
    return os.path.join(home, ".lmstudio", "models")


def format_size(size_bytes: int) -> str:
    """Format bytes into readable MB or GB string."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    elif size_bytes > 0:
        return f"{size_bytes / 1024:.0f} KB"
    return "0 B"


def get_lmstudio_models() -> List[Dict[str, Any]]:
    """
    List all local models from LM Studio.
    Uses 'lms ls --json' when available, falls back to scanning ~/.lmstudio/models.
    """
    models: List[Dict[str, Any]] = []
    lms_bin = find_lms_cli()

    if lms_bin:
        try:
            res = subprocess.run(
                [lms_bin, "ls", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                for item in data:
                    # Filter for LLM text models (skip pure embeddings or multimodal projector adapters)
                    mtype = item.get("type", "llm")
                    if mtype != "llm":
                        continue

                    model_key = item.get("modelKey") or item.get("path") or ""
                    display_name = item.get("displayName") or model_key
                    size_bytes = item.get("sizeBytes", 0)
                    params = item.get("paramsString", "")
                    quant = item.get("quantization", {}).get("name", "") if isinstance(item.get("quantization"), dict) else ""

                    if not model_key:
                        continue

                    models.append({
                        "id": model_key,
                        "name": display_name,
                        "size_str": format_size(size_bytes),
                        "size_bytes": size_bytes,
                        "backend": "lmstudio",
                        "params": params,
                        "quant": quant,
                        "url": "http://127.0.0.1:1234/v1"
                    })
                if models:
                    return models
        except Exception as e:
            print(f"[LocalModels] Error querying 'lms ls': {e}")

    # Fallback: scan ~/.lmstudio/models directory for .gguf files
    models_dir = get_lmstudio_models_dir()
    if os.path.isdir(models_dir):
        for root, _, files in os.walk(models_dir):
            for f in files:
                f_lower = f.lower()
                if f_lower.endswith(".gguf"):
                    # Ignore projector and draft auxiliary files
                    if f_lower.startswith("mmproj-") or f_lower.startswith("mtp-") or "embed" in f_lower:
                        continue
                    full_path = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(full_path)
                    except Exception:
                        sz = 0
                    rel_path = os.path.relpath(full_path, models_dir).replace("\\", "/")
                    name = os.path.splitext(f)[0]
                    # Clean up common naming artifacts
                    clean_name = name.replace(".Q", " (Q").replace("-GGUF", "")
                    if "(" in clean_name and not clean_name.endswith(")"):
                        clean_name += ")"
                    models.append({
                        "id": rel_path,
                        "name": clean_name,
                        "size_str": format_size(sz),
                        "size_bytes": sz,
                        "backend": "lmstudio",
                        "params": "",
                        "quant": "",
                        "url": "http://127.0.0.1:1234/v1"
                    })

    return models


def get_ollama_models() -> List[Dict[str, Any]]:
    """
    List all local models from Ollama.
    Checks REST API first (fast), falls back to 'ollama list'.
    """
    models: List[Dict[str, Any]] = []

    # 1. Try REST API if server is up
    if is_port_listening("127.0.0.1", 11434, timeout=0.15):
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("models", []):
                        name = m.get("name") or m.get("model", "")
                        sz = m.get("size", 0)
                        params = m.get("details", {}).get("parameter_size", "")
                        quant = m.get("details", {}).get("quantization_level", "")
                        if name:
                            models.append({
                                "id": name,
                                "name": name,
                                "size_str": format_size(sz),
                                "size_bytes": sz,
                                "backend": "ollama",
                                "params": params,
                                "quant": quant,
                                "url": "http://127.0.0.1:11434/v1"
                            })
                    if models:
                        return models
        except Exception:
            pass

    # 2. Try CLI 'ollama list'
    ollama_bin = find_ollama_cli()
    if ollama_bin:
        try:
            res = subprocess.run(
                [ollama_bin, "list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
                for l in lines[1:]:  # skip header
                    parts = l.split()
                    if len(parts) >= 4:
                        name = parts[0]
                        size_str = f"{parts[2]} {parts[3]}"
                        models.append({
                            "id": name,
                            "name": name,
                            "size_str": size_str,
                            "size_bytes": 0,
                            "backend": "ollama",
                            "params": "",
                            "quant": "",
                            "url": "http://127.0.0.1:11434/v1"
                        })
        except Exception as e:
            print(f"[LocalModels] Error querying 'ollama list': {e}")

    return models


def get_all_local_models() -> List[Dict[str, Any]]:
    """Return combined list of models from LM Studio and Ollama."""
    all_models: List[Dict[str, Any]] = []
    lms_models = get_lmstudio_models()
    ollama_models = get_ollama_models()

    for m in lms_models:
        all_models.append(m)
    for m in ollama_models:
        all_models.append(m)

    return all_models


def get_active_lms_model() -> Optional[str]:
    """Check currently loaded model in LM Studio via CLI 'lms ps' or API."""
    lms_bin = find_lms_cli()
    if lms_bin:
        try:
            res = subprocess.run(
                [lms_bin, "ps"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
                creationflags=CREATE_NO_WINDOW
            )
            out = (res.stdout + "\n" + res.stderr).strip()
            if "No models are currently loaded" in out:
                return None
            lines = [l.strip() for l in out.split("\n") if l.strip()]
            for l in lines:
                if "IDENTIFIER" in l:
                    continue
                parts = l.split()
                if len(parts) >= 2:
                    return parts[0]
        except Exception:
            pass

    # Fallback to GET /models API
    if is_port_listening("127.0.0.1", 1234, timeout=0.15):
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:1234/v1/models")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models and len(models) > 0:
                    return models[0].get("id")
        except Exception:
            pass
    return None


def start_lms_server() -> Tuple[bool, str]:
    """Start LM Studio local headless server using 'lms server start'."""
    lms_bin = find_lms_cli()
    if not lms_bin:
        return False, "Утилита 'lms' не найдена. Убедитесь, что LM Studio установлена."

    try:
        res = subprocess.run(
            [lms_bin, "server", "start"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        out = (res.stdout + " " + res.stderr).lower()
        if res.returncode == 0 or "already running" in out or "port 1234" in out:
            # Poll port up to 5 seconds
            for _ in range(25):
                if is_port_listening("127.0.0.1", 1234, timeout=0.2):
                    return True, "Сервер LM Studio запущен успешно (порт 1234)."
                time.sleep(0.2)
            return True, "Сервер LM Studio запущен."
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, f"Ошибка запуска сервера LM Studio: {e}"


def load_lms_model(model_key: str) -> Tuple[bool, str]:
    """Load a specific model into LM Studio memory via 'lms load -y <model_key>'."""
    lms_bin = find_lms_cli()
    if not lms_bin:
        return False, "Утилита 'lms' не найдена."

    # Make sure server is running first
    if not is_port_listening("127.0.0.1", 1234, timeout=0.2):
        ok, msg = start_lms_server()
        if not ok:
            return False, msg

    try:
        res = subprocess.run(
            [lms_bin, "load", "-y", model_key],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            creationflags=CREATE_NO_WINDOW
        )
        out = (res.stdout + "\n" + res.stderr)
        if "successfully" in out.lower() or "loaded" in out.lower() or res.returncode == 0:
            return True, f"Модель '{model_key}' успешно загружена в память."
        return False, res.stderr.strip() or res.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Таймаут загрузки модели '{model_key}' (> 60 сек)."
    except Exception as e:
        return False, f"Ошибка загрузки модели '{model_key}': {e}"


def unload_lms_model(model_key: Optional[str] = None) -> Tuple[bool, str]:
    """Unload a model from LM Studio memory."""
    lms_bin = find_lms_cli()
    if not lms_bin:
        return False, "Утилита 'lms' не найдена."
    try:
        cmd = [lms_bin, "unload"]
        if model_key:
            cmd.append(model_key)
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        return True, "Модель выгружена из памяти."
    except Exception as e:
        return False, f"Ошибка выгрузки: {e}"


def start_ollama_server() -> Tuple[bool, str]:
    """Start Ollama server in background if not already running."""
    if is_port_listening("127.0.0.1", 11434, timeout=0.2):
        return True, "Сервер Ollama уже запущен."

    ollama_bin = find_ollama_cli()
    if not ollama_bin:
        return False, "Утилита 'ollama' не найдена. Убедитесь, что Ollama установлена."

    try:
        subprocess.Popen(
            [ollama_bin, "serve"],
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Poll port up to 5 seconds
        for _ in range(25):
            if is_port_listening("127.0.0.1", 11434, timeout=0.2):
                return True, "Сервер Ollama запущен успешно (порт 11434)."
            time.sleep(0.2)
        return True, "Сервер Ollama запускается."
    except Exception as e:
        return False, f"Ошибка запуска Ollama: {e}"


def ensure_model_ready(model_id: str, backend: str = "auto") -> Tuple[bool, str, str]:
    """
    Ensure the backend server is running and the model is ready.
    Returns: (success: bool, message: str, effective_url: str)
    """
    # Auto-detect backend if needed
    if backend == "auto":
        if ":" in model_id and not "/" in model_id:
            backend = "ollama"
        else:
            backend = "lmstudio"

    if backend == "ollama":
        if not is_port_listening("127.0.0.1", 11434, timeout=0.2):
            ok, msg = start_ollama_server()
            if not ok:
                return False, msg, "http://127.0.0.1:11434/v1"
        return True, "Ollama готова.", "http://127.0.0.1:11434/v1"

    else:  # lmstudio
        # 1. Ensure server is running
        if not is_port_listening("127.0.0.1", 1234, timeout=0.2):
            ok, msg = start_lms_server()
            if not ok:
                return False, msg, "http://127.0.0.1:1234/v1"

        # 2. Check if model is already loaded
        active = get_active_lms_model()
        if active and (active == model_id or model_id in active or active in model_id):
            return True, f"Модель '{active}' уже активна в LM Studio.", "http://127.0.0.1:1234/v1"

        # 3. Load model if specified
        if model_id and model_id != "default" and model_id != "local-model":
            ok, msg = load_lms_model(model_id)
            if not ok:
                return False, msg, "http://127.0.0.1:1234/v1"

        return True, "LM Studio готова.", "http://127.0.0.1:1234/v1"

