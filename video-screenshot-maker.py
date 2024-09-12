import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List
from ffmpy import FFmpeg
from rich.console import Console
from rich.progress import track
import subprocess
import json
import re
import textwrap
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Suppress Pillow debug logs by setting its logging level to WARNING or higher
logging.getLogger('PIL').setLevel(logging.WARNING)

# Console for user interaction
console = Console()

# Ensure output directory is based on the script's root directory
ROOT_DIR = Path(__file__).parent.absolute()

def prompt_user_inputs():
    # Prompt for the source directory with default "./source"
    source_dir = console.input("[bold blue]Enter the source directory for MKV files (default: ./source): [/bold blue]").strip()
    if not source_dir:
        source_dir = "./source"
    
    # Prompt for the number of screenshots with default 3
    num_of_screenshots_input = console.input("[bold blue]Enter number of screenshots per video (default: 3): [/bold blue]").strip()
    num_of_screenshots = int(num_of_screenshots_input) if num_of_screenshots_input else 3
    
    # Prompt for the aspect ratio with default 16:9
    aspect_ratio = console.input("[bold blue]Do you want the screenshots to be 16:9 or 4:3? (default: 16:9): [/bold blue]").strip()
    if not aspect_ratio:
        aspect_ratio = "16:9"
    elif aspect_ratio not in ["16:9", "4:3"]:
        console.print(f"[red]Invalid input! Defaulting to 16:9 aspect ratio.[/red]")
        aspect_ratio = "16:9"
    
    # Prompt for overwrite existing screenshots with default Yes
    overwrite_existing_input = console.input("[bold blue]Overwrite existing screenshots? (Y/N, default: Y): [/bold blue]").strip().lower()
    overwrite_existing = overwrite_existing_input  in ['y', 'Y'] if overwrite_existing_input else True
    
    # Prompt for image enhancement with default No
    enhance_images_input = console.input("[bold blue]Enhance images? (Y/N, default: Y): [/bold blue]").strip().lower()
    enhance_images = enhance_images_input  in ['y', 'Y'] if enhance_images_input else True
    
    # Prompt for letterbox removal with default No
    remove_letterbox_input = console.input("[bold blue]Remove letterboxes? (Y/N, default: Y): [/bold blue]").strip().lower()
    remove_letterbox = remove_letterbox_input  in ['y', 'Y'] if remove_letterbox_input else True

    # Prompt for adding titles with default Yes
    add_titles_input = console.input("[bold blue]Add episode titles to screenshots? (Y/N, default: Y): [/bold blue]").strip().lower()
    add_titles = add_titles_input  in ['y', 'Y'] if add_titles_input else True
    
    # Prompt for adding season/episode text with default Yes
    add_season_episode_text_input = console.input("[bold blue]Include Season X - Episode Y above the title? (Y/N, default: Y): [/bold blue]").strip().lower()
    add_season_episode_text = add_season_episode_text_input  in ['y', 'Y'] if add_season_episode_text_input else True

    
    # If the directory doesn't exist, print error
    if not os.path.isdir(source_dir):
        console.print(f"[red]Invalid directory![/red] {source_dir} does not exist.")
        exit(1)
    
    return source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text

def extract_episode_metadata(mkv_file: str) -> Tuple[str, str, str, str]:
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mkv_file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        metadata = json.loads(result.stdout)
        
        # Extract show name, season number, episode number, and episode title from the metadata (tags)
        tags = metadata['format'].get('tags', {})
        show_name = tags.get('show_name', None)
        season_number = tags.get('season_number', None) or tags.get('season', None)
        episode_number = tags.get('episode_number', None) or tags.get('episode', None)
        episode_title = tags.get('title', None)  # None if not available
        
        # Fallback to filename parsing if metadata is incomplete
        if not show_name or not season_number or not episode_number or not episode_title:
            show_name, season_number, episode_number, episode_title = extract_from_filename(mkv_file)
        
        # Clean up the title if needed
        episode_title = clean_episode_title(episode_title)
        
        return show_name, str(season_number), str(episode_number), episode_title
    except Exception as e:
        logging.error(f"Error extracting metadata from {mkv_file}: {e}")
        return extract_from_filename(mkv_file)

def extract_from_filename(filename: str) -> Tuple[str, str, str, str]:
    regex = re.compile(r'(.*?)[ ._-]+[Ss](\d+)[Ee](\d+)[ ._-]+(.*?)\.[a-zA-Z]+')
    match = regex.match(Path(filename).name)
    if match:
        show_name = match.group(1).replace(".", " ").strip()
        season_number = match.group(2)
        episode_number = match.group(3)
        episode_title = match.group(4).replace(".", " ").strip()
    else:
        show_name = Path(filename).stem
        season_number = "Unknown Season"
        episode_number = "Unknown Episode"
        episode_title = "Untitled Episode"
    
    episode_title = clean_episode_title(episode_title)
    return show_name, season_number, episode_number, episode_title

def clean_episode_title(title: str) -> str:
    """Clean up unnecessary parts from episode titles (e.g., source, resolution tags, release group)."""
    if title:
        # Extract the clean title by ignoring anything in brackets or parentheses
        title_match = re.match(r'(?P<title>[^\[\(]+)', title)
        
        if title_match:
            title = title_match.group("title").strip()

        # Remove trailing content like release group tags, but preserve legitimate hyphenated titles
        # Match a hyphen, period, or underscore followed by a word or release group at the very end.
        title = re.sub(r'[-_.]\s?[A-Z0-9]{2,}$', '', title)

    return title.strip()

def _get_ss_range(duration: int, num_of_screenshots: int) -> List[str]:
    timestamps = []
    interval = duration / (num_of_screenshots + 1)
    for i in range(1, num_of_screenshots + 1):
        timestamp = str(datetime.fromtimestamp(interval * i, tz=timezone.utc).strftime('%H:%M:%S'))
        timestamps.append(timestamp)
    return timestamps

# Letterbox removal function
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

class GGBotScreenshotManager:
    def __init__(self, file_info, duration, upload_media, num_of_screenshots, screenshots_path, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text):
        self.upload_media = upload_media
        self.duration = duration
        self.num_of_screenshots: int = num_of_screenshots
        self.show_name, self.season_number, self.episode_number, self.episode_title = file_info
        self.screenshots_path = screenshots_path
        self.aspect_ratio = aspect_ratio
        self.overwrite_existing = overwrite_existing
        self.enhance_images = enhance_images
        self.remove_letterbox = remove_letterbox
        self.add_titles = add_titles
        self.add_season_episode_text = add_season_episode_text
        logging.info(f"[GGBotScreenshotManager::init] Screenshots will be saved for {self.show_name} - s{self.season_number.zfill(2)}e{self.episode_number.zfill(2)}")


    @staticmethod
    def _does_screenshot_exist(output_file):
        return Path(output_file).is_file()

    def _run_ffmpeg(self, upload_media, timestamp, output_file):
        if self.aspect_ratio == "16:9":
            vf_filter = "scale=iw:trunc(iw/16*9)"
        elif self.aspect_ratio == "4:3":
            vf_filter = "crop=4/3*ih:ih"

        FFmpeg(
            inputs={upload_media: ["-loglevel", "panic", "-ss", timestamp, "-itsoffset", "-2"]},
            outputs={output_file: ["-vf", vf_filter, "-frames:v", "1", "-q:v", "10", "-pix_fmt", "rgb24"]}
        ).run()

    def enhance_image(self, image_path):
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

    def _generate_screenshot(self, output_file, timestamp):
        if not self._does_screenshot_exist(output_file) or self.overwrite_existing:
            self._run_ffmpeg(self.upload_media, timestamp, output_file)
            
            if self.remove_letterbox:
                detect_and_remove_letterbox(output_file, output_file, aspect_ratio=self.aspect_ratio)  # Detect and remove letterboxes with the aspect ratio
                    
            if self.enhance_images:
                self.enhance_image(output_file)
            
            # Add episode title and season/episode text only if requested by user
            season_episode_text = f"Season {self.season_number.zfill(2)}   —   Episode {self.episode_number.zfill(2)}" if self.add_season_episode_text else None
            if self.add_titles:
                add_episode_title(output_file, self.episode_title, self.aspect_ratio, season_episode_text)
        else:
            logging.info(f"Screenshot already exists and overwrite is disabled: {output_file}")

    def _get_timestamp_outfile_tuple(self, ss_timestamps) -> List[Tuple[str, str]]:
        return [
            (
                timestamp,
                f"{self.screenshots_path}{self.show_name} - s{self.season_number.zfill(2)}e{self.episode_number.zfill(2)} - {self.episode_title} - ({timestamp.replace(':', '.')}).png"
            )
            for timestamp in ss_timestamps
        ]

    def _generate_screenshots(self, timestamp_outfile_tuple):
        console.print(f"[bold green]Taking screenshots for:[/bold green] [yellow]{self.show_name}[/yellow]")
        console.print(f"[bold green]Season:[/bold green] [yellow]{self.season_number}[/yellow]")
        console.print(f"[bold green]Episode:[/bold green] [yellow]{self.episode_number}[/yellow]")
        console.print(f"[bold green]Title:[/bold green] [yellow]{self.episode_title}[/yellow]")
        console.print(f"[bold green]Aspect Ratio:[/bold green] [yellow]{self.aspect_ratio}[/yellow]")

        for timestamp_file in track(timestamp_outfile_tuple, description="Taking screenshots.."):
            self._generate_screenshot(output_file=timestamp_file[1], timestamp=timestamp_file[0])

    def generate_screenshots(self):
        ss_timestamps: List[str] = _get_ss_range(int(self.duration), self.num_of_screenshots)
        timestamp_outfile_tuple = self._get_timestamp_outfile_tuple(ss_timestamps)
        self._generate_screenshots(timestamp_outfile_tuple)
        logging.info(f"Screenshots taken at: {ss_timestamps}")
        return True

def add_episode_title(image_path: str, episode_title: str, aspect_ratio: str, season_episode_text: str = None, line_spacing: int = 10, title_spacing: int = 30, bottom_margin: int = 50):
    """
    Add episode title as text centered in the lower third of the image, with an option to include the season and episode text.
    Overlay a gradient behind the text based on the aspect ratio.
    
    :param image_path: Path to the input image.
    :param episode_title: The text to add (episode title).
    :param aspect_ratio: Aspect ratio to determine the gradient overlay (either "16:9" or "4:3").
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

    # Dynamically calculate initial font size based on image size (e.g., 8% of image height)
    title_font_size = max(int(height * 0.10), 40)  # Set a minimum of 40 to avoid tiny fonts
    season_font_size = int(title_font_size / 2.25)

    # Load the custom fonts
    title_font_path = "./fonts/CooperBlackStd-Italic.otf"
    season_font_path = "./fonts/BebasNeue-Regular.ttf"

    try:
        title_font = ImageFont.truetype(title_font_path, title_font_size)
        season_font = ImageFont.truetype(season_font_path, season_font_size)
    except IOError:
        print(f"Font file '{title_font_path}' or '{season_font_path}' not found. Using default font.")
        title_font = ImageFont.load_default()
        season_font = ImageFont.load_default()

    # Define the text color (white) and drop shadow color (subtle dark gray)
    title_color = (255, 255, 255)
    season_color = (255, 255, 255)
    shadow_color = (0, 0, 0, 100)  # Semi-transparent black for subtle shadow

    # Max width for the text (40% of the image width), but ensure a minimum of 30% width
    max_width_pixels = max(width * 0.6, 300)  # Ensure a minimum width of 300 pixels

    # Use textwrap to break lines within the width limit
    wrapped_lines = textwrap.wrap(episode_title, width=int(max_width_pixels // title_font_size * 1.5))

    # Calculate total title text height (multiple lines + spacing)
    total_title_height = sum([draw.textbbox((0, 0), line, font=title_font)[3] for line in wrapped_lines])
    total_title_height += line_spacing * (len(wrapped_lines) - 1)  # Add spacing between lines

    # If season_episode_text is provided, calculate its height
    if season_episode_text:
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
    if season_episode_text:
        season_x = (width - season_width) // 2  # Center the season text horizontally
        draw.text((season_x + 2, text_y + 2), season_episode_text, font=season_font, fill=shadow_color)  # Drop shadow
        draw.text((season_x, text_y), season_episode_text, font=season_font, fill=season_color)  # Actual text
        text_y += season_height + title_spacing*1.66  # Add extra space below the season text

    # Draw each line of title text with a subtle drop shadow
    for line in wrapped_lines:
        # Get the size of each line
        text_bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Calculate position for centering the line
        text_x = (width - text_width) // 2

        # Draw drop shadow (offset slightly for a subtle effect)
        draw.text((text_x + 2, text_y + 2), line, font=title_font, fill=shadow_color)

        # Draw actual text
        draw.text((text_x, text_y), line, font=title_font, fill=title_color)

        # Move to the next line with spacing
        text_y += text_height + line_spacing

    # Save the modified image
    img.save(image_path)

def get_video_duration(mkv_path: str) -> float:
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', mkv_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        duration_str = result.stdout.strip()

        if duration_str:
            return float(duration_str)
        else:
            logging.error(f"No duration found for {mkv_path}")
            return None
    except Exception as e:
        logging.error(f"Error retrieving duration for {mkv_path}: {e}")
        return None

def process_videos_in_directory(source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text):
    mkv_files = []

    # Walk through the source directory recursively
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.mkv'):
                mkv_files.append(os.path.join(root, file))

    if not mkv_files:
        console.print("[red]No MKV files found in the source directory![/red]")
        exit(1)

    total_screenshots = 0
    total_episodes = 0

    for mkv_file in mkv_files:
        # Use mkv_file directly without re-joining the source_dir
        mkv_path = os.path.abspath(mkv_file)  # Ensure absolute path

        console.print(f"[bold blue]Processing:[/bold blue] {mkv_file}")

        file_info = extract_episode_metadata(mkv_path)

        output_root = os.path.join(ROOT_DIR, "output")
        show_folder = os.path.join(output_root, file_info[0])
        season_folder = os.path.join(show_folder, f"Season {file_info[1].zfill(2)}")
        os.makedirs(season_folder, exist_ok=True)

        # Get the duration
        duration = get_video_duration(mkv_path)  # Use mkv_path here
        if not duration:
            console.print(f"[red]Skipping {mkv_file} due to missing or invalid duration.[/red]")
            continue
        # Pass add_titles to the screenshot manager
        screenshot_manager = GGBotScreenshotManager(file_info, duration, mkv_path, num_of_screenshots, f"{season_folder}/", aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text)
        screenshot_manager.generate_screenshots()

        total_screenshots += num_of_screenshots
        total_episodes += 1

    console.print(f"\n[bold green]Successfully created {total_screenshots} images for {total_episodes} episodes.[/bold green]")

if __name__ == "__main__":
    source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text = prompt_user_inputs()
    process_videos_in_directory(source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox, add_titles, add_season_episode_text)