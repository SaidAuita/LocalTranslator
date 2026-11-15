import os
import sys
import shutil
import subprocess

def main():
    print("=" * 60)
    print("  Сборка Local Translator в .EXE (PyInstaller)")
    print("=" * 60)
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # 1. Clean previous builds
    print("[1/3] Очистка предыдущих сборок...")
    build_dir = os.path.join(base_dir, "build")
    dist_dir = os.path.join(base_dir, "dist", "LocalTranslator")
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir)
        except Exception as e:
            print(f"  Предупреждение при очистке build: {e}")
    if os.path.exists(dist_dir):
        try:
            shutil.rmtree(dist_dir)
        except Exception as e:
            print(f"  Предупреждение при очистке dist: {e}")

    # 2. Run PyInstaller
    print("[2/3] Запуск сборки PyInstaller...")
    spec_file = os.path.join(base_dir, "build_app.spec")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", spec_file]
    ret = subprocess.call(cmd)
    if ret != 0:
        print()
        print("[ОШИБКА] Сборка PyInstaller завершилась с кодом ошибки:", ret)
        return

    # 3. Copy config.json and images to output directory
    print("[3/3] Копирование конфигурации и ресурсов...")
    src_cfg = os.path.join(base_dir, "config.json")
    dst_cfg = os.path.join(dist_dir, "config.json")
    if os.path.exists(src_cfg):
        shutil.copy2(src_cfg, dst_cfg)

    src_images = os.path.join(base_dir, "images")
    dst_images = os.path.join(dist_dir, "images")
    if os.path.exists(src_images):
        if os.path.exists(dst_images):
            shutil.rmtree(dst_images)
        shutil.copytree(src_images, dst_images)

    # 4. Link models directory via directory junction (0 extra disk space)
    models_src = os.path.join(base_dir, "models")
    models_dst = os.path.join(dist_dir, "models")
    if os.path.exists(models_src) and not os.path.exists(models_dst):
        try:
            subprocess.call(["cmd", "/c", "mklink", "/J", models_dst, models_src], stdout=subprocess.DEVNULL)
            print("  [OK] Создана системная ссылка на папку моделей (models).")
        except Exception:
            pass

    # 5. Create release zip archive (excluding only root models folder)
    zip_name = "LocalTranslator-v1.2.0-windows-x64.zip"
    zip_path = os.path.join(base_dir, zip_name)
    print(f"\n[4/4] Создание релизного архива {zip_name}...")
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(dist_dir):
                if os.path.abspath(root) == os.path.abspath(dist_dir):
                    if 'models' in dirs:
                        dirs.remove('models')
                for file in files:
                    full_path = os.path.join(root, file)
                    if os.path.islink(full_path):
                        continue
                    rel_path = os.path.relpath(full_path, os.path.dirname(dist_dir))
                    zf.write(full_path, rel_path)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  [OK] Архив успешно создан: {zip_path} ({zip_size_mb:.2f} МБ)")
    except Exception as e:
        print(f"  [!] Ошибка создания архива: {e}")

    print()
    print("=" * 60)
    print("  Сборка успешно завершена!")
    print(f"  Исполняемый файл: {os.path.join(dist_dir, 'LocalTranslator.exe')}")
    print("=" * 60)
    print()
    print("Приложение полностью готово к запуску в фоновом режиме или из трея.")
    print()

if __name__ == "__main__":
    main()
