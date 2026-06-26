import os
import sys
import re
import time
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QFont

from qfluentwidgets import (
    setTheme, Theme, SubtitleLabel, BodyLabel, LineEdit, PrimaryPushButton,
    PushButton, ScrollArea, CheckBox, ComboBox, ProgressBar, TextEdit,
    CardWidget, InfoBar, InfoBarPosition, StrongBodyLabel, SwitchButton
)
from qframelesswindow import FramelessWindow


class FetchWorker(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(self.url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            ff_links = []
            for a in soup.find_all('a', href=True):
                if 'fuckingfast.co' in a['href'] and a['href'] not in ff_links:
                    ff_links.append(a['href'])
            
            self.finished_signal.emit(ff_links)
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("Network Error: Cannot reach FitGirl. Is your ISP blocking it? Try a VPN/Custom DNS.")
        except Exception as e:
            self.error_signal.emit(f"Error fetching links: {str(e)}")


class ExtractionWorker(QThread):
    progress_signal = pyqtSignal(int, str)  # current_index, message
    link_signal = pyqtSignal(str)           # resolved link or failure log
    finished_signal = pyqtSignal(str)       # completion message
    error_signal = pyqtSignal(str)          # critical error message

    def __init__(self, links, browser_name, browser_path):
        super().__init__()
        self.links = links
        self.browser_name = browser_name
        self.browser_path = browser_path
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        driver = None
        total = len(self.links)
        
        self.progress_signal.emit(0, f"Initializing using {self.browser_name} to bypass Cloudflare...")
        
        def create_driver(version=None):
            if self.browser_name.lower() == 'firefox':
                opts = FirefoxOptions()
                opts.binary_location = self.browser_path
                opts.set_preference("dom.webdriver.enabled", False)
                opts.set_preference("useAutomationExtension", False)
                return webdriver.Firefox(options=opts)
                
            elif self.browser_name.lower() == 'msedge':
                opts = EdgeOptions()
                opts.binary_location = self.browser_path
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                opts.add_experimental_option('useAutomationExtension', False)
                opts.add_argument("--disable-blink-features=AutomationControlled")
                return webdriver.Edge(options=opts)
                
            else:
                # Chrome and Brave use undetected-chromedriver
                opts = uc.ChromeOptions()
                return uc.Chrome(
                    options=opts, 
                    use_subprocess=True, 
                    browser_executable_path=self.browser_path, 
                    version_main=version
                )

        try:
            try:
                driver = create_driver()
            except Exception as e:
                error_msg = str(e)
                if self.browser_name.lower() not in ['firefox', 'msedge'] and "Current browser version is" in error_msg:
                    match = re.search(r"Current browser version is (\d+)", error_msg)
                    if match:
                        correct_version = int(match.group(1))
                        self.progress_signal.emit(0, f"Auto-fixing ChromeDriver version to v{correct_version}...")
                        driver = create_driver(version=correct_version)
                    else:
                        raise e
                else:
                    raise e
            
            for i, link in enumerate(self.links, 1):
                if not self._is_running:
                    break
                    
                filename = link.split('#')[-1] if '#' in link else link.split('/')[-1]
                self.progress_signal.emit(i - 1, f"Processing [{i}/{total}]: {filename}")
                
                try:
                    driver.get(link)
                    direct_url = None
                    for _ in range(25):
                        if not self._is_running:
                            break
                        time.sleep(1)
                        match = re.search(r'window\.open\("([^"]+)"\)', driver.page_source)
                        if match:
                            direct_url = match.group(1)
                            break
                            
                    if direct_url:
                        self.link_signal.emit(direct_url)
                    else:
                        self.link_signal.emit(f"# FAILED: {filename} ({link})")
                        
                except Exception as e:
                    self.link_signal.emit(f"# ERROR: {str(e)} -> {filename}")

            if self._is_running:
                self.finished_signal.emit(f"Extraction complete! Processed {total} links.")
            else:
                self.finished_signal.emit("Extraction cancelled.")
            
        except Exception as e:
            self.error_signal.emit(f"Critical Error: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass


class FitgirlExtractorApp(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FitGirl Helper Redesigned")
        self.resize(700, 800)
        self.setMinimumSize(550, 680)
        
        # Configure global theme to LIGHT by default
        setTheme(Theme.LIGHT)
        self.setStyleSheet("FitgirlExtractorApp { background-color: #f3f3f3; }")
        
        self.checkbox_widgets = {}  # {url: CheckBox}
        self.fetch_worker = None
        self.extract_worker = None

        # Keep titleBar raised above layout
        self.titleBar.raise_()
        
        # Setup layouts
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, self.titleBar.height() + 10, 20, 20)
        self.main_layout.setSpacing(15)

        self.setup_ui()

    def setup_ui(self):
        # 1. Main Subtitle Header
        self.title_label = SubtitleLabel("FitGirl Helper Redesigned", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # 2. Input Frame Card
        self.input_card = CardWidget(self)
        input_layout = QVBoxLayout(self.input_card)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(10)
        
        url_label = StrongBodyLabel("FitGirl Game URL:", self.input_card)
        input_layout.addWidget(url_label)
        
        url_h_layout = QHBoxLayout()
        self.url_entry = LineEdit(self.input_card)
        self.url_entry.setText("https://fitgirl-repacks.site/grand-theft-auto-v/")
        self.url_entry.setPlaceholderText("Enter FitGirl repack URL here...")
        url_h_layout.addWidget(self.url_entry)
        
        self.fetch_btn = PrimaryPushButton("1. Fetch Links", self.input_card)
        self.fetch_btn.clicked.connect(self.start_fetch)
        url_h_layout.addWidget(self.fetch_btn)
        
        input_layout.addLayout(url_h_layout)
        self.main_layout.addWidget(self.input_card)

        # 3. Status Label
        self.status_label = BodyLabel("Waiting for input...", self)
        self.status_label.setStyleSheet("color: #555; font-style: italic;")
        self.main_layout.addWidget(self.status_label)

        # 4. Checklist Frame Card
        self.checklist_card = CardWidget(self)
        checklist_layout = QVBoxLayout(self.checklist_card)
        checklist_layout.setContentsMargins(15, 15, 15, 15)
        checklist_layout.setSpacing(10)
        
        parts_label = StrongBodyLabel("Found Parts (Uncheck unwanted)", self.checklist_card)
        checklist_layout.addWidget(parts_label)
        
        # Scroll area for dynamic checklist
        self.scroll_area = ScrollArea(self.checklist_card)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(180)
        
        self.scroll_content = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_content_layout.setSpacing(5)
        self.scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        checklist_layout.addWidget(self.scroll_area)
        
        # Controls panel inside card
        ctrl_layout = QHBoxLayout()
        self.select_all_btn = PushButton("Select All", self.checklist_card)
        self.select_all_btn.clicked.connect(self.select_all)
        ctrl_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = PushButton("Deselect All", self.checklist_card)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        ctrl_layout.addWidget(self.deselect_all_btn)
        
        ctrl_layout.addSpacing(10)
        
        self.browser_combo = ComboBox(self.checklist_card)
        self.browser_combo.addItems([
            "Auto-Detect Browser", 
            "Google Chrome", 
            "Microsoft Edge", 
            "Brave", 
            "Mozilla Firefox"
        ])
        self.browser_combo.setCurrentIndex(0)
        ctrl_layout.addWidget(self.browser_combo)
        
        self.extract_btn = PrimaryPushButton("2. Extract Selected", self.checklist_card)
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)
        ctrl_layout.addWidget(self.extract_btn)
        
        checklist_layout.addLayout(ctrl_layout)
        self.main_layout.addWidget(self.checklist_card)

        # 5. Progress Bar
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)

        # 6. Output Links Frame Card
        self.output_card = CardWidget(self)
        output_layout = QVBoxLayout(self.output_card)
        output_layout.setContentsMargins(15, 15, 15, 15)
        output_layout.setSpacing(10)
        
        output_label = StrongBodyLabel("Extracted Direct Links", self.output_card)
        output_layout.addWidget(output_label)
        
        self.text_area = TextEdit(self.output_card)
        self.text_area.setReadOnly(True)
        self.text_area.setPlaceholderText("Extracted links will appear here...")
        self.text_area.setFont(QFont("Consolas", 10))
        output_layout.addWidget(self.text_area)
        
        self.main_layout.addWidget(self.output_card)

        # 7. Actions Bar
        btn_h_layout = QHBoxLayout()
        
        # Toggle Theme Switch (starts in Light mode)
        theme_layout = QHBoxLayout()
        self.theme_label = BodyLabel("Dark Mode", self)
        self.theme_switch = SwitchButton(self)
        self.theme_switch.setOnText("On")
        self.theme_switch.setOffText("Off")
        self.theme_switch.setChecked(False)
        self.theme_switch.checkedChanged.connect(self.on_theme_switch_changed)
        theme_layout.addWidget(self.theme_label)
        theme_layout.addWidget(self.theme_switch)
        btn_h_layout.addLayout(theme_layout)
        
        btn_h_layout.addStretch(1)
        
        self.clear_btn = PushButton("Clear Output", self)
        self.clear_btn.clicked.connect(self.clear_output)
        btn_h_layout.addWidget(self.clear_btn)
        
        self.copy_btn = PrimaryPushButton("📋 Copy All Links", self)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_h_layout.addWidget(self.copy_btn)
        
        self.main_layout.addLayout(btn_h_layout)

    # --- Theme Toggling ---

    def on_theme_switch_changed(self, checked):
        if checked:
            setTheme(Theme.DARK)
            self.setStyleSheet("FitgirlExtractorApp { background-color: #202020; }")
            self.status_label.setStyleSheet("color: #aaa; font-style: italic;")
        else:
            setTheme(Theme.LIGHT)
            self.setStyleSheet("FitgirlExtractorApp { background-color: #f3f3f3; }")
            self.status_label.setStyleSheet("color: #555; font-style: italic;")

    # --- Checklist Logic ---

    def select_all(self):
        for cb in self.checkbox_widgets.values():
            cb.setChecked(True)

    def deselect_all(self):
        for cb in self.checkbox_widgets.values():
            cb.setChecked(False)

    # --- Actions Logic ---

    def clear_output(self):
        self.text_area.clear()
        self.progress_bar.setValue(0)

    def copy_to_clipboard(self):
        links = self.text_area.toPlainText().strip()
        if links:
            clipboard = QApplication.clipboard()
            clipboard.setText(links)
            InfoBar.success(
                title='Success',
                content="All links copied to clipboard!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            InfoBar.warning(
                title='Empty',
                content="No links to copy!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    # --- Browser Discovery ---

    def get_browser_path(self, selected_browser):
        import sys
        browser_paths = {
            "Google Chrome": [
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/var/lib/flatpak/exports/bin/com.google.Chrome"
            ],
            "Microsoft Edge": [
                r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
                r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge"
            ],
            "Brave": [
                r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe",
                "/usr/bin/brave-browser",
                "/usr/bin/brave",
                "/var/lib/flatpak/exports/bin/com.brave.Browser"
            ],
            "Mozilla Firefox": [
                r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
                r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
                r"%LocalAppData%\Mozilla Firefox\firefox.exe",
                "/usr/bin/firefox",
                "/var/lib/flatpak/exports/bin/org.mozilla.firefox"
            ]
        }
        
        if selected_browser != "Auto-Detect Browser":
            paths_to_check = browser_paths.get(selected_browser, [])
        else:
            paths_to_check = []
            for paths in browser_paths.values():
                paths_to_check.extend(paths)

        for path in paths_to_check:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                return expanded_path
        return None

    # --- Fetching Trigger ---

    def start_fetch(self):
        url = self.url_entry.text().strip()
        if not url:
            InfoBar.error(
                title='Error',
                content="Please enter a valid FitGirl URL.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        self.fetch_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.status_label.setText("Fetching page...")
        
        # Clear checklist widget items
        while self.scroll_content_layout.count():
            item = self.scroll_content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.checkbox_widgets.clear()
        
        self.fetch_worker = FetchWorker(url)
        self.fetch_worker.finished_signal.connect(self.on_fetch_success)
        self.fetch_worker.error_signal.connect(self.on_fetch_error)
        self.fetch_worker.start()

    def on_fetch_success(self, links):
        self.fetch_btn.setEnabled(True)
        if not links:
            self.status_label.setText("No FuckingFast links found on this page!")
            return
            
        for link in links:
            filename = link.split('#')[-1] if '#' in link else link.split('/')[-1]
            cb = CheckBox(filename, self.scroll_content)
            cb.setChecked(True)
            self.scroll_content_layout.addWidget(cb)
            self.checkbox_widgets[link] = cb
            
        self.status_label.setText(f"Found {len(links)} parts. Select what you need and click Extract.")
        self.extract_btn.setEnabled(True)

    def on_fetch_error(self, err_msg):
        self.fetch_btn.setEnabled(True)
        self.status_label.setText(err_msg)
        InfoBar.error(
            title='Fetch Failed',
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

    # --- Extraction Trigger ---

    def start_extraction(self):
        selected_links = [url for url, cb in self.checkbox_widgets.items() if cb.isChecked()]
        if not selected_links:
            InfoBar.warning(
                title='Warning',
                content="No links selected to extract!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
            
        self.fetch_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.clear_output()
        
        selected_browser = self.browser_combo.currentText()
        browser_executable = self.get_browser_path(selected_browser)
        
        if not browser_executable:
            self.status_label.setText(f"Error: Could not find {selected_browser} on your system.")
            self.fetch_btn.setEnabled(True)
            self.extract_btn.setEnabled(True)
            InfoBar.error(
                title='Browser Not Found',
                content=f"Could not find {selected_browser} on your system.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            return
            
        self.progress_bar.setRange(0, len(selected_links))
        self.progress_bar.setValue(0)
        
        browser_name = os.path.basename(browser_executable).replace('.exe', '')
        
        self.extract_worker = ExtractionWorker(selected_links, browser_name, browser_executable)
        self.extract_worker.progress_signal.connect(self.on_extract_progress)
        self.extract_worker.link_signal.connect(self.on_extract_link)
        self.extract_worker.finished_signal.connect(self.on_extract_finished)
        self.extract_worker.error_signal.connect(self.on_extract_error)
        self.extract_worker.start()

    def on_extract_progress(self, val, msg):
        self.status_label.setText(msg)
        self.progress_bar.setValue(val)

    def on_extract_link(self, link_text):
        self.text_area.append(link_text)
        self.text_area.ensureCursorVisible()

    def on_extract_finished(self, msg):
        self.status_label.setText(msg)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.fetch_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        InfoBar.success(
            title='Extraction Finished',
            content=msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

    def on_extract_error(self, err_msg):
        self.status_label.setText(err_msg)
        self.fetch_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        InfoBar.error(
            title='Extraction Failed',
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

    def closeEvent(self, event):
        if self.extract_worker and self.extract_worker.isRunning():
            self.extract_worker.stop()
            self.extract_worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FitgirlExtractorApp()
    window.show()
    sys.exit(app.exec())
