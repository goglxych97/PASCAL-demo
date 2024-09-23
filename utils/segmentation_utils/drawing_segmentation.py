# utils/segmentation_utils/drawing_segmentation.py
from PyQt5.QtCore import Qt
from scipy.ndimage import zoom
import numpy as np


def bresenham_line(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return points


def render_segmentation_from_matrix(segmentation_image, slice_segmentation, view):
    """
    Render the segmentations for faster performance.
    :param segmentation_image: QImage object to draw the segmentation
    :param slice_segmentation: 2D numpy array containing segmentation data for a specific slice
    :param view: current canvas view type ('axial', 'coronal', 'sagittal')
    """
    if slice_segmentation is not None:
        segmentation_image.fill(Qt.transparent)
        height, width = slice_segmentation.shape

        color_map = {
            1: (0, 0, 255, 255),  # Red
            2: (0, 255, 0, 255),  # Green
            3: (255, 0, 0, 255),  # Blue
            4: (255, 255, 0, 255),  # Yellow
            5: (135, 206, 235, 255),  # Sky Blue
            6: (128, 0, 128, 255),  # Purple
        }

        buffer = segmentation_image.bits()
        buffer.setsize(segmentation_image.byteCount())
        img_array = np.frombuffer(buffer, np.uint8).reshape(
            (segmentation_image.height(), segmentation_image.width(), 4)
        )

        scale_x = segmentation_image.width() / width
        scale_y = segmentation_image.height() / height

        for color_value, color in color_map.items():
            positions = np.argwhere(slice_segmentation == color_value)
            if len(positions) > 0:
                mask = np.zeros((height, width), dtype=np.uint8)
                mask[positions[:, 0], positions[:, 1]] = 1
                zoomed_mask = zoom(mask, (scale_y, scale_x), order=1)
                img_array[zoomed_mask > 0.5] = color


def update_segmentation_matrix(
    segmentation_matrix,
    last_pos,
    pos,
    brush_size,
    background_image,
    brush_color_value,
):
    """
    Update the segmentation matrix by drawing a line between points.
    :param segmentation_matrix: 2D numpy array to update with segmentation
    :param last_pos: QPoint for the starting point
    :param pos: QPoint for the ending point
    :param brush_size: Brush size in pixels
    :param background_image: QImage object for the background image
    :param brush_color_value: Integer for the color value of the brush
    """
    if segmentation_matrix is None:
        return

    # Convert positions to matrix coordinates
    x0 = int(
        np.clip(
            last_pos.x() * segmentation_matrix.shape[1] / background_image.width(),
            0,
            segmentation_matrix.shape[1] - 1,
        )
    )
    y0 = int(
        np.clip(
            last_pos.y() * segmentation_matrix.shape[0] / background_image.height(),
            0,
            segmentation_matrix.shape[0] - 1,
        )
    )
    x1 = int(
        np.clip(
            pos.x() * segmentation_matrix.shape[1] / background_image.width(),
            0,
            segmentation_matrix.shape[1] - 1,
        )
    )
    y1 = int(
        np.clip(
            pos.y() * segmentation_matrix.shape[0] / background_image.height(),
            0,
            segmentation_matrix.shape[0] - 1,
        )
    )

    # Generate points using Bresenham's algorithm
    line_points = bresenham_line(x0, y0, x1, y1)

    # Prepare a mask to define brush effect area
    brush_radius = brush_size // 2
    Y, X = np.ogrid[-brush_radius : brush_radius + 1, -brush_radius : brush_radius + 1]
    mask = X**2 + Y**2 <= brush_radius**2

    updated_pixels = set()  # For Update Cache

    for x_center, y_center in line_points:
        x_min = max(x_center - brush_radius, 0)
        x_max = min(x_center + brush_radius + 1, segmentation_matrix.shape[1])
        y_min = max(y_center - brush_radius, 0)
        y_max = min(y_center + brush_radius + 1, segmentation_matrix.shape[0])

        sub_matrix = segmentation_matrix[y_min:y_max, x_min:x_max]

        mask_x_start = max(0, -x_center + brush_radius)
        mask_x_end = mask_x_start + (x_max - x_min)
        mask_y_start = max(0, -y_center + brush_radius)
        mask_y_end = mask_y_start + (y_max - y_min)

        mask_area = mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]

        if brush_color_value == 0:
            sub_matrix[mask_area] = 0
        else:
            sub_matrix[mask_area] = int(brush_color_value)

        dy_indices, dx_indices = np.nonzero(mask_area)
        y_indices = y_min + dy_indices
        x_indices = x_min + dx_indices

        updated_pixels.update(zip(y_indices, x_indices))

    return updated_pixels
