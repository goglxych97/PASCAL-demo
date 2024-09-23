# main_window.py
from canvas.canvas import Canvas
from menu.file import (
    load_image_dialog,
    load_segmentation_dialog,
    save_segmentation_dialog,
)
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDialog,
)
import numpy as np
import nibabel as nib


class MainWindow(QMainWindow):
    def __init__(self, init_file_path=None):
        super().__init__()
        self.setWindowTitle("PASCAL")
        self.setMinimumSize(960, 400)
        self.resize(960, 400)
        self.setAcceptDrops(True)

        self.canvas_list = [
            [Canvas(view="axial"), Canvas(view="coronal"), Canvas(view="sagittal")]
        ]

        self.nifti_affine = None
        self.nifti_header = None

        self.nifti_array = None
        self.segmentation_array = None

        self.connect_signal()
        self.create_menu()
        self.create_ui_elements()

        if init_file_path:  # Initial Launch
            self.load_nifti_file(init_file_path)

    def create_ui_elements(self):
        brush_size_label = QLabel("Brush Size:")
        brush_size_dropdown = QComboBox()
        brush_sizes = ["1px", "2px", "4px", "8px", "16px", "32px"]
        brush_size_dropdown.addItems(brush_sizes)
        brush_size_dropdown.setCurrentIndex(3)
        brush_size_dropdown.currentIndexChanged.connect(self.change_brush_size)

        brush_color_label = QLabel("Brush Color:")
        brush_color_dropdown = QComboBox()
        brush_colors = ["Clear", "Red", "Green", "Blue", "Yellow", "Sky Blue", "Purple"]
        brush_color_dropdown.addItems(brush_colors)
        brush_color_dropdown.setCurrentIndex(1)
        brush_color_dropdown.currentIndexChanged.connect(self.change_brush_color)

        clear_all_button = QPushButton("Clear All")
        clear_all_button.clicked.connect(self.clear_all_segmentations)

        button_layout = QHBoxLayout()
        button_layout.addWidget(brush_size_label)
        button_layout.addWidget(brush_size_dropdown)
        button_layout.addWidget(brush_color_label)
        button_layout.addWidget(brush_color_dropdown)
        button_layout.addWidget(clear_all_button)

        canvas_layout = QHBoxLayout()
        for canvas in self.canvas_list[0]:
            canvas_layout.addWidget(canvas)

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addLayout(canvas_layout)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def create_menu(self):
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu("File")

        load_nifti_action = QAction("Load Main Image", self)
        load_nifti_action.triggered.connect(self.load_nifti)
        file_menu.addAction(load_nifti_action)

        load_segmentation_action = QAction("Load Segmentation", self)
        load_segmentation_action.triggered.connect(self.load_segmentation)
        file_menu.addAction(load_segmentation_action)

        save_nifti_action = QAction("Save Segmentation", self)
        save_nifti_action.triggered.connect(self.save_segmentation)
        file_menu.addAction(save_nifti_action)

    def connect_signal(self):
        for canvas in self.canvas_list[0]:
            canvas.segmentation_updated.connect(self.update_other_canvases)
            canvas.request_slice.connect(self.update_slice_canvas)

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
        button_LoadMainImage.clicked.connect(
            lambda: self.handle_button_click(popup, self.load_nifti_file, file_paths)
        )
        layout.addWidget(button_LoadMainImage)
        button_LoadSegmentation = QPushButton(f"Load Segmentation")
        button_LoadSegmentation.clicked.connect(
            lambda: self.handle_button_click(
                popup, self.load_segmentation_file, file_paths[0]
            )
        )
        layout.addWidget(button_LoadSegmentation)

        popup.exec_()

    def handle_button_click(self, dialog, function, file_path):
        function(file_path)
        dialog.accept()

    def update_all_canvases(self):
        for canvas in self.canvas_list[0]:
            canvas.update_slice()

    def update_other_canvases(self, pos_set, canvas_view):
        if canvas_view == "axial":
            self.canvas_list[0][1].external_update_and_invalidate_cache(
                set(x[0] for x in pos_set)
            )
            self.canvas_list[0][2].external_update_and_invalidate_cache(
                set(x[1] for x in pos_set)
            )
        elif canvas_view == "coronal":
            self.canvas_list[0][0].external_update_and_invalidate_cache(
                set(x[0] for x in pos_set)
            )
            self.canvas_list[0][2].external_update_and_invalidate_cache(
                set(x[1] for x in pos_set)
            )
        elif canvas_view == "sagittal":
            self.canvas_list[0][0].external_update_and_invalidate_cache(
                set(x[0] for x in pos_set)
            )
            self.canvas_list[0][1].external_update_and_invalidate_cache(
                set(x[1] for x in pos_set)
            )
        else:
            return

    def update_slice_canvas(self, slice_index, canvas_view):
        nifti_slice, segmentation_slice = self.get_slice_for_view(
            canvas_view, slice_index
        )
        if nifti_slice is None or segmentation_slice is None:
            print(f"Error: Could not get slices for {canvas_view}")
            return

        # 각 뷰의 canvas에 데이터를 업데이트
        for canvas in self.canvas_list[0]:
            if canvas.canvas_view == canvas_view:
                canvas.set_slice_data(nifti_slice, segmentation_slice)
                break

    def get_slice_for_view(self, canvas_view, slice_index):
        """
        특정 뷰에 대한 Nifti 및 Segmentation slice를 반환하는 함수
        """
        if canvas_view == "axial":
            nifti_slice = np.rot90(self.nifti_array, k=1, axes=(0, 1))[:, ::-1, :][
                :, :, slice_index
            ]
            segmentation_slice = np.rot90(self.segmentation_array, k=1, axes=(0, 1))[
                :, ::-1, :
            ][:, :, slice_index]
        elif canvas_view == "coronal":
            nifti_slice = np.rot90(self.nifti_array, k=1, axes=(0, 2))[:, :, ::-1][
                :, slice_index, :
            ]
            segmentation_slice = np.rot90(self.segmentation_array, k=1, axes=(0, 2))[
                :, :, ::-1
            ][:, slice_index, :]
        elif canvas_view == "sagittal":
            nifti_slice = np.rot90(self.nifti_array, k=1, axes=(1, 2))[::-1, :, ::-1][
                slice_index, :, :
            ]
            segmentation_slice = np.rot90(self.segmentation_array, k=1, axes=(1, 2))[
                ::-1, :, ::-1
            ][slice_index, :, :]
        else:
            return None, None

        return nifti_slice, segmentation_slice

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
            self.segmentation_array = np.zeros_like(self.nifti_array, dtype=np.int32)

            # 초기 슬라이스 인덱스
            axial_index = self.nifti_array.shape[2] // 2
            coronal_index = self.nifti_array.shape[1] // 2
            sagittal_index = self.nifti_array.shape[0] // 2

            self.set_canvas_initial_background("axial", axial_index)
            self.set_canvas_initial_background("coronal", coronal_index)
            self.set_canvas_initial_background("sagittal", sagittal_index)

        except Exception as e:
            print(f"Failed to load Image: {e}")

    def set_canvas_initial_background(self, view_type, slice_index):
        """
        초기 Canvas 설정을 위한 함수
        """
        nifty_slice, segmentation_slice = self.get_slice_for_view(
            view_type, slice_index
        )
        for canvas in self.canvas_list[0]:
            if canvas.canvas_view == view_type:
                canvas.set_initial_background(
                    nifty_slice,
                    segmentation_slice,
                    self.nifti_array.shape,
                    np.min(self.nifti_array),
                    np.max(self.nifti_array),
                )
                break

    def save_segmentation(self):
        save_segmentation_dialog(
            self, self.segmentation_array, self.nifti_affine, self.nifti_header
        )

    def load_segmentation(self):
        file_path = load_segmentation_dialog(self)
        if file_path:
            self.load_segmentation_file(file_path)

    def load_segmentation_file(self, file_path):
        try:
            segmentation_array = nib.load(file_path).get_fdata()
            if segmentation_array.shape == self.nifti_array.shape:
                self.segmentation_array = segmentation_array
                self.update_all_canvases()
            else:
                print(
                    "Error: The dimensions of the segmentation file do not match the current Image."
                )
        except Exception as e:
            print(f"Failed to load Segmentation: {e}")

    def change_brush_size(self, index):
        brush_sizes = [1, 2, 4, 8, 16, 32]
        brush_size = brush_sizes[index]
        for canvas in self.canvas_list[0]:
            canvas.set_brush_size(brush_size)

    def change_brush_color(self, index):
        brush_color_values = [0, 1, 2, 3, 4, 5, 6]
        brush_color_value = brush_color_values[index]
        for canvas in self.canvas_list[0]:
            canvas.set_brush_color_value(brush_color_value)

    def clear_all_segmentations(self):
        if self.segmentation_array is not None:
            self.segmentation_array.fill(0)
        for canvas in self.canvas_list[0]:
            canvas.clear_all_segmentations()
