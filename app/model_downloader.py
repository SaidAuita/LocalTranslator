import os
import time
import requests
from typing import Callable, Optional
from app.config import config, APP_DIR

REPO_ID = "JustFrederik/nllb-200-distilled-1.3B-ct2-int8"
HF_BASE_URL = f"https://huggingface.co/{REPO_ID}/resolve/main"

MODEL_FILES = [
    "config.json",
    "sentencepiece.bpe.model",
    "shared_vocabulary.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "model.bin"
]


class ModelDownloader:
    def __init__(self, target_dir: Optional[str] = None, proxy: Optional[str] = None):
        cfg_dir = target_dir or config.get("nllb_model_path", "models/nllb-200-distilled-1.3B-ct2-int8")
        if not os.path.isabs(cfg_dir):
            self.target_dir = os.path.join(APP_DIR, cfg_dir)
        else:
            self.target_dir = os.path.abspath(cfg_dir)
        self.proxy = proxy if proxy is not None else config.get("proxy", "")
        self.is_cancelled = False

    def get_proxies(self) -> Optional[dict]:
        if self.proxy:
            # Only use proxy if it is actually reachable
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(self.proxy)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 10808
                from app.config import is_port_listening
                if is_port_listening(host, port):
                    return {"http": self.proxy, "https": self.proxy}
            except Exception:
                pass
        return None

    def is_model_complete(self) -> bool:
        """Check if all files including model.bin exist and are non-empty."""
        if not os.path.isdir(self.target_dir):
            return False
        for f in MODEL_FILES:
            path = os.path.join(self.target_dir, f)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                return False
        # Verify model.bin is at least 1 GB
        model_bin = os.path.join(self.target_dir, "model.bin")
        if os.path.getsize(model_bin) < 1_000_000_000:
            return False
        return True

    def cancel(self):
        self.is_cancelled = True

    def download_file(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int, int, float, float, str], None]] = None
    ) -> bool:
        """
        Download a single file with resume support.
        progress_callback signature:
            progress_callback(downloaded_bytes, total_bytes, speed_mb_s, eta_sec, status_text)
        """
        os.makedirs(self.target_dir, exist_ok=True)
        file_path = os.path.join(self.target_dir, filename)
        url = f"{HF_BASE_URL}/{filename}"

        headers = {}
        existing_size = 0
        if os.path.exists(file_path):
            existing_size = os.path.getsize(file_path)

        proxies = self.get_proxies()

        # Check remote size with HEAD or Range
        try:
            head_resp = requests.head(url, headers={"Accept-Encoding": "identity"}, proxies=proxies, timeout=15, allow_redirects=True)
            total_size = int(head_resp.headers.get("content-length", 0))
        except Exception:
            total_size = 0

        # If file already completely downloaded
        if total_size > 0 and existing_size >= total_size:
            if progress_callback:
                progress_callback(total_size, total_size, 0.0, 0.0, f"{filename} уже загружен")
            return True

        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"
            mode = "ab"
            downloaded = existing_size
        else:
            mode = "wb"
            downloaded = 0

        try:
            resp = requests.get(url, headers=headers, proxies=proxies, stream=True, timeout=30, allow_redirects=True)
            if resp.status_code not in (200, 206):
                # If range not satisfiable or unsupported, restart from 0
                resp = requests.get(url, proxies=proxies, stream=True, timeout=30, allow_redirects=True)
                mode = "wb"
                downloaded = 0

            content_length = int(resp.headers.get("content-length", 0))
            if mode == "ab":
                total_bytes = downloaded + content_length
            else:
                total_bytes = content_length or total_size

            start_time = time.time()
            bytes_since_start = 0

            with open(file_path, mode) as fp:
                for chunk in resp.iter_content(chunk_size=1024 * 512):  # 512 KB chunks
                    if self.is_cancelled:
                        return False
                    if chunk:
                        fp.write(chunk)
                        downloaded += len(chunk)
                        bytes_since_start += len(chunk)

                        elapsed = time.time() - start_time
                        if elapsed > 0.5:
                            speed_mb = (bytes_since_start / (1024 * 1024)) / elapsed
                            remaining = max(0, total_bytes - downloaded)
                            eta = (remaining / (speed_mb * 1024 * 1024)) if speed_mb > 0 else 0
                            if progress_callback:
                                progress_callback(downloaded, total_bytes, speed_mb, eta, f"Загрузка {filename}")

            if progress_callback:
                progress_callback(total_bytes, total_bytes, 0.0, 0.0, f"{filename} готов!")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(downloaded, total_size or downloaded, 0.0, 0.0, f"Ошибка: {str(e)}")
            raise e

    def download_all(
        self,
        progress_callback: Optional[Callable[[int, int, float, float, str], None]] = None
    ) -> bool:
        """Download all model files sequentially."""
        self.is_cancelled = False
        for f in MODEL_FILES:
            if self.is_cancelled:
                return False
            success = self.download_file(f, progress_callback)
            if not success:
                return False
        return self.is_model_complete()


if __name__ == "__main__":
    import sys
    print("Проверка и загрузка локальной модели NLLB 1.3B...")
    downloader = ModelDownloader()
    if downloader.is_model_complete():
        print("Модель NLLB 1.3B уже полностью загружена!")
        sys.exit(0)

    def print_progress(cur, total, speed, eta, status):
        pct = (cur / total * 100) if total > 0 else 0
        cur_mb = cur / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        print(f"\r[{status}] {pct:.1f}% ({cur_mb:.1f}/{tot_mb:.1f} MB) Скорость: {speed:.2f} MB/s ETA: {eta:.0f}s   ", end="", flush=True)

    print(f"Целевая папка: {downloader.target_dir}")
    print(f"Прокси: {downloader.proxy or 'Нет'}")
    downloader.download_all(print_progress)
    print("\nЗавершено!")
