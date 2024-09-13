from PIL import Image, ImageEnhance

def enhance_image(image_path: str):
    image = Image.open(image_path)

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2) # Slightly boost contrast

    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.1)  # Slightly boost saturation

    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.05)  # Slightly boost brightness

    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.1)  # Slightly boost sharpness

    image.save(image_path)


def resize_image_to_1080p(image_path: str):
    """
    Resizes the image to have a height of 1080px while maintaining the aspect ratio.

    :param image_path: Path to the input image that needs resizing.
    """
    # Open the image
    img = Image.open(image_path)

    # Set the target height to 1080px
    target_height = 1080

    # Calculate the aspect ratio and determine the new width based on the target height
    aspect_ratio = img.width / img.height
    new_width = int(target_height * aspect_ratio)

    # Resize the image to the new width and height (1080px)
    resized_img = img.resize((new_width, target_height), Image.LANCZOS)

    # Save the resized image, overwriting the original file
    resized_img.save(image_path)


def detect_and_remove_letterbox(image_path: str, output_path: str, aspect_ratio: str = "16:9", threshold=20):
    """
    Detects and removes letterbox (black bars) from an image and adjusts the image to the desired aspect ratio.

    :param image_path: Path to the input image.
    :param output_path: Path to save the cropped image without letterboxes.
    :param aspect_ratio: Desired aspect ratio ("16:9" or "4:3").
    :param threshold: Brightness threshold to detect letterboxes (default is 20).
    """
    # Open the image
    img = Image.open(image_path)

    # Convert to grayscale
    gray_img = img.convert("L")

    # Get the pixel data
    pixels = gray_img.load()

    width, height = img.size

    # Find the top and bottom bounds
    top = 0
    bottom = height - 1

    # Detect top letterbox
    for y in range(height):
        row_brightness = [pixels[x, y] for x in range(width)]
        if max(row_brightness) > threshold:
            top = y
            break

    # Detect bottom letterbox
    for y in range(height - 1, -1, -1):
        row_brightness = [pixels[x, y] for x in range(width)]
        if max(row_brightness) > threshold:
            bottom = y
            break

    # Crop the image to remove letterboxes
    cropped_img = img.crop((0, top, width, bottom))

    # Enforce the desired aspect ratio
    cropped_width, cropped_height = cropped_img.size
    desired_aspect = 16 / 9 if aspect_ratio == "16:9" else 4 / 3
    current_aspect = cropped_width / cropped_height

    if current_aspect > desired_aspect:  # Image is too wide, crop width
        new_width = int(cropped_height * desired_aspect)
        offset = (cropped_width - new_width) // 2
        cropped_img = cropped_img.crop((offset, 0, offset + new_width, cropped_height))
    elif current_aspect < desired_aspect:  # Image is too tall, crop height
        new_height = int(cropped_width / desired_aspect)
        offset = (cropped_height - new_height) // 2
        cropped_img = cropped_img.crop((0, offset, cropped_width, offset + new_height))

    # Save the cropped image with the correct aspect ratio
    cropped_img.save(output_path)