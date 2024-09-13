import sys

from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List
from ffmpy import FFmpeg

from rich.console import Console
from rich.progress import track
# from logging.handlers import RotatingFileHandler
from image_utils import detect_and_remove_letterbox, enhance_image, resize_image_to_target_dimensions
from file_utils import extract_episode_metadata, get_video_duration
from text_utils import add_episode_title
from log_config import logger

# Console for user interaction
console = Console()



# Root directory of the script
ROOT_DIR = Path(__file__).parent.absolute()

def load_fonts_from_directory(fonts_dir: Path) -> List[str]:
    """
    Load all font filenames from the specified directory.
    """
    fonts = []
    if not fonts_dir.exists():
        logger.error(f"Font directory '{fonts_dir}' does not exist.")
        console.print(f"[red]Error: Font directory '{fonts_dir}' does not exist.[/red]")
        return fonts

    for file in fonts_dir.iterdir():
        if file.suffix.lower() in ['.ttf', '.otf']:
            fonts.append(file.name)

    if not fonts:
        logger.warning(f"No fonts found in the specified directory: {fonts_dir}")
        console.print("[red]No fonts found in the specified directory.[/red]")

    return fonts

def prompt_user_inputs():
    # Prompt for the source directory with default "./source"
    source_dir_input = console.input("[bold blue]Enter the source directory for MKV files (default: ./source): [/bold blue]").strip()
    source_dir = Path(source_dir_input or "./source").resolve()

    # Validate source directory
    if not source_dir.is_dir():
        console.print(f"[red]Invalid directory! '{source_dir}' does not exist.[/red]")
        sys.exit(1)

    # Prompt for the number of screenshots with default 3
    while True:
        num_screenshots_input = console.input("[bold blue]Enter number of screenshots per video (default: 3): [/bold blue]").strip()
        if not num_screenshots_input:
            num_screenshots = 3
            break
        try:
            num_screenshots = int(num_screenshots_input)
            if num_screenshots > 0:
                break
            else:
                console.print("[red]Please enter a positive integer.[/red]")
        except ValueError:
            console.print("[red]Invalid input! Please enter a valid integer.[/red]")

    # Prompt for the aspect ratio with default 16:9
    aspect_ratio_input = console.input("[bold blue]Choose aspect ratio (16:9 or 4:3, default: 16:9): [/bold blue]").strip()
    aspect_ratio = aspect_ratio_input or "16:9"
    if aspect_ratio not in ["16:9", "4:3"]:
        console.print("[red]Invalid aspect ratio! Defaulting to 16:9.[/red]")
        aspect_ratio = "16:9"

    # Prompt for overwrite existing screenshots with default Yes
    overwrite_existing_input = console.input("[bold blue]Overwrite existing screenshots? (Y/N, default: Y): [/bold blue]").strip().lower()
    overwrite_existing = overwrite_existing_input in ['y', 'yes'] if overwrite_existing_input else True

    # Prompt for image enhancement with default Yes
    enhance_images_input = console.input("[bold blue]Enhance images? (Y/N, default: Y): [/bold blue]").strip().lower()
    enhance_images = enhance_images_input in ['y', 'yes'] if enhance_images_input else True

    # Prompt for letterbox removal with default Yes
    remove_letterbox_input = console.input("[bold blue]Remove letterboxes? (Y/N, default: Y): [/bold blue]").strip().lower()
    remove_letterbox = remove_letterbox_input in ['y', 'yes'] if remove_letterbox_input else True

    return source_dir, num_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox

def prompt_user_text_customization(fonts_dir: Path) -> Tuple[str, str, bool]:
    """
    Prompt user for text customization options.
    """
    title_font = season_font = None
    add_season_episode_text = False

    # Load available fonts
    available_fonts = load_fonts_from_directory(fonts_dir)
    if not available_fonts:
        console.print(f"[red]No fonts available in '{fonts_dir}'. Please add font files and try again.[/red]")
        sys.exit(1)

    # Select title font
    console.print("\n[yellow]Available fonts for Episode Title text:[/yellow]")
    for idx, font in enumerate(available_fonts, 1):
        console.print(f"[{idx}] {font}")

    while True:
        choice = console.input("[yellow]Choose a font for the Episode Title text (enter number): [/yellow]").strip()
        try:
            title_font = available_fonts[int(choice) - 1]
            break
        except (ValueError, IndexError):
            console.print("[red]Invalid choice. Please select a valid number from the list.[/red]")

    # Prompt to include season/episode text
    include_season_text_input = console.input("[yellow]Include Season X – Episode Y above the title? (Y/N, default: Y): [/yellow]").strip().lower()
    add_season_episode_text = include_season_text_input in ['y', 'yes'] if include_season_text_input else True

    # Select season font if applicable
    if add_season_episode_text:
        console.print("\n[yellow]Available fonts for Season/Episode text:[/yellow]")
        for idx, font in enumerate(available_fonts, 1):
            console.print(f"[{idx}] {font}")

        while True:
            choice = console.input("[yellow]Choose a font for the Season/Episode text (enter number): [/yellow]").strip()
            try:
                season_font = available_fonts[int(choice) - 1]
                break
            except (ValueError, IndexError):
                console.print("[red]Invalid choice. Please select a valid number from the list.[/red]")

    return title_font, season_font, add_season_episode_text

def _calculate_timestamps(duration: float, num_screenshots: int) -> List[str]:
    """
    Calculate evenly spaced timestamps within the video duration.
    """
    timestamps = []
    interval = duration / (num_screenshots + 1)
    for i in range(1, num_screenshots + 1):
        timestamp = str(datetime.fromtimestamp(interval * i, tz=timezone.utc).strftime('%H:%M:%S'))
        timestamps.append(timestamp)
    return timestamps

class ScreenshotManager:
    def __init__(
        self,
        file_info,
        duration,
        video_path,
        num_screenshots,
        output_dir,
        aspect_ratio,
        overwrite_existing,
        enhance_images,
        remove_letterbox,
        add_titles,
        title_font=None,
        season_font=None,
        add_season_episode_text=False
    ):
        self.video_path = video_path
        self.duration = duration
        self.num_screenshots = num_screenshots
        self.show_name, self.season_number, self.episode_number, self.episode_title = file_info
        self.output_dir = output_dir
        self.aspect_ratio = aspect_ratio
        self.overwrite_existing = overwrite_existing
        self.enhance_images = enhance_images
        self.remove_letterbox = remove_letterbox
        self.add_titles = add_titles
        self.title_font = title_font
        self.season_font = season_font
        self.add_season_episode_text = add_season_episode_text
        logger.info(f"Screenshots will be saved for {self.show_name} - S{self.season_number.zfill(2)}E{self.episode_number.zfill(2)}")

    def _screenshot_exists(self, output_file: Path) -> bool:
        return output_file.exists()

    def _run_ffmpeg(self, timestamp: str, output_file: Path):
        vf_filter = None
        if self.aspect_ratio == "16:9":
            vf_filter = "scale=iw*sar:ih,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        elif self.aspect_ratio == "4:3":
            vf_filter = "scale=iw*sar:ih,scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2"

        inputs = [self.video_path, "-loglevel", "panic", "-ss", timestamp]
        outputs = [str(output_file), "-frames:v", "1", "-q:v", "2", "-pix_fmt", "rgb24"]
        if vf_filter:
            outputs.extend(["-vf", vf_filter])

        ff = FFmpeg(
            inputs={str(self.video_path): inputs[1:]},
            outputs={str(output_file): outputs[1:]}
        )
        ff.run()

    def _generate_screenshot(self, timestamp: str, output_file: Path):
        try:
            if not self._screenshot_exists(output_file) or self.overwrite_existing:
                self._run_ffmpeg(timestamp, output_file)

                if not output_file.exists():
                    logger.error(f"Screenshot was not generated: {output_file}")
                    return

                if self.remove_letterbox:
                    detect_and_remove_letterbox(output_file, output_file, self.aspect_ratio)

                # Resize to target dimensions based on aspect ratio
                resize_image_to_target_dimensions(output_file, self.aspect_ratio)
                
                if self.enhance_images:
                    enhance_image(output_file)

                if self.add_titles:
                    season_episode_text = f"Season {self.season_number.zfill(2)} – Episode {self.episode_number.zfill(2)}" if self.add_season_episode_text else None
                    add_episode_title(
                        output_file,
                        self.episode_title,
                        self.aspect_ratio,
                        self.title_font,
                        self.season_font,
                        season_episode_text
                    )

               
            else:
                logger.info(f"Screenshot already exists and overwrite is disabled: {output_file}")
        except Exception as e:
            logger.error(f"Failed to generate screenshot for {output_file}: {e}")

    def generate_screenshots(self):
        timestamps = _calculate_timestamps(self.duration, self.num_screenshots)
        output_files = [
            self.output_dir / f"{self.show_name} - S{self.season_number.zfill(2)}E{self.episode_number.zfill(2)} - {self.episode_title} - ({timestamp.replace(':', '.')}).png"
            for timestamp in timestamps
        ]

        console.print(f"\n[bold green]Taking screenshots for:[/bold green] [yellow]{self.show_name}[/yellow]")
        console.print(f"[bold green]Season:[/bold green] [yellow]{self.season_number}[/yellow]")
        console.print(f"[bold green]Episode:[/bold green] [yellow]{self.episode_number}[/yellow]")
        console.print(f"[bold green]Title:[/bold green] [yellow]{self.episode_title}[/yellow]")
        console.print(f"[bold green]Aspect Ratio:[/bold green] [yellow]{self.aspect_ratio}[/yellow]")


        for timestamp, output_file in track(zip(timestamps, output_files), description="Taking screenshots...", total=len(timestamps)):
            self._generate_screenshot(timestamp, output_file)

def process_videos_in_directory(
    source_dir: Path,
    num_screenshots: int,
    aspect_ratio: str,
    overwrite_existing: bool,
    enhance_images: bool,
    remove_letterbox: bool,
    add_titles: bool,
    title_font: str = None,
    season_font: str = None,
    add_season_episode_text: bool = False
):
    
    mkv_files = sorted(source_dir.rglob("*.mkv"))

    if not mkv_files:
        console.print("[red]No MKV files found in the source directory![/red]")
        return

    failed_files = []
    total_screenshots = 0
    total_episodes = 0
    total_failures = 0

    for mkv_file in mkv_files:
        console.print(f"\n[bold blue]Processing file:[/bold blue] {mkv_file.name}")
        try:
            file_info = extract_episode_metadata(mkv_file)
            duration = get_video_duration(mkv_file)
            if not duration:
                console.print(f"[red]Skipping {mkv_file.name} due to invalid duration.[/red]")
                failed_files.append(mkv_file.name)
                total_failures += 1
                continue

            # Prepare output directories
            output_dir = ROOT_DIR / "output" / file_info[0] / f"Season {file_info[1].zfill(2)}"
            output_dir.mkdir(parents=True, exist_ok=True)

            manager = ScreenshotManager(
                file_info=file_info,
                duration=duration,
                video_path=mkv_file,
                num_screenshots=num_screenshots,
                output_dir=output_dir,
                aspect_ratio=aspect_ratio,
                overwrite_existing=overwrite_existing,
                enhance_images=enhance_images,
                remove_letterbox=remove_letterbox,
                add_titles=add_titles,
                title_font=title_font,
                season_font=season_font,
                add_season_episode_text=add_season_episode_text
            )
            manager.generate_screenshots()
            total_screenshots += num_screenshots
            total_episodes += 1
        except Exception as e:
            logger.error(f"Error processing {mkv_file.name}: {e}")
            total_failures += 1

    console.print(f"\n[bold green]Successfully created {total_screenshots} images for {total_episodes} episodes.[/bold green]")
    if total_failures > 0:
        console.print(f"[bold red]Failed to process {total_failures} file(s).[/bold red]")
        console.error(f"[bold red]List of failed files:[/bold red]")
        for failed_file in failed_files:
            console.error(f"[bold red] - {failed_file}[/bold red]")

if __name__ == "__main__":
    try:
        # Get user inputs
        source_dir, num_screenshots, aspect_ratio, overwrite_existing, enhance_images, remove_letterbox = prompt_user_inputs()

        # Prompt for text customization
        add_titles_input = console.input("[bold blue]Add episode titles to screenshots? (Y/N, default: Y): [/bold blue]").strip().lower()
        add_titles = add_titles_input in ['y', 'yes'] if add_titles_input else True

        if add_titles:
            fonts_dir = ROOT_DIR / "fonts"
            title_font, season_font, add_season_episode_text = prompt_user_text_customization(fonts_dir)
        else:
            title_font = season_font = None
            add_season_episode_text = False

        # Process videos
        process_videos_in_directory(
            source_dir=source_dir,
            num_screenshots=num_screenshots,
            aspect_ratio=aspect_ratio,
            overwrite_existing=overwrite_existing,
            enhance_images=enhance_images,
            remove_letterbox=remove_letterbox,
            add_titles=add_titles,
            title_font=title_font,
            season_font=season_font,
            add_season_episode_text=add_season_episode_text
        )
    except KeyboardInterrupt:
        console.print("\n[bold red]Process interrupted by user. Exiting gracefully.[/bold red]")
        sys.exit(0)