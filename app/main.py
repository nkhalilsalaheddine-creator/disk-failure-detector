"""
main.py
Entry point for the SMART Disk Failure Predictor app.
Run with: python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow
from predictor import Predictor


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SMART Disk Failure Predictor")

    # Load model — show friendly error if missing
    try:
        predictor = Predictor(model_path='../model/disk_model.pkl')
    except FileNotFoundError as e:
        err = QMessageBox()
        err.setWindowTitle("Model Not Found")
        err.setText(str(e))
        err.setIcon(QMessageBox.Icon.Critical)
        err.exec()
        sys.exit(1)

    window = MainWindow(predictor=predictor)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
