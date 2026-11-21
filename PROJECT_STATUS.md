# Project Status: Local Translator (Translate)

**Current Version:** 1.3.0  
**Stack:** Python 3.10+, PyQt6, CTranslate2 (NLLB-200 1.3B INT8), LM Studio / Ollama API, pynput (Global Hotkeys)  
**Location:** `C:\_CODE\Utilites\Translate`

---

## 🌟 Key Features Implemented

### 1. Keyboard Layout Switching & Punto Switcher Mechanics (v1.3.0)
- **`app/layout_converter.py`**:
  - Full bidirectional hardware mapping between English QWERTY and Russian ЙЦУКЕН keyboards (including punctuation, symbols, uppercase/lowercase).
  - `convert_en_to_ru`, `convert_ru_to_en`, `toggle_layout`, `convert_layout`.
  - Heuristic detection of mistyped layout (`is_probably_wrong_layout`): checks vowel distributions, impossible consonant sequences (`ghb`, `xnj`, `ltk`), and dictionary patterns.
- **Punto Switcher In-Place Toggle (`Pause`)**:
  - Hotkey `<pause>` grabs selected text in any Windows app, converts its layout (RU ↔ EN), and replaces it on the fly.
- **Auto-Correction on Translate**:
  - Option `"fix_layout_on_translate": True` automatically detects when text is typed in wrong layout (e.g. `ghbdtn, rfr ltkf?`), converts it to `Привет, как дела?`, and translates it.
  - Floating HUD (`ui_popup.py`) shows a badge indicator `🔄 Раскладка: [orig] ➔ [fixed]` and features a quick toggle button `[🔄]` (`Ctrl+R` / `Pause`).
  - Main window (`ui_main.py`) features `[🔄 Раскладка]` button and `Ctrl+R` / `Pause` shortcuts.
- **Settings Dialog**:
  - Checkbox to enable/disable auto-correction.
  - Dedicated key sequence editors for `hotkey_layout` (default `Pause`) and `hotkey_layout_translate` (default `Ctrl+Shift+R`).

### 2. Core Translation Engines & OCR (v1.0 - v1.2)
- CTranslate2 offline NLLB-200 1.3B INT8 with CUDA / CPU acceleration.
- LM Studio / Ollama local LLM integration with automatic model discovery and headless background launch.
- Compare Mode: side-by-side translation with millisecond latency metrics.
- Screen OCR Snippet tool (`Ctrl+Shift+S`) via Vision-Language LLM.
- 12 fully translated UI languages.
- System tray with cache clearing and minimization.

---

## 🚀 Key Files & Architecture
- `main.py`: Application entrypoint, `ApplicationManager`, signal wiring.
- `app/config.py`: Configuration persistence, default values, proxy detection.
- `app/layout_converter.py`: Layout switching tables and auto-detection algorithms.
- `app/hotkey_service.py`: Windows low-level clipboard & `pynput` global hotkeys listener.
- `app/ui_main.py`: Main window, `SettingsDialog`, language selectors.
- `app/ui_popup.py`: Quick floating HUD translation window.
- `app/ui_snippet.py`: High-DPI screen snipping tool.
- `app/i18n.py`: 12-language localization dictionary.
