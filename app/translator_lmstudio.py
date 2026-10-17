import time
import requests
import subprocess
import re
from typing import Tuple, List, Optional
from app.config import config, LANGUAGES
from app.languages_data import get_language_info


class LMStudioTranslator:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.get("lm_studio_url", "http://127.0.0.1:1234/v1")).rstrip("/")
        self.last_detected_model: Optional[str] = None
        # Cache key: (text_stripped, src_lang, tgt_lang, model_name) -> (translated_text, latency_ms, model_name)
        self._cache = {}

    def clear_cache(self):
        """Clear translation cache."""
        self._cache.clear()

    def get_api_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def check_connection(self) -> Tuple[bool, str, List[str]]:
        """
        Check if LM Studio is reachable and fetch available models.
        Returns: (is_online, current_or_first_model_name, list_of_models)
        """
        try:
            # Fast socket pre-check to avoid waiting for HTTP timeout if server is off
            import urllib.parse
            parsed = urllib.parse.urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 1234
            from app.config import is_port_listening
            if not is_port_listening(host, port, timeout=0.1):
                return False, "", []

            url = self.get_api_url("models")
            # Bypass system proxy for local loopback connections
            resp = requests.get(url, timeout=1.0, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                configured = config.get("lm_studio_model", "")
                selected = configured if configured in models else (models[0] if models else "default")
                self.last_detected_model = selected
                return True, selected, models
            return False, "", []
        except Exception:
            return False, "", []

    def start_server_via_lms(self) -> Tuple[bool, str]:
        """Attempt to launch LM Studio server using 'lms server start'."""
        try:
            res = subprocess.run(["lms", "server", "start"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0 or "already running" in res.stdout.lower() or "port 1234" in res.stdout.lower():
                return True, "Сервер LM Studio запущен успешно."
            return False, res.stderr or res.stdout
        except FileNotFoundError:
            return False, "Команда 'lms' не найдена в PATH. Запустите LM Studio вручную."
        except Exception as e:
            return False, f"Ошибка запуска: {e}"

    def detect_lang_names(self, text: str, src: str, tgt: str) -> Tuple[str, str]:
        """Resolve human-readable language names for prompting."""
        if src == "auto" and tgt == "auto":
            if re.search(r'[\u0400-\u04FF]', text):
                return "Russian", "English"
            return "English", "Russian"
        elif src == "auto":
            is_cyrillic = bool(re.search(r'[\u0400-\u04FF]', text))
            s_name = "Russian" if is_cyrillic else "English"
            t_info = get_language_info(tgt)
            t_name = f"{t_info.get('en_name', 'Russian')} ({t_info.get('name', 'Русский')})"
            return s_name, t_name
        elif tgt == "auto":
            s_info = get_language_info(src)
            s_name = f"{s_info.get('en_name', 'English')} ({s_info.get('name', 'Английский')})"
            t_name = "Russian" if "рус" in s_name.lower() or "cyrl" in s_name.lower() else "English"
            return s_name, t_name
        else:
            s_info = get_language_info(src)
            t_info = get_language_info(tgt)
            s_name = f"{s_info.get('en_name', src)} ({s_info.get('name', src)})"
            t_name = f"{t_info.get('en_name', tgt)} ({t_info.get('name', tgt)})"
            return s_name, t_name

    def translate(
        self,
        text: str,
        src_lang: str = "auto",
        tgt_lang: str = "auto",
        force_refresh: bool = False
    ) -> Tuple[str, float, str]:
        """
        Translate text via LM Studio OpenAI-compatible endpoint.
        Returns: (translated_text, latency_ms, model_name)
        """
        clean_text = text.strip() if text else ""
        if not clean_text:
            return "", 0.0, ""

        s_name, t_name = self.detect_lang_names(clean_text, src_lang, tgt_lang)

        # Retrieve model
        model_to_use = config.get("lm_studio_model") or self.last_detected_model or "local-model"

        # Check in-memory cache to prevent duplicate slow calls and llama.cpp prefix-cache reuse issues
        cache_key = (clean_text, src_lang, tgt_lang, model_to_use)
        if not force_refresh and cache_key in self._cache:
            cached_res, cached_lat, cached_mod = self._cache[cache_key]
            return cached_res, 0.0, cached_mod

        system_prompt = (
            f"You are a professional translator. Translate the text from {s_name} to {t_name}.\n"
            "Requirements:\n"
            "- Output ONLY the direct translation.\n"
            "- Do NOT add explanations, notes, greetings, or conversational filler.\n"
            "- Preserve original formatting, bullet points, and technical terms."
        )

        user_content = f"Translate the following text to {t_name}:\n\n{clean_text}"

        word_count = len(clean_text.split())
        estimated_max_tokens = max(256, min(4096, word_count * 4 + 128))

        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": float(config.get("lm_studio_temperature", 0.2)),
            "max_tokens": estimated_max_tokens,
            "stream": False
        }

        url = self.get_api_url("chat/completions")
        start_time = time.perf_counter()

        try:
            # Localhost requests bypass proxies. Timeout is 90s.
            resp = requests.post(
                url,
                json=payload,
                timeout=90,
                proxies={"http": None, "https": None}
            )
            resp.raise_for_status()
            data = resp.json()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("LM Studio вернул пустой ответ.")

            raw_translation = choices[0].get("message", {}).get("content", "").strip()

            # Clean any accidental outer markdown fences or quotes
            clean_translation = raw_translation
            if clean_translation.startswith("```") and clean_translation.endswith("```"):
                lines = clean_translation.split("\n")
                if len(lines) >= 3:
                    clean_translation = "\n".join(lines[1:-1]).strip()

            used_model = data.get("model", model_to_use)

            # Store in cache (limit cache to 200 items)
            if len(self._cache) > 200:
                self._cache.pop(next(iter(self._cache)))
            self._cache[cache_key] = (clean_translation, latency_ms, used_model)

            return clean_translation, latency_ms, used_model

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Таймаут ответа LM Studio (> 90 сек).\n"
                "Сервер LM Studio или видеопамять (VRAM) перегружены."
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Не удалось подключиться к LM Studio по адресу {self.base_url}.\n"
                "Убедитесь, что LM Studio запущен и в нём активен Local Server."
            )
        except Exception as e:
            raise RuntimeError(f"Ошибка LM Studio: {str(e)}")

    def recognize_image(self, image_base64: str, prompt: Optional[str] = None) -> Tuple[str, float, str]:
        """
        Extract text from an image via Vision-Language LLM in LM Studio.
        Returns: (extracted_text, latency_ms, model_name)
        """
        if not image_base64:
            return "", 0.0, ""

        model_to_use = config.get("lm_studio_model") or self.last_detected_model or "local-model"

        if not prompt:
            prompt = (
                "Transcribe all text from this image accurately and completely. "
                "Output ONLY the extracted text, exactly as shown, preserving line breaks. "
                "Do NOT add any introduction, explanations, comments, or markdown code blocks."
            )

        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
            "stream": False
        }

        url = self.get_api_url("chat/completions")
        start_time = time.perf_counter()

        try:
            resp = requests.post(
                url,
                json=payload,
                timeout=120,
                proxies={"http": None, "https": None}
            )

            if resp.status_code != 200:
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    if "error" in err_json and "message" in err_json["error"]:
                        err_detail = err_json["error"]["message"]
                except Exception:
                    pass
                raise RuntimeError(f"HTTP {resp.status_code}: {err_detail}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("LM Studio вернул пустой ответ для изображения.")

            raw_text = choices[0].get("message", {}).get("content", "").strip()

            clean_text = raw_text
            if clean_text.startswith("```") and clean_text.endswith("```"):
                lines = clean_text.split("\n")
                if len(lines) >= 3:
                    clean_text = "\n".join(lines[1:-1]).strip()

            used_model = data.get("model", model_to_use)
            return clean_text, latency_ms, used_model

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Таймаут распознавания изображения (> 120 сек).\n"
                "Сервер LM Studio или видеопамять (VRAM) перегружены."
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Не удалось подключиться к LM Studio по адресу {self.base_url}.\n"
                "Убедитесь, что LM Studio запущен и в нём активен Local Server."
            )
        except Exception as e:
            raise RuntimeError(f"Ошибка Vision LLM: {str(e)}")


# Global singleton instance
lmstudio_translator = LMStudioTranslator()

