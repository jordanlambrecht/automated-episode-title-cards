import os
from PIL import Image, ImageDraw, ImageFont,ImageFilter
import textwrap

from pathlib import Path
from .log_config import logger
from .load_config import config





# Helper Function to Load and Apply Gradient
def load_and_apply_gradient(img: Image.Image) -> Image.Image:

    """Loads and applies the gradient overlay based on the aspect ratio."""
    aspect_ratio = config['global_options']['aspect_ratio']
    prefer_strong_gradient = config['text_overlays']['prefer_strong_gradient']
    width, height = img.size
    # gradients_dir = Path(__file__).parent / "gradients"
    gradients_dir =  "./gradients"
    if(prefer_strong_gradient):
        gradient_filename = f"gradient_{aspect_ratio.replace(':', 'x')}_bottom_strong.png"
    else:
        gradient_filename = f"gradient_{aspect_ratio.replace(':', 'x')}_bottom.png"
    gradient_path = os.path.join(gradients_dir,gradient_filename)

    try:
        with Image.open(gradient_path) as gradient:
            gradient = gradient.resize((width, gradient.height))
            img.paste(gradient, (0, height - gradient.height), gradient)

    except IOError:
        logger.warning(f"Gradient file '{gradient_path}' not found. Skipping gradient overlay.")

    return img

# Helper Function to Load Fonts
def load_font(font_name: str, font_size: int, fallback: bool = True) -> ImageFont.FreeTypeFont:
    """Loads the specified font, falling back to default if necessary."""
    # fonts_dir = Path(__file__).parent / "fonts"
    fonts_dir = "./fonts"
    font_path = os.path.join(fonts_dir,font_name)
    try:
        return ImageFont.truetype(str(font_path), font_size)
    except IOError:
        if fallback:
            logger.warning(f"Font '{font_name}' not found. Using default font.")
            return ImageFont.load_default()
        else:
            raise

# Helper Function to Draw Text with Drop Shadow

def draw_text_with_shadow(draw: ImageDraw.Draw, position: tuple, text: str, font: ImageFont.FreeTypeFont, text_color: tuple, shadow_color: tuple):
    """
    Draws text with a drop shadow effect.
    :param draw: ImageDraw object used for drawing text.
    :param position: Tuple (x, y) coordinates where the text should be placed.
    :param text: The actual text string to draw.
    :param font: Font object for rendering the text.
    :param text_color: Color of the text in RGBA (e.g., (255, 255, 255, 255) for white with full opacity).
    :param shadow_color: Color of the shadow in RGBA (e.g., (0, 0, 0, 150) for black with transparency).
    """
    x, y = position

    # Draw shadow first
    shadow_offset = 3  # You can adjust the offset to your liking
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color, anchor="ms")

    # Draw actual text on top of the shadow
    draw.text((x, y), text, font=font, fill=text_color, anchor="ms")

# Main Function
def add_episode_title(
    image_path: Path,
    episode_title: str,
    aspect_ratio: str,
    title_font_name: str,
    season_font_name: str = None,
    season_episode_text: str = None,
    line_spacing: int = 20,
    title_spacing: int = 30,  # Space between season text and title text
    bottom_margin: int = 1
):
    """
    Add episode title and optional season/episode text to the image, overlaying a gradient based on aspect ratio.
    """
    enable_gradient = config['text_overlays']['add_gradient']
    try:
        with Image.open(image_path) as img:
            width, height = img.size

            # Apply gradient if enabled
            if enable_gradient:
                img = load_and_apply_gradient(img)

            # Set up drawing context
            draw = ImageDraw.Draw(img)

            # Dynamically calculate initial font sizes based on image size
            title_font_size = max(int(height * 0.10), 60)  # 10% of image height, minimum 60
            season_font_size = max(int(title_font_size * 0.4), 30)  # Season font is 40% of title font, minimum 30
            line_spacing = max(int(title_font_size * 0.10), 5)  # Line spacing for title, minimum 5
            title_spacing = max(int(season_font_size * 0.5), 35)  # Spacing between title and season, minimum 5

            # Load title font and season font
            title_font = load_font(title_font_name, title_font_size)
            season_font = load_font(season_font_name, season_font_size) if season_font_name and season_episode_text else None

            # Define text and shadow colors
            title_color = (255, 255, 255, 255)  # White for title text
            season_color = (255, 255, 255, 255)  # White for season text
            shadow_color = (0, 0, 0, 150)  # Semi-transparent black for shadow

            # Calculate max width for the text (60% of the image width)
            max_width_pixels = int(width * 0.6)

            # Wrap the episode title text into multiple lines
            chars_per_line = int(max_width_pixels / (title_font_size * 0.6))  # Rough estimate of chars per line
            wrapped_lines = textwrap.wrap(episode_title, width=chars_per_line)

            # Calculate total height of the wrapped title lines
            total_title_height = sum([draw.textbbox((0, 0), line, font=title_font)[3] for line in wrapped_lines])
            total_title_height += line_spacing * (len(wrapped_lines) - 1)  # Add spacing between title lines

            # Calculate the height of the season text
            season_height = draw.textbbox((0, 0), season_episode_text, font=season_font)[3] if season_episode_text else 0

            # Calculate the Y position to draw the title (starting from the bottom margin)
            text_y = height - bottom_margin

            # Draw episode title lines with drop shadows, starting from the bottom
            for line in reversed(wrapped_lines):  # Start from bottom to top
                text_x = width // 2
                line_height = draw.textbbox((0, 0), line, font=title_font)[3]
                text_y -= line_height + line_spacing  # Move upwards for each line

                draw_text_with_shadow(draw, (text_x, text_y), line, title_font, title_color, shadow_color)

            # Calculate Y position for the season text above the title
            if season_episode_text and season_font:
                season_y = text_y - season_height*2 - title_spacing  # Position season above the title
                season_x = width // 2

                draw_text_with_shadow(draw, (season_x, season_y), season_episode_text, season_font, season_color, shadow_color)
                
            # Save the modified image
            img.save(image_path)

    except Exception as e:
        logger.error(f"Error adding title to image {image_path}: {e}")