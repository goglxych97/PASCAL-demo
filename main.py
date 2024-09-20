# main.py
from windows.init_window import InitWindow
from windows.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
import sys

def main():
    app = QApplication(sys.argv)
    init_window = InitWindow()
    main_window = None

    def launch_main_window(nifti_file_path):
        global main_window
        init_window.close()
        main_window = MainWindow(nifti_file_path)
        main_window.show()

    init_window.nifti_loaded.connect(launch_main_window)
    init_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
