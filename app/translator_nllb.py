import os
import re
import time
import ctranslate2
from transformers import AutoTokenizer
from typing import Tuple, Optional
from app.config import config, LANGUAGES, APP_DIR
from app.languages_data import get_nllb_code


def init_cuda_dlls():
    """Discover and register CUDA DLL directories (e.g. from Ollama or NVIDIA Toolkit)."""
    import os
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.2\bin"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            try:
                os.add_dll_directory(path)
                os.environ["PATH"] = path + ";" + os.environ.get("PATH", "")
            except Exception:
                pass


# Initialize DLLs on module import
init_cuda_dlls()


class NLLBTranslator:
    def __init__(self, model_path: Optional[str] = None):
        cfg_path = model_path or config.get("nllb_model_path", "models/nllb-200-distilled-1.3B-ct2-int8")
        if not os.path.isabs(cfg_path):
            self.model_path = os.path.join(APP_DIR, cfg_path)
        else:
            self.model_path = os.path.abspath(cfg_path)
        self.translator: Optional[ctranslate2.Translator] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.device = "cpu"
        self.compute_type = "int8"
        self.is_loaded = False
        self.load_error: Optional[str] = None
        self._cache = {}

    def clear_cache(self):
        self._cache.clear()

    def unload_model(self):
        """Unload model from memory to free VRAM/RAM."""
        self.translator = None
        self.tokenizer = None
        self.is_loaded = False
        self.load_error = None

    def reload_model(self) -> bool:
        """Force reload model (e.g. after changing device)."""
        self.unload_model()
        return self.load_model()

    def check_cuda_available(self) -> bool:
        try:
            return ctranslate2.get_cuda_device_count() > 0
        except Exception:
            return False

    def load_model(self) -> bool:
        """Load NLLB model and tokenizer into memory with fallback to CPU."""
        desired_device = config.get("device", "auto")
        # If already loaded with the desired device, keep it
        if self.is_loaded:
            if desired_device == "cpu" and self.device == "cuda":
                self.unload_model()
            elif desired_device == "cuda" and self.device == "cpu":
                self.unload_model()
            else:
                return True

        model_bin = os.path.join(self.model_path, "model.bin")
        if not os.path.exists(model_bin):
            self.load_error = f"Файл модели model.bin не найден в {self.model_path}. Требуется загрузка."
            return False

        desired_device = config.get("device", "auto")
        should_try_cuda = desired_device == "cuda" or (desired_device == "auto" and self.check_cuda_available())

        try:
            # Load tokenizer from local files
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True,
                src_lang="rus_Cyrl"
            )
        except Exception as e:
            self.load_error = f"Ошибка токенизатора: {e}"
            return False

        # Try CUDA first if available
        if should_try_cuda:
            try:
                self.device = "cuda"
                self.compute_type = "int8_float16"
                self.translator = ctranslate2.Translator(
                    self.model_path,
                    device="cuda",
                    compute_type="int8_float16",
                    inter_threads=1,
                    intra_threads=4
                )
                self.is_loaded = True
                self.load_error = None
                print(f"[NLLB] Успешно загружено на CUDA (RTX 3080 Ti)!")
                return True
            except Exception as cuda_err:
                print(f"[NLLB] Предупреждение: CUDA недоступна ({cuda_err}), переключение на CPU...")

        # Fallback to CPU
        try:
            self.device = "cpu"
            self.compute_type = "int8"
            self.translator = ctranslate2.Translator(
                self.model_path,
                device="cpu",
                compute_type="int8",
                inter_threads=1,
                intra_threads=4
            )
            self.is_loaded = True
            self.load_error = None
            print(f"[NLLB] Успешно загружено на CPU (INT8)")
            return True
        except Exception as e:
            self.load_error = str(e)
            self.is_loaded = False
            print(f"[NLLB] Ошибка загрузки модели на CPU: {e}")
            return False

    def detect_language(self, text: str) -> Tuple[str, str]:
        """
        Auto-detect direction:
        If Cyrillic present -> RU -> EN.
        Else -> EN -> RU.
        Returns: (src_nllb_code, tgt_nllb_code)
        """
        if re.search(r'[\u0400-\u04FF]', text):
            return "rus_Cyrl", "eng_Latn"
        return "eng_Latn", "rus_Cyrl"

    def translate(
        self,
        text: str,
        src_lang: str = "auto",
        tgt_lang: str = "auto",
        force_refresh: bool = False
    ) -> Tuple[str, float]:
        """
        Translate text.
        Returns: (translated_text, latency_in_ms)
        """
        clean_text = text.strip() if text else ""
        if not clean_text:
            return "", 0.0

        cache_key = (clean_text, src_lang, tgt_lang)
        if not force_refresh and cache_key in self._cache:
            return self._cache[cache_key][0], 0.0

        if not self.is_loaded:
            if not self.load_model():
                raise RuntimeError(self.load_error or "Модель NLLB не загружена.")

        start_time = time.perf_counter()

        # Determine language codes
        if src_lang == "auto" and tgt_lang == "auto":
            src_nllb, tgt_nllb = self.detect_language(text)
        elif src_lang == "auto":
            auto_src, _ = self.detect_language(text)
            src_nllb = auto_src
            tgt_nllb = get_nllb_code(tgt_lang, "eng_Latn")
            if src_nllb == tgt_nllb:
                tgt_nllb = "rus_Cyrl" if src_nllb == "eng_Latn" else "eng_Latn"
        elif tgt_lang == "auto":
            src_nllb = get_nllb_code(src_lang, "rus_Cyrl")
            tgt_nllb = "eng_Latn" if src_nllb == "rus_Cyrl" else "rus_Cyrl"
        else:
            src_nllb = get_nllb_code(src_lang, "rus_Cyrl")
            tgt_nllb = get_nllb_code(tgt_lang, "eng_Latn")

        # Split text into paragraphs to maintain formatting
        paragraphs = text.split("\n")
        translated_paragraphs = []

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                translated_paragraphs.append("")
                continue

            self.tokenizer.src_lang = src_nllb
            source_ids = self.tokenizer.encode(para_clean)
            source_tokens = self.tokenizer.convert_ids_to_tokens(source_ids)

            target_prefix = [tgt_nllb]
            results = self.translator.translate_batch(
                [source_tokens],
                target_prefix=[target_prefix],
                beam_size=4,
                max_decoding_length=1024,
                repetition_penalty=1.2
            )

            output_tokens = results[0].hypotheses[0]
            # Strip target_prefix token if present
            if output_tokens and output_tokens[0] == tgt_nllb:
                output_tokens = output_tokens[1:]

            output_ids = self.tokenizer.convert_tokens_to_ids(output_tokens)
            para_translated = self.tokenizer.decode(output_ids, skip_special_tokens=True).strip()
            translated_paragraphs.append(para_translated)

        final_translation = "\n".join(translated_paragraphs)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if len(self._cache) > 200:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = (final_translation, latency_ms)

        return final_translation, latency_ms


# Global singleton instance
nllb_translator = NLLBTranslator()
