# menu/file.py
from utils.segmentation_utils.transform_save_segmentation import save_transform_segmentation
from PyQt5.QtWidgets import QFileDialog

def load_image_dialog(main_window):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getOpenFileName(
        main_window,
        "Load NIfTI File",
        "",
        "NIfTI Files (*.nii *.nii.gz)",
        options=options
    )
    return file_path

def load_segmentation_dialog(main_window):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getOpenFileName(
        main_window,
        "Load Segmentation File",
        "",
        "NIfTI Files (*.nii *.nii.gz)",
        options=options
    )
    return file_path

def save_segmentation_dialog(main_window, segmentation_matrix, affine, header):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        main_window,
        "Save Segmentation File",
        "",
        "NIfTI Files (*.nii.gz)",
        options=options
    )
    if file_path:
        save_transform_segmentation(
            segmentation_matrix,
            affine,
            header,
            file_path
        )
