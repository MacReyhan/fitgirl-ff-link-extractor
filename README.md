# FitGirl Helper Redesigned

![GitHub Repo stars](https://img.shields.io/github/stars/MacReyhan/fitgirl_helper_redesigned?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/MacReyhan/fitgirl_helper_redesigned?style=flat-square)
![GitHub license](https://img.shields.io/github/license/MacReyhan/fitgirl_helper_redesigned?style=flat-square)

A modern, sleek desktop utility application built in Python and styled with the Microsoft WinUI 3 / Fluent Design system using QFluentWidgets. 

It provides a highly interactive and threaded GUI to easily search, filter, and extract direct download links from FuckingFast file hosters on FitGirl repack pages, bypassing Cloudflare Turnstile verification seamlessly.

---

## 🌟 Features

- **Fluent UI 3 Design**: Fully redesigned interface matching Windows 11 aesthetics, using rounded cards, smooth hover animations, and clean layouts.
- **Dynamic Theme Toggling**: Includes a built-in toggle switch to swap between **Light Mode** and **Dark Mode** on the fly.
- **Smart Filtering Checklist**: Instantly parses and lists all available setup files, language packs, and optional parts in an interactive list. Select exactly what you need and skip what you don't.
- **Cloudflare Bypass**: Employs an undetected browser process (`undetected-chromedriver`) to automatically handle Turnstile checks in the background.
- **Multi-threaded Core**: Utilizes PyQt6 `QThread` and signal-slot mechanisms to isolate scraping and automation tasks from the UI, keeping the application fast and responsive.
- **High-DPI Support**: Automatically scales crisp fonts and icons based on your display settings.
- **Copy-to-Clipboard**: Copy all resolved direct download URLs with a single click, ready for import into download managers like **JDownloader 2**, **IDM**, or **Free Download Manager**.
- **Process Protection**: Automatically terminates background webdriver processes upon closing the window to prevent orphaned memory/process leaks.

---

## 🛠️ Requirements & Prerequisites

Before running the application, make sure you have:
1. **Python 3.8 or higher** installed.
2. A compatible Chromium-based browser installed (**Google Chrome**, **Brave**, or **Microsoft Edge**) or **Mozilla Firefox**.
3. **Active internet connection** (a VPN or custom DNS is recommended if your ISP blocks access to FitGirl repack sites).

---

## 🚀 Getting Started

### 1. Installation & Environment Setup

Clone this repository to your machine and navigate to the directory:
```bash
git clone https://github.com/MacReyhan/fitgirl_helper_redesigned.git
cd fitgirl_helper_redesigned
```

Create and activate a Python virtual environment (optional but recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Running the Application

Start the program using python:
```bash
python ff_grabber.py
```

---

## 📦 Building a Standalone Executable

If you want to package the application into a single `.exe` executable for Windows, you can compile it using **PyInstaller**:

1. Install PyInstaller in your environment:
   ```bash
   pip install pyinstaller
   ```
2. Build the executable with the following command:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --name="FitgirlHelperRedesigned" ff_grabber.py
   ```
3. The packaged executable will be generated inside the `dist/` directory as `FitgirlHelperRedesigned.exe`.

---

## 🤖 CI/CD Automation

This repository includes a pre-configured **GitHub Actions CI/CD workflow** located at `.github/workflows/build-exe.yml`. 

- Every time you push a change to the `main` branch or create a pull request, the workflow automatically spins up a Windows runner, installs the necessary dependencies, builds a standalone executable, and uploads the built `.exe` as a downloadable artifact.
- You can also manually trigger the build from the "Actions" tab of the repository on GitHub.

---

## 📝 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.

---

## 🤝 Credits & Acknowledgements

- **FitGirl Repacks** - for providing a catalog of compressed repack pages.
- **QFluentWidgets** - for the gorgeous WinUI 3 style Qt components.
- **Undetected-chromedriver & Selenium** - for standard-setting browser automation tools.
- **BeautifulSoup4** - for lightweight HTML parsing.
