from functools import lru_cache
from utils.cache_utils.cache_decorators import slice_cache
from utils.image_utils.normalize import return_min_max_value, min_max_normalize 
from utils.segmentation_utils.drawing_segmentation import update_segmentation_matrix, render_segmentation_from_matrix
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollBar, QHBoxLayout, QWidget
import numpy as np

class Canvas(QWidget):
    segmentation_updated = pyqtSignal()
    request_slice = pyqtSignal(int)  # Slice 데이터를 요청할 때 사용

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Canvas Layout
        self.label = QLabel(self)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setMinimumSize(300, 300)
        self.scroll_bar = QScrollBar(Qt.Vertical, self)
        self.scroll_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.scroll_bar.setMinimumWidth(15)
        self.scroll_bar.valueChanged.connect(self.scroll_to_slice)
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.scroll_bar)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Canvas Params
        self.nifty_shape = None
        self.background_image = None
        self.segmentation_image = None
        self.last_point = QPoint()
        self.drawing = False
        self.current_slice_index = 0
        self.brush_color = QColor(255, 0, 0, 255)
        self.brush_size = 8
        self.brush_color_value = 1
        self.segmentation_matrix = None
        self.nifti_slice_data = None  # Nifti slice data 저장
        self.segmentation_slice_data = None  # Segmentation slice data 저장

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.background_image is not None:
            self.update_slice()
    
    def update_slice(self):
        if self.nifti_slice_data is None or self.segmentation_slice_data is None:
            # Slice 데이터가 없으면 MainWindow에 요청
            self.request_slice.emit(self.current_slice_index)
            return 
        
        size_tuple = (self.label.size().width(), self.label.size().height())
        self.background_image = self.render_cached_image(self.current_slice_index, size_tuple)
        self.segmentation_image = self.render_cached_segmentation(self.current_slice_index, size_tuple)
        self.update_display() 

    def update_display(self):
        if self.background_image is None or self.segmentation_image is None:
            return

        combined_image = QImage(self.label.size(), QImage.Format_ARGB32)
        combined_image.fill(Qt.transparent)
        painter = QPainter(combined_image)
        painter.drawImage(self.label.rect(), self.background_image)
        painter.drawImage(self.label.rect(), self.segmentation_image)
        painter.end()
        self.label.setPixmap(QPixmap.fromImage(combined_image))

    def set_slice_data(self, nifti_slice, segmentation_slice):
        """MainWindow에서 slice 데이터를 설정해주는 함수"""
        self.nifti_slice_data = nifti_slice
        self.segmentation_slice_data = segmentation_slice
        self.update_slice()

    def set_background_image_from_nifti(self, nifty_shape):
        self.nifty_shape = nifty_shape
        self.current_slice_index = self.nifty_shape[2] // 2
        self.scroll_bar.setMaximum(self.nifty_shape[2] - 1)
        self.scroll_bar.setValue(self.current_slice_index)

        self.render_cached_image.cache_clear()
        self.render_cached_segmentation.cache_clear()
        self.update_slice()

    @lru_cache(maxsize=100)
    def render_cached_image(self, slice_index, size):
        import matplotlib.pyplot as plt
        plt.imshow(self.nifti_slice_data)
        plt.show()
        
        slice_image = self.nifti_slice_data  # 요청받아온 데이터 사용
        min_value, max_value = return_min_max_value(slice_image)
        slice_image = min_max_normalize(slice_image, min_value, max_value)
        height, width = slice_image.shape
        bytes_per_line = width
        qimage = QImage(slice_image.tobytes(), width, height, bytes_per_line, QImage.Format_Grayscale8)

        return qimage.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)

    @slice_cache(maxsize=100)
    def render_cached_segmentation(self, slice_index, size):
        slice_segmentation = self.segmentation_slice_data  # 요청받아온 데이터 사용

        segmentation_image = QImage(size[0], size[1], QImage.Format_ARGB32)
        segmentation_image.fill(Qt.transparent)

        render_segmentation_from_matrix(
            segmentation_image,
            slice_segmentation
        )

        return segmentation_image

    def scroll_to_slice(self, value):
        if self.nifty_shape is not None:
            max_index = self.nifty_shape[2] - 1
            self.current_slice_index = min(max(0, value), max_index)
            self.update_slice()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = self.translate_mouse_position(event.pos())
            self.drawing = True
            self.draw_segmentation(event.pos())
            self.last_point = self.translate_mouse_position(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drawing:
            self.draw_segmentation(event.pos())
            self.last_point = self.translate_mouse_position(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def translate_mouse_position(self, pos):
        if self.background_image is None:
            return pos
        
        x_ratio = self.background_image.width() / self.label.width()
        y_ratio = self.background_image.height() / self.label.height()

        return QPoint(int(pos.x() * x_ratio), int(pos.y() * y_ratio))

    def draw_segmentation(self, pos):
        pos = self.translate_mouse_position(pos)
        update_segmentation_matrix(
            self.segmentation_matrix,
            self.last_point,
            pos,
            self.brush_size,
            self.background_image,
            self.current_slice_index,
            self.brush_color_value
        )
        self.render_cached_segmentation.cache_invalidate(self.current_slice_index)
        size_tuple = (self.label.size().width(), self.label.size().height())
        self.segmentation_image = self.render_cached_segmentation(self.current_slice_index, size_tuple)
        self.update_display()
        self.segmentation_updated.emit() 

    def wheelEvent(self, event):
        if self.nifty_shape is not None:
            delta = event.angleDelta().y() // 120
            new_index = self.current_slice_index + delta
            self.scroll_bar.setValue(new_index)

    def set_brush_color(self, color):
        self.brush_color = color

    def set_brush_size(self, size):
        self.brush_size = size

    def set_brush_color_value(self, color_value):
        self.brush_color_value = color_value

    def clear_all_segmentations(self):
        self.render_cached_segmentation.cache_clear()  # Clear cached segmentation
        self.segmentation_image.fill(Qt.transparent)
        self.update_display()
