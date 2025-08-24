import cv2
import os
import depth_estimation
import rect_predict
import numpy as np

def test_images(image_folder):
    midas, transform, device = depth_estimation.init_depth_model("DPT_Large")
    for image_file in os.listdir(image_folder):
        image_path = os.path.join(image_folder, image_file)
        image = cv2.imread(image_path)
        if image is None:
            raise AssertionError(f"Failed to load image: {image_file}")
        
        # Test depth estimation
        depth_image, _ = depth_estimation.process_depth(image, midas, transform, device)
        assert depth_image is not None, f"Depth estimation failed for {image_file}"
        
        # Test edge detection
        edges_image = rect_predict.detect_edges_with_rgb(depth_image)
        assert edges_image is not None, f"Edge detection failed for {image_file}"

        out_image, rectangles = rect_predict.detect_rectangles(edges_image, original_image=image)
        assert rectangles is not None, f"Rectangle detection failed for {image_file}"
        assert out_image is not None, f"Output image generation failed for {image_file}"

        cv2.imwrite(os.path.join("output/depth_images", f"output_{image_file}"), depth_image)
        cv2.imwrite(os.path.join("output/images", f"output_{image_file}"), out_image)

        print(f"Image {image_file} processed successfully.")

def test_videos(video_folder):
    for video_file in os.listdir(video_folder):
        video_path = os.path.join(video_folder, video_file)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise AssertionError(f"Failed to open video: {video_file}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Test rectangle detection
            _, rectangles = rect_predict.detect_rectangles(frame)
            assert rectangles is not None, f"Rectangle detection failed for {video_file}"
        
        cap.release()
        print(f"Video {video_file} processed successfully.")

if __name__ == "__main__":
    test_images("test_data/images")
    test_videos("test_data/videos")