"""
Скрипт загрузки модели Meta NLLB-200 1.3B INT8 (CTranslate2).
Запускает загрузку с поддержкой докачки и прокси.
"""
import sys
from app.model_downloader import ModelDownloader


def main():
    print("=" * 65)
    print("  Загрузчик локальной модели NLLB-200 1.3B INT8 (CTranslate2)")
    print("=" * 65)

    downloader = ModelDownloader()
    print(f"Целевая папка : {downloader.target_dir}")
    print(f"Прокси         : {downloader.proxy or 'Прямое соединение'}")

    if downloader.is_model_complete():
        print("\n✓ Модель NLLB 1.3B уже полностью загружена и проверена!")
        return

    print("\nНачало загрузки файлов модели (общий размер ~1.4 ГБ)...")
    print("Поддерживается пауза и автоматическое возобновление при обрыве связи.\n")

    def progress(cur, total, speed, eta, status):
        pct = (cur / total * 100) if total > 0 else 0
        cur_mb = cur / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        print(f"\r[{status}] {pct:.1f}% ({cur_mb:.1f}/{tot_mb:.1f} MB) Скорость: {speed:.2f} MB/s ETA: {eta:.0f}s    ", end="", flush=True)

    try:
        success = downloader.download_all(progress)
        if success:
            print("\n\n✓ Модель успешно загружена! Теперь можно запускать: python main.py")
        else:
            print("\n\n✕ Загрузка была прервана.")
    except KeyboardInterrupt:
        print("\n\nЗагрузка приостановлена. Запустите скрипт снова, чтобы продолжить с места остановки.")
    except Exception as e:
        print(f"\n\n✕ Ошибка: {e}")


if __name__ == "__main__":
    main()
