"""Utility functions for edge detection and rectangle finding."""

import cv2
import numpy as np
import distributions

def detect_vertical_edges(image):
    """
    Apply a convolution pass to detect vertical edges in the image.
    """
    # Define a kernel for detecting vertical edges
    vertical_kernel = np.array([[-1, 0, 1],
                                 [-2, 0, 2],
                                 [-1, 0, 1]])
    
    # Convert the image to grayscale if it's not already
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply the kernel using cv2.filter2D
    vertical_edges = cv2.filter2D(gray_image, -1, vertical_kernel)
    
    return vertical_edges

def detect_edges_with_rgb(image):
    """Return an RGB edge map encoding different edge orientations."""
    # Define kernels for detecting edges
    left_kernel = np.array([[1, 0, -1],
                            [2, 0, -2],
                            [1, 0, -1]])
    
    right_kernel = np.array([[-1, 0, 1],
                             [-2, 0, 2],
                             [-1, 0, 1]])
    
    top_kernel = np.array([[-1, -2, -1],
                           [0, 0, 0],
                           [1, 2, 1]])
    
    # Convert the image to grayscale if it's not already
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply the kernels using cv2.filter2D
    left_edges = cv2.filter2D(gray_image, -1, left_kernel)
    right_edges = cv2.filter2D(gray_image, -1, right_kernel)
    top_edges = cv2.filter2D(gray_image, -1, top_kernel)
    
    # Normalize the edge images to fit in the range [0, 255]
    left_edges = cv2.normalize(left_edges, None, 0, 255, cv2.NORM_MINMAX)
    right_edges = cv2.normalize(right_edges, None, 0, 255, cv2.NORM_MINMAX)
    top_edges = cv2.normalize(top_edges, None, 0, 255, cv2.NORM_MINMAX)
    
    # Create an RGB image where each channel corresponds to an edge direction
    edge_image = np.zeros((gray_image.shape[0], gray_image.shape[1], 3), dtype=np.uint8)
    edge_image[:, :, 0] = left_edges  # Blue channel for left edges
    edge_image[:, :, 1] = right_edges  # Green channel for right edges
    edge_image[:, :, 2] = top_edges  # Red channel for top edges
    
    return edge_image


def detect_rectangles(image, original_image=None):
    """Locate rectangular features in an edge image and draw them."""
    if original_image is None:
        original_image = image.copy()

    # Calculate intensity distributions for each channel
    blue_distribution = np.sum(image[:, :, 0], axis=0)  # Blue channel
    green_distribution = np.sum(image[:, :, 1], axis=0)  # Green channel

    # Detect high-intensity regions
    blue_regions = distributions.detect_high_intensity_regions(blue_distribution, "Blue")
    green_regions = distributions.detect_high_intensity_regions(green_distribution, "Green")

    # Find consecutive pairs of blue and green regions
    pairs = distributions.find_consecutive_pairs(blue_regions, green_regions)

    # Draw rectangles for blue regions
    for start, end in blue_regions:
        cv2.rectangle(original_image, (start, 0), (end, original_image.shape[0]), (255, 0, 0), thickness=2)  # Blue rectangle

    # Draw rectangles for green regions
    for start, end in green_regions:
        cv2.rectangle(original_image, (start, 0), (end, original_image.shape[0]), (0, 255, 0), thickness=2)  # Green rectangle

    # Draw white bars for the pairs
    image_height = original_image.shape[0]
    bar_height = int(image_height * 0.05)  # Top 5% of the image height
    for blue, green in pairs:
        blue_start, blue_end = blue
        green_start, green_end = green
        # Draw white bar from the end of the blue region to the start of the green region
        cv2.rectangle(original_image, (blue_end, 0), (green_start, bar_height), (255, 255, 255), thickness=-1)

    return original_image, pairs
