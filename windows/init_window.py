from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel


class InitWindow(QWidget):
    init_loaded = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PASCAL")
        self.setAcceptDrops(True)

        # Create and set up UI elements
        self.create_ui_elements()

    def create_ui_elements(self):
        """Create and configure UI elements for the initial window."""
        layout = QVBoxLayout()

        # Instruction label
        self.label = QLabel(
            "Upload NIfTI by clicking the button below or drag & drop", self
        )
        layout.addWidget(self.label)

        # Upload button
        upload_button = QPushButton("Load Main Image")
        upload_button.clicked.connect(self.upload_file)
        layout.addWidget(upload_button)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for file uploads."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop events to load NIfTI files."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith((".nii", ".nii.gz")):
                self.transfer_file_path(file_path)
                break

    def transfer_file_path(self, file_path):
        """Emit the signal with the loaded file path."""
        self.init_loaded.emit(file_path)

    def upload_file(self):
        """Open a file dialog to upload a NIfTI file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open NIfTI File", "", "NIfTI Files (*.nii *.nii.gz)", options=options
        )
        if file_path:
            self.transfer_file_path(file_path)
