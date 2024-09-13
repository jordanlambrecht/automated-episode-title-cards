from PIL import Image, ImageDraw, ImageFont
import textwrap

from pathlib import Path
from log_config import logger






# Helper Function to Load and Apply Gradient
def load_and_apply_gradient(img: Image.Image, aspect_ratio: str) -> Image.Image:
    """Loads and applies the gradient overlay based on the aspect ratio."""
    width, height = img.size
    gradients_dir = Path(__file__).parent / "gradients"
    gradient_filename = f"gradient_{aspect_ratio.replace(':', 'x')}_bottom.png"
    gradient_path = gradients_dir / gradient_filename

    try:
        with Image.open(gradient_path) as gradient:
            gradient = gradient.resize((width, gradient.height))
            img.paste(gradient, (0, height - gradient.height), gradient)
            logger.debug(f"Applied gradient: {gradient_filename}")
    except IOError:
        logger.warning(f"Gradient file '{gradient_filename}' not found. Skipping gradient overlay.")

    return img

# Helper Function to Load Fonts
def load_font(font_name: str, font_size: int, fallback: bool = True) -> ImageFont.FreeTypeFont:
    """Loads the specified font, falling back to default if necessary."""
    fonts_dir = Path(__file__).parent / "fonts"
    font_path = fonts_dir / font_name
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
    """Draws text with a drop shadow."""
    x, y = position
    # Draw shadow first
    draw.text((x + 2, y + 2), text, font=font, fill=shadow_color, anchor="ms")
    # Draw actual text
    draw.text((x, y), text, font=font, fill=text_color, anchor="ms")

# Main Function
def add_episode_title(
    image_path: Path,
    episode_title: str,
    aspect_ratio: str,
    title_font_name: str,
    season_font_name: str = None,
    season_episode_text: str = None,
    line_spacing: int = 40,
    title_spacing: int = 30,  # Space between season text and title text
    bottom_margin: int = 10
):
    """
    Add episode title and optional season/episode text to the image, overlaying a gradient based on aspect ratio.
    This function first writes the episode title and calculates the space taken,
    then writes the season/episode text above it.
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size

            # Apply gradient
            img = load_and_apply_gradient(img, aspect_ratio)

            # Set up drawing context
            draw = ImageDraw.Draw(img)

            # Dynamically calculate initial font sizes based on image size
            title_font_size = max(int(height * 0.12), 60)  # 12% of image height, min 60
            season_font_size = max(int(title_font_size * 0.333), 40)
            line_spacing = min(int(title_font_size * 0.25), 25)
            title_spacing = min(int(season_font_size * .75), 50)
            # Load title font and season font
            title_font = load_font(title_font_name, title_font_size)
            season_font = load_font(season_font_name, season_font_size) if season_font_name and season_episode_text else None

            # Define text and shadow colors
            title_color = (255, 255, 255)
            season_color = (255, 255, 255)
            shadow_color = (0, 0, 0, 150)  # Semi-transparent black

            # Max width for the text (60% of the image width)
            max_width_pixels = max(width * 0.6, 300)

            # Wrap the episode title text
            chars_per_line = int(max_width_pixels / (title_font_size * 0.6))
            wrapped_lines = textwrap.wrap(episode_title, width=chars_per_line)

            # Start drawing from the bottom of the image, moving upwards
            text_y = height - bottom_margin

            # Draw episode title lines with drop shadows, starting from the bottom
            for line in reversed(wrapped_lines):  # Reverse order to start from bottom up
                text_x = width // 2
                line_height = draw.textbbox((0, 0), line, font=title_font)[3]
                text_y -= line_height + line_spacing  # Move upwards
                draw_text_with_shadow(draw, (text_x, text_y), line, title_font, title_color, shadow_color)

            # Now, calculate the total height used by the title text
            total_title_height = sum([draw.textbbox((0, 0), line, font=title_font)[3] for line in wrapped_lines])
            total_title_height += line_spacing * (len(wrapped_lines) - 1)

            # Calculate the new Y-position above the title for the season text
            if season_episode_text and season_font:
                text_y -= (season_font_size*2 + title_spacing*2)
                season_x = width // 2
                draw_text_with_shadow(draw, (season_x, text_y), season_episode_text, season_font, season_color, shadow_color)

            # Save the modified image
            img.save(image_path)

    except Exception as e:
        logger.error(f"Error adding title to image {image_path}: {e}")