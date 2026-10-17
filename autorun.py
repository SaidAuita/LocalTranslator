import sys
import os
import winreg

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "LocalTranslator"


def install():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Prefer compiled .exe if present, otherwise run_background.bat
    exe_path = os.path.join(base_dir, "dist", "LocalTranslator", "LocalTranslator.exe")
    if os.path.exists(exe_path):
        target = f'"{exe_path}" --minimized'
    else:
        bat_path = os.path.join(base_dir, "run_background.bat")
        target = f'"{bat_path}"'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, target)
        winreg.CloseKey(key)
        print("=" * 60)
        print("  [УСПЕХ] Local Translator добавлен в автозагрузку Windows!")
        print(f"  Команда запуска: {target}")
        print("  При старте системы переводчик запускается бесшумно в трее.")
        print("  Для перевода выделенного текста: Ctrl+Q")
        print("=" * 60)
    except Exception as e:
        print("[ОШИБКА] Не удалось настроить автозагрузку:", e)


def uninstall():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print("[УСПЕХ] Local Translator удален из автозагрузки Windows.")
    except FileNotFoundError:
        print("[ИНФО] Запись в автозагрузке не найдена.")
    except Exception as e:
        print("[ОШИБКА]:", e)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    if action == "uninstall":
        uninstall()
    else:
        install()
