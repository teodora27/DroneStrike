import matplotlib.pyplot as plt
import numpy as np
import os
import cv2

def plot_comparative_distribution(distribution, channel_name, regions):
    """Plot intensity distribution with highlighted regions."""
    plt.figure(figsize=(12, 6))
    plt.plot(distribution, label=f'{channel_name} Distribution', color=channel_name.lower())
    for start, end in regions:
        plt.axvspan(start, end, color='yellow', alpha=0.3, label='High-Intensity Region' if start == regions[0][0] else "")
    plt.title(f'{channel_name} Channel High-Intensity Regions')
    plt.xlabel('Column Index')
    plt.ylabel('Sum of Pixel Intensities')
    plt.legend()
    plt.grid(True)
    plt.show()

def detect_high_intensity_regions(distribution, channel_name):
    """
    Detect regions where the intensity is much higher than normal.
    """
    # Define a threshold as a multiple of the mean intensity
    threshold = np.mean(distribution) + 3.5 * np.std(distribution)
    high_intensity_mask = distribution > 10000  # Adjust this threshold as needed

    # Find continuous regions of high intensity
    regions = []
    start = None
    for i, is_high in enumerate(high_intensity_mask):
        if is_high and start is None:
            start = i
        elif not is_high and start is not None:
            regions.append((start, i - 1))
            start = None
    if start is not None:  # Handle case where region extends to the end
        regions.append((start, len(distribution) - 1))

    print(f"{channel_name} Channel High-Intensity Regions: {regions}")

    # Plot the high-intensity regions
    # plot_comparative_distribution(distribution, channel_name, regions)

    return regions

def find_consecutive_pairs(blue_regions, green_regions):
    """
    Find pairs of blue and green regions where:
    - Blue is to the left of green.
    - There are no green regions before the current blue region.
    - There are no blue regions after the current green region.
    """
    pairs = []
    i, j = 0, 0  # Two pointers for blue_regions and green_regions

    while i < len(blue_regions) and j < len(green_regions):
        blue_start, blue_end = blue_regions[i]
        green_start, green_end = green_regions[j]

        if blue_end < green_start:  # Blue is to the left of green
            # Check if there are no green regions before the current blue region
            if j == 0 or green_regions[j - 1][1] < blue_start:
                # Check if there are no blue regions after the current green region
                if i + 1 >= len(blue_regions) or blue_regions[i + 1][0] > green_end:
                    pairs.append(((blue_start, blue_end), (green_start, green_end)))
            i += 1  # Move to the next blue region
        else:
            j += 1  # Move to the next green region

    return pairs


if __name__ == "__main__":
    # Example usage for debugging on a folder of images
    for image_file in os.listdir("output/images"):
        if image_file.__contains__("_depth"):
            continue
        image_path = os.path.join("output/images", image_file)

        edge_image = cv2.imread(image_path)
        red_distribution = np.sum(edge_image[:, :, 2], axis=0)  # Red channel
        green_distribution = np.sum(edge_image[:, :, 1], axis=0)  # Green channel
        blue_distribution = np.sum(edge_image[:, :, 0], axis=0)  # Blue channel

        blue_regions = detect_high_intensity_regions(blue_distribution, "Blue")
        green_regions = detect_high_intensity_regions(green_distribution, "Green")

        pairs = find_consecutive_pairs(blue_regions, green_regions)
        print(f"Consecutive Blue-Green Pairs for {image_file}: {pairs}")

        # Draw rectangles for blue regions
        for start, end in blue_regions:
            cv2.rectangle(edge_image, (start, 0), (end, edge_image.shape[0]), (255, 0, 0), thickness=-1)  # Blue rectangle

        # Draw rectangles for green regions
        for start, end in green_regions:
            cv2.rectangle(edge_image, (start, 0), (end, edge_image.shape[0]), (0, 255, 0), thickness=-1)  # Green rectangle

        # Draw white bars for the pairs
        image_height = edge_image.shape[0]
        bar_height = int(image_height * 0.05)  # Top 5% of the image height
        for blue, green in pairs:
            blue_start, blue_end = blue
            green_start, green_end = green
            # Draw white bar from the end of the blue region to the start of the green region
            cv2.rectangle(edge_image, (blue_end, 0), (green_start, bar_height), (255, 255, 255), thickness=-1)

        # Save or display the modified image
        output_path = os.path.join("output/processed", image_file)
        os.makedirs("output/processed", exist_ok=True)
        cv2.imwrite(output_path, edge_image)
        print(f"Processed image saved to {output_path}")