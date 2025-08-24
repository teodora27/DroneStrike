# depth_estimation.py
import torch
import cv2
import numpy as np

def init_depth_model(model_type: str = "DPT_Large"):
    """
    Initialize the MiDaS depth estimation model and its transform.
    model_type: "DPT_Large", "DPT_Hybrid", or "MiDaS_small".
    Returns the model, transformation function, and device.
    """
    # Load the pretrained model and its associated transforms from Torch Hub
    midas = torch.hub.load("intel-isl/MiDaS", model_type)
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    
    if model_type in ["DPT_Large", "DPT_Hybrid"]:
        transform = midas_transforms.dpt_transform
    else:
        transform = midas_transforms.default_transform

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    midas.to(device)
    midas.eval()

    return midas, transform, device

def process_depth(image, midas, transform, device):
    """
    Process an image to compute a depth map.
    Returns a tuple (depth_colormap, raw_depth) where:
      - depth_colormap: color-mapped depth image for display.
      - raw_depth: relative depth values (same size as image).
    """
    # Convert image to RGB and apply the model's preprocessing transforms
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    input_batch = transform(img_rgb).to(device)
    
    # Run the forward pass without tracking gradients
    with torch.no_grad():
        prediction = midas(input_batch)
    
    # Resize the output to the original image size
    raw_depth = torch.nn.functional.interpolate(
        prediction.unsqueeze(1),
        size=img_rgb.shape[:2],
        mode="bicubic",
        align_corners=False,
    ).squeeze().cpu().numpy()
    
    depth_min = raw_depth.min()
    depth_max = raw_depth.max()
    depth_vis = (255 * (raw_depth - depth_min) / (depth_max - depth_min + 1e-6)).astype(np.uint8)
    depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_MAGMA)
    
    return depth_colormap, raw_depth

def convert_to_metric(raw_depth, min_m=0.5, max_m=10.0):
    """
    Convert relative depth (raw_depth) to approximate metric depth (in meters).
    Assumes:
      - Pixel with maximum raw value (closest) corresponds to min_m.
      - Pixel with minimum raw value (farthest) corresponds to max_m.
    """
    depth_min = raw_depth.min()
    depth_max = raw_depth.max()
    # Normalize depth to 0..1 then scale to the desired range
    norm_depth = (raw_depth - depth_min) / (depth_max - depth_min + 1e-6)
    metric_depth = (1 - norm_depth) * (max_m - min_m) + min_m
    return metric_depth
