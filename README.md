# 🌐 Local Translator • NLLB 1.3B & LM Studio (Vision OCR)

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/GUI-PyQt6-green?logo=qt" alt="PyQt6" />
  <img src="https://img.shields.io/badge/Engine-CTranslate2%20CUDA%2FCPU-purple" alt="CTranslate2" />
  <img src="https://img.shields.io/badge/Model-Meta%20NLLB--200%201.3B%20INT8-orange" alt="NLLB" />
  <img src="https://img.shields.io/badge/LLM-LM%20Studio%20API-red" alt="LM Studio" />
  <img src="https://img.shields.io/badge/OCR-Vision%20LLM%20Snippet-teal" alt="Vision OCR" />
  <img src="https://img.shields.io/badge/License-MIT-brightgreen" alt="License" />
</p>

**Local Translator** is a fast, 100% private, and feature-rich desktop translation tool for Windows in the spirit of the classic *QTranslate*. It seamlessly combines high-speed offline neural machine translation (**Meta NLLB-200 1.3B INT8** via **CTranslate2**) with any local Large Language Models and Vision-Language models running in **LM Studio**.

---

## 🌟 Key Features

### 1. ⚡ Ultra-Fast Local Translation (Meta NLLB-200 1.3B)
* Runs **100% locally and offline** — zero telemetry, zero cloud data transfer.
* Accelerated by **CTranslate2** with NVIDIA CUDA (GPU) or optimized CPU INT8 execution.
* Near-instant translation with typical latencies of **30–80 ms** on modern GPUs.

### 2. 🤖 LM Studio Integration (Local LLMs)
* Connects directly to LM Studio’s OpenAI-compatible local API server (`http://127.0.0.1:1234/v1`).
* Use any loaded LLM (Qwen 2.5, DeepSeek, Llama 3, Gemma 2, Mistral, etc.) with smart translation prompting and automatic fallback.

### 3. ⚖️ Side-by-Side Dual Model Comparison (2 Models)
* Translates text with both **NLLB-200** and **LM Studio** simultaneously.
* Displays both outputs side-by-side with real-time response latency metrics in milliseconds (`⚡ ms`) and one-click copy buttons.

### 4. 📷 Screen Snippet OCR via Vision-Language LLM (`Ctrl+Shift+S`)
* Built-in snipping overlay tool with multi-monitor and High-DPI physical coordinate support.
* Drag to select any text area on your screen (PDF, video subtitles, games, scanned documents).
* The screenshot is sent directly to LM Studio's multimodal endpoint (`/v1/chat/completions`) using vision models like **Qwen2-VL**, **MiniCPM-V**, **LLaVA**, or **Phi-3.5-Vision**.
* **Two-in-One Workflow**: recognized text is instantly placed into the **Source Text** window (available for copying/editing) and automatically translated into your target language!
* Also supports pasting screenshots directly from the clipboard.

### 5. 🎯 Floating HUD at Cursor (`Ctrl+Q`) & In-Place Replacement (`Ctrl+Shift+Q`)
* **`Ctrl+Q`**: Select text anywhere in Windows (browser, chat, document) and press `Ctrl+Q` to pop up a dark-mode floating HUD with instant translation right under your cursor.
* **`Ctrl+Shift+Q`**: Instantly replaces selected text in-place with its translation.

### 6. 🌍 200+ Languages with Intelligent Search
* Full FLORES-200 language coverage (202 languages).
* Smart substring autocompletion and recent language history pinning.
* **Locale-Aware Display**: Shows English names first (`German / Deutsch (Немецкий) [de]`, sorted A–Z) when using an international UI language, and Russian first (`Немецкий / Deutsch (German) [de]`, sorted А–Я) in Russian mode.
* Dedicated quick-switch buttons for **RU**, **EN**, and **Auto**.

### 7. 🌐 12 User Interface Languages
* Fully localized GUI with on-the-fly switching in Settings:
  * 🇬🇧 English (default)
  * 🇷🇺 Русский
  * 🇩🇪 Deutsch
  * 🇫🇷 Français
  * 🇪🇸 Español
  * 🇮🇹 Italiano
  * 🇨🇳 中文 (Simplified)
  * 🇯🇵 日本語
  * 🇺🇦 Українська
  * 🇹🇷 Türkçe
  * 🇵🇱 Polski
  * 🇵🇹 Português

### 8. 🖥️ Windows Tray & Silent Background Mode
* Minimizes to the system tray on close or starts minimized on Windows boot.
* Right-click tray menu provides quick access to Translator, Screen OCR, Settings, and Cache clearing.

---

## ⌨️ Global Shortcuts

| Shortcut | Action | Description |
|---|---|---|
| <kbd>Ctrl</kbd> + <kbd>Q</kbd> | **Popup Translation** | Shows floating translation window near cursor for selected text |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Q</kbd> | **Replace In-Place** | Translates and replaces selected text directly in the active app |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | **Screen Snippet OCR** | Dims screen, captures selected rectangle, extracts text via Vision LLM & translates |
| <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | **Translate** | Triggers translation in the main window |
| <kbd>Esc</kbd> | **Dismiss / Cancel** | Closes popup, settings dialog, or cancels screen snipping |

---

## 🚀 Quick Start

### Option A: Run Pre-Built Portable Executable (Recommended)
1. Download or compile `dist/LocalTranslator/LocalTranslator.exe`.
2. Run `LocalTranslator.exe`.
3. If the NLLB model is not yet downloaded, click the **Download 1.3B Model** banner in the UI (downloads ~1.38 GB directly with pause/resume support).

### Option B: Run from Python Source

#### 1. Clone the repository
```bash
git clone https://github.com/your-username/local-translator.git
cd local-translator
```

#### 2. Create and activate a virtual environment
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.venv\Scripts\activate.bat
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Run the application
```bash
python main.py
```

---

## 🤖 Configuring LM Studio & Vision LLM OCR

### Text Translation via LM Studio
1. Launch **[LM Studio](https://lmstudio.ai/)**.
2. Download any text model (e.g. `Qwen2.5-7B-Instruct`, `Llama-3.1-8B-Instruct`, `Mistral-7B`, etc.).
3. Go to the **Developer / Local Server** tab in LM Studio and click **Start Server** (default: `http://localhost:1234`).
4. In Local Translator, choose the `LM Studio` or `2 Models` tab.

### Screen OCR with Vision Models
To use the **Screen Snippet OCR (`Ctrl+Shift+S`)** feature:
1. In LM Studio, load a multimodal Vision model:
   * **Qwen2-VL** (e.g. `Qwen2-VL-7B-Instruct-GGUF`) — *Highly recommended, outstanding multilingual OCR*
   * **MiniCPM-V 2.6**
   * **LLaVA 1.6 / LLaVA-NeXT**
   * **Phi-3.5-Vision**
2. Ensure the local server is running.
3. Press `Ctrl+Shift+S` anywhere in Windows, select any text area on your screen, and release the mouse!

---

## 📦 Building Standalone .EXE with PyInstaller

To build the self-contained portable Windows executable:

```bash
python build_exe.py
```
Or run:
```cmd
build_exe.bat
```

The output will be generated in `dist/LocalTranslator/LocalTranslator.exe`. The script automatically links your downloaded `models/` directory using an NTFS junction point (taking 0 extra disk space).

---

## 📁 Project Architecture

```
LocalTranslator/
├── app/
│   ├── config.py              # Configuration manager & JSON persistence
│   ├── languages_data.py      # 202 FLORES languages, locale-aware names & sorting
│   ├── i18n.py                # 12-language localization dictionary & tr() helper
│   ├── translator_nllb.py     # CTranslate2 NLLB 1.3B engine (CUDA/CPU)
│   ├── translator_lmstudio.py # LM Studio client (text translation & Vision OCR)
│   ├── model_downloader.py    # Resumable HuggingFace downloader with proxy support
│   ├── hotkey_service.py      # Global hotkeys (pynput + Win32 clipboard API)
│   ├── ui_snippet.py          # High-DPI screen snipping overlay widget
│   ├── ui_popup.py            # Floating cursor HUD (QTranslate style)
│   ├── ui_main.py             # Main window (Single, 2 Models comparison, OCR)
│   └── ui_tray.py             # Windows system tray service & context menu
├── models/                    # NLLB model directory (~1.38 GB, ignored by git)
├── build_app.spec             # PyInstaller specification file
├── build_exe.py               # Automated compilation script
├── download_1.3b_model.py     # Standalone CLI model downloader
├── requirements.txt           # Python package dependencies
├── config.example.json        # Template configuration file
├── LICENSE                    # MIT License
└── main.py                    # Application entry point
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🙏 Acknowledgements
* [Meta AI](https://github.com/facebookresearch/fairseq/tree/nllb) for the NLLB-200 translation models.
* [OpenNMT / CTranslate2](https://github.com/OpenNMT/CTranslate2) for the high-performance inference engine.
* [LM Studio](https://lmstudio.ai/) for the local LLM runtime and OpenAI-compatible server.
* [PyQt6](https://riverbankcomputing.com/software/pyqt/) for the GUI framework.
