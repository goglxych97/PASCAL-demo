from utils.cache_utils.cache_decorators import slice_cache
from utils.image_utils.normalize import min_max_normalize
from utils.segmentation_utils.drawing_segmentation import (
    update_segmentation_matrix,
    render_segmentation_from_matrix,
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollBar, QHBoxLayout, QWidget


class Canvas(QWidget):
    segmentation_updated = pyqtSignal(set, str)
    request_slice = pyqtSignal(int, str)

    def __init__(self, view):
        super().__init__()
        self.canvas_view = view
        self.initialize_parameters()
        self.create_ui_elements()

    def create_ui_elements(self):
        """Create and set up UI elements for the canvas."""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Main label to display images
        self.label = QLabel(self)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setMinimumSize(300, 300)

        # Scroll bar to navigate through slices
        self.scroll_bar = QScrollBar(Qt.Vertical, self)
        self.scroll_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.scroll_bar.setMinimumWidth(15)
        self.scroll_bar.valueChanged.connect(self.scroll_to_slice)

        # Layout configuration
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.scroll_bar)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def initialize_parameters(self):
        """Initialize canvas parameters."""
        self.nifti_shape = None
        self.last_point = QPoint()
        self.drawing = False
        self.current_slice_index = 0
        self.brush_color = QColor(255, 0, 0, 255)  # Default to red
        self.brush_size = 8
        self.brush_color_value = 1  # Default color value (1 for drawing)

        self.background_array = None
        self.segmentation_array = None
        self.background_image = None
        self.segmentation_image = None

        self.square_length = None
        self.nifti_min = None
        self.nifti_max = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.background_image:
            self.update_slice_display()

    def update_slice_display(self):
        """Update the displayed slice images."""
        size_tuple = (self.label.size().width(), self.label.size().height())
        self.background_image = self.render_cached_image(
            self.current_slice_index, size_tuple
        )
        self.segmentation_image = self.render_cached_segmentation(
            self.current_slice_index, size_tuple
        )
        self.update_display()

    def update_display(self):
        """Combine background and segmentation images and update the label display."""
        if not (self.background_image and self.segmentation_image):
            return

        combined_image = self.create_combined_image()
        self.label.setPixmap(QPixmap.fromImage(combined_image))

    def create_combined_image(self):
        """Create a combined image from background and segmentation."""
        combined_image = QImage(self.label.size(), QImage.Format_ARGB32)
        combined_image.fill(Qt.transparent)
        painter = QPainter(combined_image)
        painter.drawImage(self.label.rect(), self.background_image)
        painter.drawImage(self.label.rect(), self.segmentation_image)
        painter.end()
        return combined_image

    def set_slice_data(self, nifti_slice, segmentation_slice):
        """Set NIfTI and segmentation data for a specific slice."""
        if not self.validate_slice_data(nifti_slice, segmentation_slice):
            return

        self.background_array = nifti_slice
        self.segmentation_array = segmentation_slice
        self.update_slice_display()

    def validate_slice_data(self, nifti_slice, segmentation_slice):
        """Validate the given slice data."""
        if nifti_slice is None or nifti_slice.size == 0:
            print(
                f"Error: Invalid nifti_slice data. Shape: {nifti_slice.shape if nifti_slice is not None else 'None'}"
            )
            return False
        if segmentation_slice is None or segmentation_slice.size == 0:
            print(
                f"Error: Invalid segmentation_slice data. Shape: {segmentation_slice.shape if segmentation_slice is not None else 'None'}"
            )
            return False
        return True

    def set_initial_background(
        self, nifti_array, segment_array, nifti_shape, min_val, max_val
    ):
        """Set initial background and segmentation arrays."""
        self.nifti_shape = nifti_shape
        self.nifti_min = min_val
        self.nifti_max = max_val

        self.current_slice_index = self.determine_initial_index()
        self.square_length = max(nifti_array.shape)
        self.set_scroll_bar_max()
        self.set_data_and_update(nifti_array, segment_array)

    def determine_initial_index(self):
        """Determine the initial slice index based on the canvas view."""
        if self.canvas_view == "axial":
            return self.nifti_shape[2] // 2
        elif self.canvas_view == "coronal":
            return self.nifti_shape[1] // 2
        elif self.canvas_view == "sagittal":
            return self.nifti_shape[0] // 2
        return 0

    def set_scroll_bar_max(self):
        """Set the maximum value for the scroll bar based on the canvas view."""
        if self.canvas_view == "axial":
            self.scroll_bar.setMaximum(self.nifti_shape[2] - 1)
        elif self.canvas_view == "coronal":
            self.scroll_bar.setMaximum(self.nifti_shape[1] - 1)
        elif self.canvas_view == "sagittal":
            self.scroll_bar.setMaximum(self.nifti_shape[0] - 1)

    def set_data_and_update(self, nifti_array, segment_array):
        """Set the data arrays and update the canvas display."""
        self.background_array = nifti_array
        self.segmentation_array = segment_array
        self.scroll_bar.setValue(self.current_slice_index)
        self.update_slice_display()

    @slice_cache(maxsize=100)
    def render_cached_image(self, slice_index, size):
        """Render the background image with caching."""
        if self.background_array is None or len(self.background_array.shape) != 2:
            return QImage(size[0], size[1], QImage.Format_Grayscale8)

        return self.create_qimage_from_array(self.background_array, size)

    @slice_cache(maxsize=100)
    def render_cached_segmentation(self, slice_index, size):
        """Render the segmentation image with caching."""
        segmentation_image = QImage(size[0], size[1], QImage.Format_ARGB32)
        segmentation_image.fill(Qt.transparent)
        render_segmentation_from_matrix(
            segmentation_image, self.segmentation_array, self.canvas_view
        )
        return segmentation_image

    def create_qimage_from_array(self, array, size):
        """Create a QImage from a numpy array."""
        normalized_image = min_max_normalize(array, self.nifti_min, self.nifti_max)
        height, width = normalized_image.shape
        bytes_per_line = width
        qimage = QImage(
            normalized_image.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format_Grayscale8,
        )
        return qimage.scaled(
            size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

    def scroll_to_slice(self, value):
        """Handle scrolling to a new slice."""
        max_index = self.get_max_index_for_view()
        new_index = min(max(0, value), max_index)
        if new_index != self.current_slice_index:
            self.current_slice_index = new_index
            self.request_slice.emit(self.current_slice_index, self.canvas_view)

    def get_max_index_for_view(self):
        """Get the maximum index for the current canvas view."""
        if self.canvas_view == "axial":
            return self.nifti_shape[2] - 1
        elif self.canvas_view == "coronal":
            return self.nifti_shape[1] - 1
        elif self.canvas_view == "sagittal":
            return self.nifti_shape[0] - 1
        return 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = self.translate_mouse_position(event.pos())
            self.drawing = True
            self.draw_segmentation(event.pos(), draw_mode="draw")  # Left click to draw
            self.last_point = self.translate_mouse_position(event.pos())
        elif event.button() == Qt.RightButton:
            self.last_point = self.translate_mouse_position(event.pos())
            self.drawing = True
            self.draw_segmentation(
                event.pos(), draw_mode="erase"
            )  # Right click to erase
            self.last_point = self.translate_mouse_position(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drawing:
            self.draw_segmentation(event.pos(), draw_mode="draw")  # Left click to draw
            self.last_point = self.translate_mouse_position(event.pos())
        elif event.buttons() & Qt.RightButton and self.drawing:
            self.draw_segmentation(
                event.pos(), draw_mode="erase"
            )  # Right click to erase
            self.last_point = self.translate_mouse_position(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() in [Qt.LeftButton, Qt.RightButton]:
            self.drawing = False

    def translate_mouse_position(self, pos):
        """Translate the mouse position to the image position."""
        if self.background_image is None:
            return pos

        x_ratio = self.background_image.width() / self.label.width()
        y_ratio = self.background_image.height() / self.label.height()
        return QPoint(int(pos.x() * x_ratio), int(pos.y() * y_ratio))

    def draw_segmentation(self, pos, draw_mode="draw"):
        """Draw or erase segmentation on the image."""
        pos = self.translate_mouse_position(pos)

        if draw_mode == "erase":
            current_brush_value = 0  # Erase mode sets the brush value to 0
        else:
            current_brush_value = (
                self.brush_color_value
            )  # Draw mode uses current brush color

        updated_pos = update_segmentation_matrix(
            self.segmentation_array,
            self.last_point,
            pos,
            self.brush_size,
            self.background_image,
            current_brush_value,
        )

        self.update_and_invalidate_cache(updated_pos)

    def update_and_invalidate_cache(self, pos):
        """Update the segmentation image and invalidate cache for the current slice."""
        size_tuple = (self.label.size().width(), self.label.size().height())
        self.render_cached_segmentation.cache_invalidate(self.current_slice_index)
        self.segmentation_image = self.render_cached_segmentation(
            self.current_slice_index, size_tuple
        )
        self.update_display()
        self.segmentation_updated.emit(pos, self.canvas_view)

    def external_update_and_invalidate_cache(self, pos_set):
        """External update and cache invalidation for the canvas."""
        size_tuple = (self.label.size().width(), self.label.size().height())
        for slice_index in pos_set:
            self.render_cached_segmentation.cache_invalidate(slice_index)
        self.segmentation_image = self.render_cached_segmentation(
            self.current_slice_index, size_tuple
        )
        self.update_display()

    def clear_cached_segmentation(self):
        """Clear the segmentation cache for the current slice."""
        self.render_cached_segmentation.cache_clear()

    def wheelEvent(self, event):
        """Handle mouse wheel event to change slice index."""
        if self.nifti_shape is not None:
            delta = -event.angleDelta().y() // 120
            new_index = self.current_slice_index + delta
            new_index = max(0, min(self.get_max_index_for_view(), new_index))
            self.scroll_bar.setValue(new_index)

    def set_brush_color(self, color):
        self.brush_color = color

    def set_brush_size(self, size):
        self.brush_size = size

    def set_brush_color_value(self, color_value):
        self.brush_color_value = color_value

    def clear_all_segmentations(self):
        """Clear all segmentations on the canvas."""
        self.clear_cached_segmentation()
        self.segmentation_image.fill(Qt.transparent)
        self.update_display()
