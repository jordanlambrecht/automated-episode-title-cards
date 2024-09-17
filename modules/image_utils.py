from PIL import Image, ImageEnhance
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def enhance_image(image_path: Path):
    """Enhance the image's contrast, color, brightness, and sharpness."""
    try:
        image = Image.open(image_path)

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)

        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)

        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)

        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)

        image.save(image_path)
    except Exception as e:
        logger.error(f"Error enhancing image {image_path}: {e}")

def resize_image_to_target_dimensions(image_path: Path, aspect_ratio: str):
    """
    Resizes the image to the target dimensions based on the aspect ratio.

    :param image_path: Path to the input image that needs resizing.
    :param aspect_ratio: The desired aspect ratio ("16:9" or "4:3").
    """
    # Define target dimensions based on aspect ratio
    if aspect_ratio == "16:9":
        target_width = 1920
        target_height = 1080
    elif aspect_ratio == "4:3":
        target_width = 1440
        target_height = 1080
    else:
        # Default to 16:9 if unknown aspect ratio
        target_width = 1920
        target_height = 1080

    # Open the image
    img = Image.open(image_path)

    # Resize the image to the target dimensions
    resized_img = img.resize((target_width, target_height), Image.LANCZOS)

    # Save the resized image, overwriting the original file
    resized_img.save(image_path)

def detect_and_remove_letterbox(image_path: Path, output_path: Path, aspect_ratio: str = "16:9", threshold=20):
    """
    Detects and removes letterbox (black bars) from an image and crops it to the desired aspect ratio.

    :param image_path: Path to the input image.
    :param output_path: Path to save the cropped image without letterboxes.
    :param aspect_ratio: Desired aspect ratio ("16:9" or "4:3").
    :param threshold: Brightness threshold to detect letterboxes (default is 20).
    """
    # Open the image
    img = Image.open(image_path)
    img_array = np.array(img.convert("L"))

    # Create a mask where pixels brighter than the threshold are considered content
    mask = img_array > threshold
    coords = np.argwhere(mask)

    if coords.size == 0:
        logger.warning(f"\nNo content detected in image {image_path}. Skipping letterbox removal.")
        return

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0) + 1  # slices are exclusive at the top

    # Crop the image to content area
    cropped_img = img.crop((x_min, y_min, x_max, y_max))

    # Now enforce the desired aspect ratio
    cropped_width, cropped_height = cropped_img.size
    if aspect_ratio == "16:9":
        desired_ratio = 16 / 9
    elif aspect_ratio == "4:3":
        desired_ratio = 4 / 3
    else:
        desired_ratio = cropped_width / cropped_height  # Keep original aspect ratio if unknown

    current_ratio = cropped_width / cropped_height

    if abs(current_ratio - desired_ratio) > 0.01:
        # Adjust the cropping to achieve the desired aspect ratio
        if current_ratio > desired_ratio:
            # Crop width
            new_width = int(cropped_height * desired_ratio)
            offset = (cropped_width - new_width) // 2
            cropped_img = cropped_img.crop((offset, 0, offset + new_width, cropped_height))
        else:
            # Crop height
            new_height = int(cropped_width / desired_ratio)
            offset = (cropped_height - new_height) // 2
            cropped_img = cropped_img.crop((0, offset, cropped_width, offset + new_height))

    # Save the cropped image
    cropped_img.save(output_path)