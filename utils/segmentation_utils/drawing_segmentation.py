# utils/segmentation_utils/drawing_segmentation.py
from PyQt5.QtCore import Qt
from scipy.ndimage import zoom
import numpy as np

def bresenham_line(x0, y0, x1, y1):
    """
    Generate points between two coordinates using Bresenham's line algorithm.
    :param x0: Integer, x-coord of the start point
    :param y0: Integer, y-coord of the start point
    :param x1: Integer, x-coord of the end point
    :param y1: Integer, y-coord of the end point
    :return: List of (x, y) points between the start and end points
    """
    points = []  # List to store all points
    dx = abs(x1 - x0)  # Diff in x-coords
    dy = abs(y1 - y0)  # Diff in y-coords
    sx = 1 if x0 < x1 else -1  # Step direction for x
    sy = 1 if y0 < y1 else -1  # Step direction for y
    err = dx - dy  # Init the error term

    while True:
        points.append((x0, y0))  # Add the point to the points list
        if x0 == x1 and y0 == y1:  # If end, break the loop
            break
        e2 = err * 2  # Calculate double the error term to determine the next step
        if e2 > -dy:  # Adjust x-coord and error term
            err -= dy  # Subtract dy from the error term
            x0 += sx
        if e2 < dx:  # Adjust y-coord and error term
            err += dx  # Add dx to the error term
            y0 += sy
    
    return points

def render_segmentation_from_matrix(segmentation_image, slice_segmentation):
    """
    Render the segmentations for faster performance.
    :param segmentation_image: QImage object to draw the segmentation
    :param segmentation_matrix: Numpy array containing segmentation
    :param current_slice_index: Index for current slice to render
    """
    if slice_segmentation is not None:
        segmentation_image.fill(Qt.transparent)
        height, width = slice_segmentation.shape

        # Define color mapping using RGBA tuples
        # R and B channels are inverted.
        color_map = {
            1: (0, 0, 255, 255),  # Red
            2: (0, 255, 0, 255),  # Green
            3: (255, 0, 0, 255),  # Blue 
            4: (255, 255, 0, 255),  # Sky Blue
            5: (135, 206, 235, 255),  # Yellow
            6: (128, 0, 128, 255)  # Purple
        }

        # Access the QImage bits and manipulate them directly
        buffer = segmentation_image.bits()
        buffer.setsize(segmentation_image.byteCount())
        img_array = np.frombuffer(buffer, np.uint8).reshape((segmentation_image.height(), segmentation_image.width(), 4))

        # Compute scale factors for resizing based on the image size and segmentation size
        scale_x = segmentation_image.width() / width
        scale_y = segmentation_image.height() / height

        # Create an empty array for faster assignment
        for color_value, color in color_map.items():
            # Get the positions for this color value
            positions = np.argwhere(slice_segmentation == color_value)
            # Map to image coordinates and apply linear interpolation scaling
            if len(positions) > 0:
                # # Compute scaled coordinates using linear interpolation
                # screen_x = np.clip(np.round(positions[:, 1] * scale_x).astype(int), 0, segmentation_image.width() - 1)
                # screen_y = np.clip(np.round(positions[:, 0] * scale_y).astype(int), 0, segmentation_image.height() - 1)
                # Create an empty mask for the color and set it in the zoomed image
                mask = np.zeros((height, width), dtype=np.uint8)
                mask[positions[:, 0], positions[:, 1]] = 1
                # Use zoom for linear interpolation to scale mask up to the image size
                zoomed_mask = zoom(mask, (scale_y, scale_x), order=1)  # Linear interpolation
                # Fill the img_array based on zoomed_mask positions
                img_array[zoomed_mask > 0.5] = color  # Assign color where zoomed mask is present

def update_segmentation_matrix(segmentation_matrix, last_pos, pos, brush_size, background_image, current_slice_index, brush_color_value):
    """
    Update the segmentation matrix by drawing a line between points.
    :param segmentation_matrix: Numpy array to update with segmentation
    :param last_pos: QPoint for the starting point
    :param pos: QPoint for the ending point
    :param brush_size: Brush size in pixels
    :param background_image: QImage object for the background image
    :param current_slice_index: Index for current slice to update
    :param brush_color_value: Integer for the color value of the brush
    """
    if segmentation_matrix is None:
        return

    # Convert positions to matrix coordinates
    x0 = int(np.clip(last_pos.x() * segmentation_matrix.shape[1] / background_image.width(), 0, segmentation_matrix.shape[1] - 1))
    y0 = int(np.clip(last_pos.y() * segmentation_matrix.shape[0] / background_image.height(), 0, segmentation_matrix.shape[0] - 1))
    x1 = int(np.clip(pos.x() * segmentation_matrix.shape[1] / background_image.width(), 0, segmentation_matrix.shape[1] - 1))
    y1 = int(np.clip(pos.y() * segmentation_matrix.shape[0] / background_image.height(), 0, segmentation_matrix.shape[0] - 1))

    # Generate points using Bresenham's algorithm
    line_points = bresenham_line(x0, y0, x1, y1)

    # Prepare a mask to define brush effect area
    brush_radius = brush_size // 2
    Y, X = np.ogrid[-brush_radius:brush_radius+1, -brush_radius:brush_radius+1]
    mask = X**2 + Y**2 <= brush_radius**2  # Create a circular mask

    # Update the segmentation matrix
    for x_center, y_center in line_points:
        x_min = max(x_center - brush_radius, 0)
        x_max = min(x_center + brush_radius + 1, segmentation_matrix.shape[1])
        y_min = max(y_center - brush_radius, 0)
        y_max = min(y_center + brush_radius + 1, segmentation_matrix.shape[0])

        # Extract the relevant sub-matrix to apply the brush
        sub_matrix = segmentation_matrix[y_min:y_max, x_min:x_max, current_slice_index]

        # Apply mask within bounds
        mask_x_start = max(0, -x_center + brush_radius)
        mask_x_end = mask_x_start + (x_max - x_min)
        mask_y_start = max(0, -y_center + brush_radius)
        mask_y_end = mask_y_start + (y_max - y_min)

        # Update the sub_matrix with the brush color value or clear
        if brush_color_value == 0:
            sub_matrix[mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]] = 0
        else:
            sub_matrix[mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]] = int(brush_color_value)