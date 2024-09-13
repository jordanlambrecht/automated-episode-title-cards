from PIL import Image, ImageDraw, ImageFont
import textwrap
import logging

def add_episode_title(image_path: str, episode_title: str, aspect_ratio: str, title_font_path: str, season_font_path: str = None, season_episode_text: str = None, line_spacing: int = 10, title_spacing: int = 30, bottom_margin: int = 100):
    """
    Add episode title as text centered in the lower third of the image, with an option to include the season and episode text.
    Overlay a gradient behind the text based on the aspect ratio.
    
    :param image_path: Path to the input image.
    :param episode_title: The text to add (episode title).
    :param aspect_ratio: Aspect ratio to determine the gradient overlay (either "16:9" or "4:3").
    :param title_font_path: Path to the font file for the episode title.
    :param season_font_path: Path to the font file for the season/episode text (optional).
    :param season_episode_text: Optional text to display above the episode title (e.g., "Season 01 - Episode 01").
    :param line_spacing: Extra vertical space between lines.
    :param title_spacing: Extra space between season/episode text and title.
    :param bottom_margin: Minimum margin from the bottom of the image to the text.
    """
    # Open the image
    img = Image.open(image_path)
    
    # Load the appropriate gradient based on the aspect ratio
    if aspect_ratio not in ["16:9", "4:3"]:
        print(f"Invalid aspect ratio: {aspect_ratio}. Defaulting to '16:9'.")
        aspect_ratio = "16:9"
        
    gradient_path = f"./gradients/gradient_{aspect_ratio.replace(':', 'x')}_bottom.png"
    try:
        gradient = Image.open(gradient_path)
    except IOError:
        print(f"Gradient file '{gradient_path}' not found.")
        return

    # Resize the gradient to match the image width
    gradient = gradient.resize((img.width, gradient.height))

    # Paste the gradient onto the original image (lower third)
    img.paste(gradient, (0, img.height - gradient.height), gradient)

    # Set up drawing context
    draw = ImageDraw.Draw(img)

    # Get the size of the image
    width, height = img.size

    # Dynamically calculate initial font size based on image size (e.g., 12% of image height for title, 7% for season/episode)
    title_font_size = max(int(height * 0.12), 60)  # Set a minimum of 60 for readability
    season_font_size = max(int(title_font_size / 1.8), 40)  # Ensure season/episode text remains readable

    # Load the user-selected fonts
    try:
        title_font = ImageFont.truetype(title_font_path, title_font_size)
        print(f"Using title font: {title_font_path}")  # Add this for debugging
    except IOError:
        print(f"Title font file '{title_font_path}' not found. Using default font.")
        title_font = ImageFont.load_default()

    if season_font_path and season_episode_text:
        try:
            season_font = ImageFont.truetype(season_font_path, season_font_size)
            print(f"Using season font: {season_font_path}")  # Add this for debugging
        except IOError:
            print(f"Season font file '{season_font_path}' not found. Using default font.")
            season_font = ImageFont.load_default()
    else:
        season_font = None

    # Define the text color (white) and drop shadow color (subtle dark gray)
    title_color = (255, 255, 255)
    season_color = (255, 255, 255)
    shadow_color = (0, 0, 0, 150)  # Semi-transparent black for subtle shadow

    # Max width for the text (40% of the image width), but ensure a minimum of 30% width
    max_width_pixels = max(width * 0.6, 300)  # Ensure a minimum width of 300 pixels

    # Use textwrap to break lines within the width limit
    wrapped_lines = textwrap.wrap(episode_title, width=int(max_width_pixels // title_font_size * 1.5))

    # Calculate total title text height (multiple lines + spacing)
    total_title_height = sum([draw.textbbox((0, 0), line, font=title_font)[3] for line in wrapped_lines])
    total_title_height += line_spacing * (len(wrapped_lines) - 1)  # Add spacing between lines

    # If season_episode_text is provided, calculate its height
    if season_episode_text and season_font:
        season_bbox = draw.textbbox((0, 0), season_episode_text, font=season_font)
        season_width = season_bbox[2] - season_bbox[0]
        season_height = season_bbox[3] - season_bbox[1]
    else:
        season_width = 0
        season_height = 0

    # Calculate the start position to vertically center the text in the lower third
    lower_third_height = height // 3
    total_text_height = total_title_height + season_height + title_spacing  # Include both title and season/episode text
    text_y = height - lower_third_height + (lower_third_height - total_text_height) // 2

    # Ensure there's a margin of at least 50px from the bottom of the image
    if text_y + total_text_height + bottom_margin > height:
        text_y = height - total_text_height - bottom_margin

    # Draw the season/episode text if provided, centered above the title
    if season_episode_text and season_font:
        season_x = (width - season_width) // 2  # Center the season text horizontally
        draw.text((season_x + 2, text_y + 2), season_episode_text, font=season_font, fill=shadow_color)  # Drop shadow
        draw.text((season_x, text_y), season_episode_text, font=season_font, fill=season_color)  # Actual text
        text_y += season_height + title_spacing  # Add extra space below the season text

    # Draw each line of title text with a subtle drop shadow
    for line in wrapped_lines:
        # Get the size of each line
        text_bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Calculate position for centering the line
        text_x = (width - text_width) // 2

        # Draw the drop shadow first
        draw.text((text_x + 2, text_y + 2), line, font=title_font, fill=shadow_color)

        # Draw the actual text
        draw.text((text_x, text_y), line, font=title_font, fill=title_color)

        # Move to the next line with spacing
        text_y += text_height + line_spacing

    # Save the modified image
    img.save(image_path)