# main_window.py
from canvas.canvas import Canvas
from menu.file import load_image_dialog, load_segmentation_dialog, save_segmentation_dialog
from PyQt5.QtWidgets import (
    QAction, QComboBox, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QVBoxLayout, QWidget, QDialog
)
import numpy as np
import nibabel as nib

class MainWindow(QMainWindow):
    def __init__(self, nifti_file_path=None):
        super().__init__()
        self.setWindowTitle("PASCAL")
        self.setMinimumSize(960, 400)
        self.resize(960, 400)

        self.init_ui()
        self.setAcceptDrops(True)

        if nifti_file_path: # Initial Launch
            self.load_nifti_file(nifti_file_path)

    def init_ui(self):
        self.canvas_axial = Canvas()
        self.canvas_coronal = Canvas()
        self.canvas_sagittal = Canvas()
        
        # Canvas에서 slice 요청 시 처리
        self.canvas_axial.request_slice.connect(self.provide_slice_data)
        self.canvas_coronal.request_slice.connect(self.provide_slice_data)
        self.canvas_sagittal.request_slice.connect(self.provide_slice_data)

        self.nifti_array = None
        self.nifti_affine = None
        self.nifti_header = None
        self.segmentation_matrix = None

        self.connect_signal()
        self.create_menu()

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(self.create_button_layout())
        layout.addLayout(self.create_canvas_layout())
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def provide_slice_data(self, slice_index):
        """Canvas가 요청할 때 제공할 데이터"""
        if self.nifti_array is not None and self.segmentation_matrix is not None:
            for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
                if canvas.current_slice_index == slice_index:
                    nifti_slice = self.nifti_array[:, :, slice_index]
                    segmentation_slice = self.segmentation_matrix[:, :, slice_index]
                    canvas.set_slice_data(nifti_slice, segmentation_slice)

    def create_button_layout(self):
        brush_size_label = QLabel("Brush Size:")
        brush_size_dropdown = QComboBox()
        brush_sizes = ['1px', '2px', '4px', '8px', '16px', '32px']
        brush_size_dropdown.addItems(brush_sizes)
        brush_size_dropdown.setCurrentIndex(3)  # Default: '8px'
        brush_size_dropdown.currentIndexChanged.connect(self.change_brush_size)

        brush_color_label = QLabel("Brush Color:")
        brush_color_dropdown = QComboBox()
        brush_colors = ['Clear', 'Red', 'Green', 'Blue', 'Yellow', 'Sky Blue', 'Purple']
        brush_color_dropdown.addItems(brush_colors)
        brush_color_dropdown.setCurrentIndex(1)  # Default: 'Red'
        brush_color_dropdown.currentIndexChanged.connect(self.change_brush_color)

        clear_all_button = QPushButton("Clear All")
        clear_all_button.clicked.connect(self.clear_all_segmentations)

        button_layout = QHBoxLayout()
        button_layout.addWidget(brush_size_label)
        button_layout.addWidget(brush_size_dropdown)
        button_layout.addWidget(brush_color_label)
        button_layout.addWidget(brush_color_dropdown)
        button_layout.addWidget(clear_all_button)

        return button_layout

    def create_canvas_layout(self):
        canvas_layout = QHBoxLayout()
        canvas_layout.addWidget(self.canvas_axial)
        canvas_layout.addWidget(self.canvas_coronal)
        canvas_layout.addWidget(self.canvas_sagittal)

        return canvas_layout

    def connect_signal(self):
        self.canvas_axial.segmentation_updated.connect(self.update_all_canvases)
        self.canvas_coronal.segmentation_updated.connect(self.update_all_canvases)
        self.canvas_sagittal.segmentation_updated.connect(self.update_all_canvases)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if file_paths:
                self.drag_drop_dialog(file_paths[0])

    def drag_drop_dialog(self, file_paths):
        popup = QDialog(self)
        popup.setWindowTitle("Quick Action Dialog")
        popup.setFixedSize(300, 200)
        layout = QVBoxLayout(popup)
        button_LoadMainImage = QPushButton(f"Load Main Image")
        button_LoadMainImage.clicked.connect(lambda: self.handle_button_click(popup, self.load_nifti_file, file_paths))
        layout.addWidget(button_LoadMainImage)
        button_LoadSegmentation = QPushButton(f"Load Segmentation")
        button_LoadSegmentation.clicked.connect(lambda: self.handle_button_click(popup, self.load_segmentation_file, file_paths[0]))
        layout.addWidget(button_LoadSegmentation)

        popup.exec_()

    def handle_button_click(self, dialog, function, file_path):
        function(file_path)
        dialog.accept()

    def update_all_canvases(self):
        for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
            canvas.update_slice()

    def create_menu(self):
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu('File')

        load_nifti_action = QAction('Load Main Image', self)
        load_nifti_action.triggered.connect(self.load_nifti)
        file_menu.addAction(load_nifti_action)

        load_segmentation_action = QAction('Load Segmentation', self)
        load_segmentation_action.triggered.connect(self.load_segmentation)
        file_menu.addAction(load_segmentation_action)

        save_nifti_action = QAction('Save Segmentation', self)
        save_nifti_action.triggered.connect(self.save_segmentation)
        file_menu.addAction(save_nifti_action)

    def load_nifti(self):
        file_path = load_image_dialog(self)
        if file_path:
            self.load_nifti_file(file_path)

    def load_nifti_file(self, file_path):
        try:
            nifti_data = nib.load(file_path)
            self.nifti_array = nib.as_closest_canonical(nifti_data).get_fdata()
            self.nifti_affine = nifti_data.affine
            self.nifti_header = nifti_data.header
            self.segmentation_matrix = np.zeros_like(self.nifti_array, dtype=np.int32)
            for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
                canvas.set_background_image_from_nifti(self.nifti_array.shape)  # Shape 정보만 전달

        except Exception as e:
            print(f"Failed to load Image: {e}")

    def save_segmentation(self):
        save_segmentation_dialog(
            self,
            self.segmentation_matrix,
            self.nifti_affine,
            self.nifti_header
        )

    def load_segmentation(self):
        file_path = load_segmentation_dialog(self)
        if file_path:
            self.load_segmentation_file(file_path)

    def load_segmentation_file(self, file_path):
        try:
            segmentation_matrix = nib.load(file_path).get_fdata()
            if segmentation_matrix.shape == self.nifti_array.shape:
                self.segmentation_matrix = segmentation_matrix
                self.update_all_canvases()
            else:
                print("Error: The dimensions of the segmentation file do not match the current Image.")
        except Exception as e:
            print(f"Failed to load Segmentation: {e}")

    def change_brush_size(self, index):
        brush_sizes = [1, 2, 4, 8, 16, 32]
        brush_size = brush_sizes[index]
        for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
            canvas.set_brush_size(brush_size)

    def change_brush_color(self, index):
        brush_color_values = [0, 1, 2, 3, 4, 5, 6]
        brush_color_value = brush_color_values[index]
        for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
            canvas.set_brush_color_value(brush_color_value)

    def clear_all_segmentations(self):
        if self.segmentation_matrix is not None:
            self.segmentation_matrix.fill(0)
        for canvas in [self.canvas_axial, self.canvas_coronal, self.canvas_sagittal]:
            canvas.clear_all_segmentations()
