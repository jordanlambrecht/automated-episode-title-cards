import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List
from ffmpy import FFmpeg
from rich.console import Console
from rich.progress import track

import textwrap
from PIL import Image, ImageDraw, ImageFont
import time

from image_utils import detect_and_remove_letterbox, enhance_image, resize_image_to_1080p
from file_utils import clean_episode_title, extract_from_filename, get_video_duration, extract_episode_metadata
from text_utils import add_episode_title
# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Suppress Pillow debug logs by setting its logging level to WARNING or higher
logging.getLogger('PIL').setLevel(logging.WARNING)

# Console for user interaction
console = Console()

# Ensure output directory is based on the script's root directory
ROOT_DIR = Path(__file__).parent.absolute()

def load_fonts_from_directory(fonts_dir: str) -> List[str]:
    """
    Load all fonts from the specified directory and return a list of file names.
    """
    fonts = []
    if not os.path.exists(fonts_dir):
        logging.error(f"Font directory '{fonts_dir}' does not exist.")
        console.print(f"[red]Error: Font directory '{fonts_dir}' does not exist.[/red]")
        return fonts

    for file in os.listdir(fonts_dir):
        if file.lower().endswith(('.ttf', '.otf')):  # Only include TTF and OTF fonts
            fonts.append(file)

    if not fonts:
        logging.warning(f"No fonts found in the specified directory: {fonts_dir}")
        console.print("[red]No fonts found in the specified directory.[/red]")
    else:
        logging.info(f"Loaded fonts: {fonts}")

    return fonts

def prompt_user_inputs():
    # Prompt for the source directory with default "./source"
    source_dir = console.input("[bold blue]Enter the source directory for MKV files (default: ./source): [/bold blue]").strip() or "./source"
    
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
    overwrite_existing = overwrite_existing_input in ['y', 'Y'] if overwrite_existing_input else True
    
    # Prompt for image enhancement with default No
    enhance_images_input = console.input("[bold blue]Enhance images? (Y/N, default: Y): [/bold blue]").strip().lower()
    enhance_images = enhance_images_input in ['y', 'Y'] if enhance_images_input else True
    
    # Prompt for letterbox removal with default No
    remove_letterbox_input = console.input("[bold blue]Remove letterboxes? (Y/N, default: Y): [/bold blue]").strip().lower()
    remove_letterbox = remove_letterbox_input in ['y', 'Y'] if remove_letterbox_input else True
    # If the directory doesn't exist, print error
    if not os.path.isdir(source_dir):
        console.print(f"[red]Invalid directory![/red] {source_dir} does not exist.")
        exit(1)
    
    return source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox


def prompt_user_text_customization(fonts_dir: str) -> Tuple[str, str, bool]:
    """
    Prompts user for text customization options like fonts for episode titles, 
    and whether to include season/episode text, along with its font.
    
    :param fonts_dir: Directory where font files are located
    :return: A tuple containing selected title font, season font (if applicable), and whether to include season/episode text
    """
    
    title_font = season_font = None  # Initialize to None
    add_season_episode_text = False  # Initialize to False by default
    
    # Print a special separator and color for text customization
    console.print("\n[bold yellow]TEXT CUSTOMIZATION OPTIONS[/bold yellow]", style="bold yellow")
    
    # Load available fonts from the fonts directory
    try:
        available_fonts = load_fonts_from_directory(fonts_dir)
    except Exception as e:
        console.print(f"[red]Error loading fonts from {fonts_dir}: {e}[/red]")
        return "CooperBlackStd-Italic.otf", None, False  # Default title font and no season text in case of error
    
    # Prompt for title font selection first
    console.print("[yellow]Available fonts for Episode Title text:[/yellow]", style="yellow")
    for idx, font in enumerate(available_fonts, start=1):
        console.print(f"[{idx}] {font}")
    
    title_font_choice = console.input("[yellow]Choose a font for the Episode Title text (enter number): [/yellow]").strip()
    try:
        title_font = available_fonts[int(title_font_choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice. Defaulting to CooperBlackStd-Italic.otf[/red]")
        title_font = "CooperBlackStd-Italic.otf"
    
    # Prompt for adding season/episode text with default Yes
    add_season_episode_text_input = console.input("[yellow]Include Season X - Episode Y above the title? (Y/N, default: Y): [/yellow]").strip().lower()
    add_season_episode_text = add_season_episode_text_input in ['y', 'Y'] if add_season_episode_text_input else True
    
    season_font = None  # Default to None unless the user selects Yes for season/episode text
    
    # Only prompt for season font selection if the user chooses to include season/episode text
    if add_season_episode_text:
        console.print("\n[yellow]Available fonts for Season/Episode text:[/yellow]", style="yellow")
        for idx, font in enumerate(available_fonts, start=1):
            console.print(f"[{idx}] {font}")
        
        season_font_choice = console.input("[yellow]Choose a font for the Season/Episode text (enter number): [/yellow]").strip()
        try:
            season_font = available_fonts[int(season_font_choice) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice. Defaulting to BebasNeue-Regular.ttf[/red]")
            season_font = "BebasNeue-Regular.ttf"

    return title_font, season_font, add_season_episode_text





def _get_ss_range(duration: int, num_of_screenshots: int) -> List[str]:
    timestamps = []
    interval = duration / (num_of_screenshots + 1)
    for i in range(1, num_of_screenshots + 1):
        timestamp = str(datetime.fromtimestamp(interval * i, tz=timezone.utc).strftime('%H:%M:%S'))
        timestamps.append(timestamp)
    return timestamps


class GGBotScreenshotManager:
    def __init__(
        self,
        file_info,
        duration,
        upload_media,
        num_of_screenshots,
        screenshots_path,
        aspect_ratio,
        overwrite_existing,
        enhance_images,
        remove_letterbox,
        add_titles,
        title_font=None,
        season_font=None,
        add_season_episode_text=False
    ):
        self.upload_media = upload_media
        self.duration = duration
        self.num_of_screenshots = num_of_screenshots
        self.show_name, self.season_number, self.episode_number, self.episode_title = file_info
        self.screenshots_path = screenshots_path
        self.aspect_ratio = aspect_ratio
        self.overwrite_existing = overwrite_existing
        self.enhance_images = enhance_images
        self.remove_letterbox = remove_letterbox
        self.add_titles = add_titles
        self.title_font = title_font
        self.season_font = season_font
        self.add_season_episode_text = add_season_episode_text
        logging.info(f"[GGBotScreenshotManager::init] Screenshots will be saved for {self.show_name} - s{self.season_number.zfill(2)}e{self.episode_number.zfill(2)}")

    def _does_screenshot_exist(self, output_file):
        return Path(output_file).is_file()

    def _run_ffmpeg(self, upload_media, timestamp, output_file):
        if self.aspect_ratio == "16:9":
            vf_filter = "scale=iw:trunc(iw/16*9)"
        elif self.aspect_ratio == "4:3":
            vf_filter = "crop=4/3*ih:ih"
        time.sleep(0.5)
        FFmpeg(
            inputs={upload_media: ["-loglevel", "panic", "-ss", timestamp, "-itsoffset", "-2"]},
            outputs={output_file: ["-vf", vf_filter, "-frames:v", "1", "-q:v", "10", "-pix_fmt", "rgb24"]}
        ).run()
        time.sleep(0.5)
        # Check if the file exists after running ffmpeg
        if not os.path.exists(output_file):
            logging.error(f"Screenshot was not generated: {output_file}")
        else:
            logging.info(f"Screenshot generated: {output_file}")

    def _generate_screenshot(self, output_file, timestamp):
        try:
            if not self._does_screenshot_exist(output_file) or self.overwrite_existing:
                self._run_ffmpeg(self.upload_media, timestamp, output_file)

                if self.remove_letterbox:
                    detect_and_remove_letterbox(output_file, output_file, aspect_ratio=self.aspect_ratio)

                if self.enhance_images:
                    enhance_image(output_file)

                season_episode_text = f"Season {self.season_number.zfill(2)} – Episode {self.episode_number.zfill(2)}" if self.add_season_episode_text else None
                if self.add_titles:
                    print(f"Using title font: {self.title_font}, season font: {self.season_font}")
                    add_episode_title(
                        output_file, 
                        self.episode_title, 
                        self.aspect_ratio, 
                        self.title_font,  # Pass the selected title font here
                        self.season_font,  # Pass the selected season font here
                        season_episode_text
    )
            else:
                logging.info(f"Screenshot already exists and overwrite is disabled: {output_file}")
        except Exception as e:
            logging.error(f"Failed to generate screenshot for {output_file}: {e}")

        # Resize to 1080p after all processing
        resize_image_to_1080p(output_file)

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
            console.log(f"\nProcessing file: {timestamp_file[1]}")  # Use console.log here
            try:
                self._generate_screenshot(output_file=timestamp_file[1], timestamp=timestamp_file[0])
            except Exception as e:
                logging.error(f"Error generating screenshot for timestamp {timestamp_file[0]}: {e}")
        
    def generate_screenshots(self):
        ss_timestamps: List[str] = _get_ss_range(int(self.duration), self.num_of_screenshots)
        timestamp_outfile_tuple = self._get_timestamp_outfile_tuple(ss_timestamps)
        self._generate_screenshots(timestamp_outfile_tuple)
        logging.info(f"Screenshots taken at: {ss_timestamps}")
        return True
    


def process_videos_in_directory(
    source_dir: str, 
    num_of_screenshots: int, 
    aspect_ratio: str, 
    overwrite_existing: bool, 
    enhance_images: bool, 
    remove_letterbox: bool, 
    add_titles: bool, 
    title_font: str = None, 
    season_font: str = None, 
    add_season_episode_text: bool = False
):
    mkv_files = [f for f in os.listdir(source_dir) if f.endswith('.mkv')]
    
    if not mkv_files:
        console.print("[red]No MKV files found in the source directory![/red]")
        return

    total_screenshots = 0
    total_episodes = 0
    total_failures = 0

    for mkv_file in mkv_files:
        mkv_path = os.path.join(source_dir, mkv_file)
        console.print(f"[bold blue]Processing:[/bold blue] {mkv_file}")
        
        file_info = extract_episode_metadata(mkv_path)
        
        output_root = os.path.join(ROOT_DIR, "output")
        show_folder = os.path.join(output_root, file_info[0])
        season_folder = os.path.join(show_folder, f"Season {file_info[1].zfill(2)}")
        os.makedirs(season_folder, exist_ok=True)
        
        # Get the video duration using the modular function
        duration = get_video_duration(mkv_path)
        if not duration:
            console.print(f"[red]Skipping {mkv_file} due to missing or invalid duration.[/red]")
            total_failures += 1
            continue
        
        # Pass all the parameters to the screenshot manager
        screenshot_manager = GGBotScreenshotManager(
            file_info,
            duration,
            mkv_path,
            num_of_screenshots,
            f"{season_folder}/",
            aspect_ratio,
            overwrite_existing,
            enhance_images,
            remove_letterbox,
            add_titles,
            title_font,
            season_font,
            add_season_episode_text
        )

        try:
            screenshot_manager.generate_screenshots()
            total_screenshots += num_of_screenshots
            total_episodes += 1
        except Exception as e:
            console.print(f"[red]Error generating screenshots for {mkv_file}: {e}[/red]")
            total_failures += 1
            continue  # Skip the file if screenshot generation fails

    console.print(f"\n[bold green]Successfully created {total_screenshots} images for {total_episodes} episodes.[/bold green]")
    console.print(f"[bold red]Failed to process {total_failures} file(s).[/bold red]")

if __name__ == "__main__":
    # Get general inputs
    source_dir, num_of_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox = prompt_user_inputs()

    # Check if the user wants to add titles
    add_titles = console.input("[bold blue]Add episode titles to screenshots? (Y/N, default: Y): [/bold blue]").strip().lower() in ['y', 'Y', '']

    if add_titles:
        fonts_dir = "./fonts"
        # If the user wants to customize the titles, call the text customization
        title_font, season_font, add_season_episode_text = prompt_user_text_customization(fonts_dir)
        print(f"Selected title font: {title_font}, season font: {season_font}")
    else:
        title_font = season_font = None
        add_season_episode_text = False

    # Call the main process with all parameters
    process_videos_in_directory(
        source_dir=source_dir,
        num_of_screenshots=num_of_screenshots,
        aspect_ratio=aspect_ratio,
        overwrite_existing=overwrite_existing,
        enhance_images=enhance_images,
        remove_letterbox=remove_letterbox,
        add_titles=add_titles,
        title_font=title_font,
        season_font=season_font,
        add_season_episode_text=add_season_episode_text
    )