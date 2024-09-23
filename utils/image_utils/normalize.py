# utils/image_utils/normalize.py
import numpy as np


def return_min_max_value(image_data):
    min_value = np.min(image_data)
    max_value = np.max(image_data)

    return min_value, max_value


def min_max_normalize(image_data, min_value, max_value):
    """
    Normalize the image to the range [0, 255].
    :param image_data: 2D slice numpy
    :return: Normalized 2D numpy array of type uint8.
    """
    if max_value == min_value:
        return np.zeros_like(
            image_data, dtype=np.uint8
        )  # Prevent division by zero if the image is flat

    normalized_data = 255 * (image_data - min_value) / (max_value - min_value)

    return normalized_data.astype(np.uint8)
