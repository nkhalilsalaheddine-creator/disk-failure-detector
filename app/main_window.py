"""
main_window.py
PyQt6 main window — two pages via QStackedWidget.
Page 0: Disk selection + scan
Page 1: Prediction result + feature breakdown table
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QGroupBox, QStackedWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from scanner import get_connected_disks, scan_disk
from predictor import Predictor


# ─────────────────────────────────────────────
# Background worker thread
# ─────────────────────────────────────────────
class ScanWorker(QThread):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, disk_path: str):
        super().__init__()
        self.disk_path = disk_path

    def run(self):
        try:
            self.finished.emit(scan_disk(self.disk_path))
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, predictor: Predictor):
        super().__init__()
        self.predictor = predictor
        self.worker    = None

        self.setWindowTitle("SMART Disk Failure Predictor")
        self.setMinimumSize(900, 700)
        self._apply_stylesheet()
        self._build_ui()
        self._refresh_disk_list()

    # ── Stylesheet ───────────────────────────────
    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0d1117;
                color: #e6edf3;
                font-family: 'Courier New', monospace;
            }
            QGroupBox {
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                font-size: 11px;
                color: #8b949e;
                letter-spacing: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QPushButton {
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 18px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #58a6ff;
            }
            QPushButton:pressed { background-color: #1f6feb; }
            QPushButton:disabled { color: #484f58; border-color: #21262d; }
            QPushButton#scan_btn {
                background-color: #1f6feb;
                border-color: #1f6feb;
                font-size: 13px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton#scan_btn:hover { background-color: #388bfd; }
            QPushButton#nav_btn {
                background-color: #21262d;
                border-color: #30363d;
                font-size: 12px;
                padding: 8px 20px;
            }
            QPushButton#nav_btn:hover {
                border-color: #58a6ff;
                color: #58a6ff;
            }
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: #e6edf3;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background-color: #21262d;
                border: 1px solid #30363d;
                selection-background-color: #1f6feb;
            }
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
                font-size: 11px;
            }
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:selected { background-color: #1f3a5f; }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                border: none;
                border-bottom: 1px solid #30363d;
                padding: 6px 10px;
                font-size: 10px;
                letter-spacing: 1px;
            }
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #1f6feb; border-radius: 4px; }
            QScrollBar:vertical { background: #0d1117; width: 8px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; }
        """)

    # ── Root UI (header + stacked pages) ────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(self._build_header())

        # Stacked widget holds the two pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_page_scan())      # index 0
        self.stack.addWidget(self._build_page_results())   # index 1
        root.addWidget(self.stack)

        # Status bar
        self.status_label = QLabel("Ready. Select a disk and press SCAN.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        root.addWidget(self.status_label)

    # ── Shared header ────────────────────────────
    def _build_header(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("◈ SMART DISK FAILURE PREDICTOR")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff; letter-spacing: 3px;")
        layout.addWidget(title)
        layout.addStretch()

        subtitle = QLabel("powered by Random Forest · Backblaze dataset")
        subtitle.setStyleSheet("font-size: 10px; color: #484f58; letter-spacing: 1px;")
        layout.addWidget(subtitle)

        return widget

    # ── Page 0: Scan ─────────────────────────────
    def _build_page_scan(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # Disk selection group
        group = QGroupBox("Disk Selection")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        # Auto-detect row
        auto_row = QHBoxLayout()
        auto_label = QLabel("Auto-detected disk:")
        auto_label.setFixedWidth(150)
        auto_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.disk_combo = QComboBox()
        self.disk_combo.setMinimumWidth(280)
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._refresh_disk_list)
        auto_row.addWidget(auto_label)
        auto_row.addWidget(self.disk_combo)
        auto_row.addWidget(refresh_btn)
        auto_row.addStretch()
        group_layout.addLayout(auto_row)

        # Scan button + progress bar
        action_row = QHBoxLayout()
        self.scan_btn = QPushButton("▶  SCAN DISK")
        self.scan_btn.setObjectName("scan_btn")
        self.scan_btn.setFixedHeight(42)
        self.scan_btn.clicked.connect(self._start_scan)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        action_row.addWidget(self.scan_btn)
        action_row.addWidget(self.progress_bar)
        action_row.addStretch()
        group_layout.addLayout(action_row)

        layout.addWidget(group)
        layout.addStretch()

        return page

    # ── Page 1: Results ──────────────────────────
    def _build_page_results(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # ← Back button at top
        nav_row = QHBoxLayout()
        self.back_btn = QPushButton("←  Back to Scan")
        self.back_btn.setObjectName("nav_btn")
        self.back_btn.setFixedWidth(160)
        self.back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        nav_row.addWidget(self.back_btn)
        nav_row.addStretch()
        layout.addLayout(nav_row)

        # Result summary panel
        layout.addWidget(self._build_result_panel())

        # Feature breakdown table
        layout.addWidget(self._build_breakdown_table())

        return page

    # ── Result summary widget ────────────────────
    def _build_result_panel(self) -> QGroupBox:
        group = QGroupBox("Prediction Result")
        layout = QHBoxLayout(group)
        layout.setSpacing(20)

        self.verdict_badge = QLabel("—")
        self.verdict_badge.setFixedSize(120, 120)
        self.verdict_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_badge.setStyleSheet(
            "font-size: 20px; font-weight: bold; border-radius: 60px; border: 3px solid #30363d;"
        )
        layout.addWidget(self.verdict_badge)

        details = QVBoxLayout()
        self.disk_name_label  = QLabel("")
        self.disk_name_label.setStyleSheet("font-size: 14px; color: #e6edf3;")
        self.disk_path_label  = QLabel("")
        self.disk_path_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        self.confidence_label = QLabel("")
        self.confidence_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.confidence_bar   = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setFixedHeight(8)
        self.confidence_bar.setTextVisible(False)
        self.verdict_label    = QLabel("")
        self.verdict_label.setWordWrap(True)
        self.verdict_label.setStyleSheet("font-size: 12px; color: #e6edf3;")

        details.addWidget(self.disk_name_label)
        details.addWidget(self.disk_path_label)
        details.addSpacing(6)
        details.addWidget(self.confidence_label)
        details.addWidget(self.confidence_bar)
        details.addSpacing(6)
        details.addWidget(self.verdict_label)
        details.addStretch()
        layout.addLayout(details)

        return group

    # ── Breakdown table widget ───────────────────
    def _build_breakdown_table(self) -> QGroupBox:
        group = QGroupBox("Feature Breakdown  (sorted by model importance)")
        layout = QVBoxLayout(group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["SMART ATTRIBUTE", "VALUE", "IMPORTANCE %", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(300)

        layout.addWidget(self.table)
        return group

    # ── Logic ────────────────────────────────────
    def _refresh_disk_list(self):
        self.disk_combo.clear()
        disks = get_connected_disks()
        if disks:
            self.disk_combo.addItems(disks)
            self.status_label.setText(f"Found {len(disks)} disk(s). Select one and press SCAN.")
        else:
            self.disk_combo.addItem("No disks detected")
            self.status_label.setText("No disks auto-detected. Check smartctl installation.")

    def _get_selected_disk(self) -> str | None:
        val = self.disk_combo.currentText()
        return val if val and val != "No disks detected" else None

    def _start_scan(self):
        disk_path = self._get_selected_disk()
        if not disk_path:
            QMessageBox.warning(self, "No Disk Selected", "Please select a disk from the list.")
            return

        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"Scanning {disk_path} via smartctl...")

        self.worker = ScanWorker(disk_path)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()

    def _on_scan_finished(self, scan_row):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)

        try:
            result = self.predictor.predict(scan_row)
        except Exception as e:
            self._on_scan_error(f"Prediction failed: {e}")
            return

        self._populate_results(result)
        self.status_label.setText(f"Scan complete — {result['disk_name']} ({result['disk_path']})")

        # Automatically navigate to results page
        self.stack.setCurrentIndex(1)

    def _on_scan_error(self, message: str):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.status_label.setText(f"Error: {message}")
        QMessageBox.critical(self, "Scan Error", message)

    def _populate_results(self, result: dict):
        is_failed  = result['label'] == 'Failed'
        confidence = result['confidence']

        if is_failed:
            badge_style = ("font-size: 18px; font-weight: bold; border-radius: 60px;"
                           "background-color: #3d1c1c; color: #f85149; border: 3px solid #f85149;")
            badge_text = "✕\nFAILED"
            bar_color  = "#f85149"
        else:
            badge_style = ("font-size: 18px; font-weight: bold; border-radius: 60px;"
                           "background-color: #122d22; color: #3fb950; border: 3px solid #3fb950;")
            badge_text = "✓\nHEALTHY"
            bar_color  = "#3fb950"

        self.verdict_badge.setStyleSheet(badge_style)
        self.verdict_badge.setText(badge_text)
        self.verdict_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.disk_name_label.setText(result['disk_name'])
        self.disk_path_label.setText(result['disk_path'])
        self.confidence_label.setText(f"Confidence: {confidence*100:.1f}%")
        self.confidence_label.setStyleSheet(f"font-size: 12px; color: {bar_color};")
        self.confidence_bar.setValue(int(confidence * 100))
        self.confidence_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #21262d; border: 1px solid #30363d; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 4px; }}
        """)
        self.verdict_label.setText(result['verdict'])

        # Populate table
        breakdown = result['breakdown']
        self.table.setRowCount(len(breakdown))

        for row_idx, entry in enumerate(breakdown):
            name_item = QTableWidgetItem(entry['label'])
            if entry['is_critical']:
                name_item.setForeground(QColor("#e3b341"))
            self.table.setItem(row_idx, 0, name_item)

            val = entry['value']
            val_text = f"{val:.0f}" if val == int(val) else f"{val:.4f}"
            val_item = QTableWidgetItem(val_text)
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, val_item)

            imp_item = QTableWidgetItem(f"{entry['importance']:.2f}%")
            imp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, imp_item)

            if entry['is_triggered']:
                status_item = QTableWidgetItem("⚠  TRIGGERED")
                status_item.setForeground(QColor("#f85149"))
            elif entry['is_critical']:
                status_item = QTableWidgetItem("✓  OK")
                status_item.setForeground(QColor("#3fb950"))
            else:
                status_item = QTableWidgetItem("—")
                status_item.setForeground(QColor("#484f58"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, status_item)
