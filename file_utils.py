from load_config import config
import re
import subprocess

from pathlib import Path
from typing import Tuple

from log_config import logger
import language_tool_python


tool = language_tool_python.LanguageTool('en-US')

# Function to check and correct grammar in the episode title
def correct_grammar(text: str) -> str:
    """Corrects the grammar of a given text and logs corrections if needed."""

    if config['features'].get('check_grammar', False):
        matches = tool.check(text)
        corrected_text = language_tool_python.utils.correct(text, matches)

        if corrected_text == text:
            logger.debug("Title's grammar is okay.")
        else:
            logger.info(f"Corrected title's grammar from '{text}' to '{corrected_text}'")
    else:
        logger.debug("Grammar checking is disabled.")

    return corrected_text


def clean_episode_title(title: str) -> str:
    """Clean up unnecessary parts from episode titles, similar to Plex's method."""
    if title:
        # Remove any content in square or round brackets, including nested ones
        title = re.sub(r'\[[^\]]*\]', '', title)
        title = re.sub(r'\([^\)]*\)', '', title)

        # Remove common video quality tags and other release info
        # This regex targets typical tags like WEB-DL, BluRay, x264, h264, etc.
        title = re.sub(
            r'\b(WEB[-\. ]?DL|WEB[-\. ]?Rip|Blu[-\. ]?Ray|BDRip|HDRip|HDTV|DVDRip|x264|x265|h\.?264|h\.?265|HEVC|AAC2?\.?0|AAC5\.1|EAC3|DDP5\.1|DD5\.1|Atmos|TrueHD)\b',
            '',
            title,
            flags=re.IGNORECASE
        )

        # Remove release group names, which are often at the end after a dash
        title = re.sub(r'[-_.]\s*[A-Za-z0-9]+$', '', title)

        # Replace underscores and periods with spaces
        title = re.sub(r'[_\.]', ' ', title)

        # Remove extra spaces
        title = re.sub(r'\s{2,}', ' ', title)

        # Trim leading and trailing spaces and punctuation
        title = title.strip(' -.')
        
        title = correct_grammar(title)

    return title.strip()

def extract_from_filename(filename: str) -> Tuple[str, str, str, str]:
    """Extract show name, season number, episode number, and episode title from filename."""
    regex = re.compile(r"(.*?)[ ._-]+[Ss]?(\d+)[Ee]?(\d+)[ ._-]+(.*?)\.[a-zA-Z0-9]+$")
    match = regex.match(filename)
    if match:
        show_name = match.group(1).replace(".", " ").strip()
        season_number = match.group(2)
        episode_number = match.group(3)
        episode_title = match.group(4).replace(".", " ").strip()
    else:
        show_name = Path(filename).stem
        season_number = "1"
        episode_number = "1"
        episode_title = "Untitled Episode"

    episode_title = clean_episode_title(episode_title)
    return show_name, season_number, episode_number, episode_title

def get_video_duration(video_path: Path) -> float:
    """Retrieve video duration using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return float(duration_str)
        else:
            logger.error(f"No duration found for {video_path}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving duration for {video_path}: {e}")
        return None

def extract_episode_metadata(video_path: Path) -> Tuple[str, str, str, str]:
    """Extract episode metadata from video file."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format_tags=title,season_number,episode_sort,show', '-of', 'default=noprint_wrappers=1', str(video_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        tags = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                tags[key] = value

        show_name = tags.get('TAG:show') or tags.get('TAG:album') or ''
        season_number = tags.get('TAG:season_number') or '1'
        episode_number = tags.get('TAG:episode_sort') or '1'
        episode_title = tags.get('TAG:title') or ''

        if not all([show_name, season_number, episode_number, episode_title]):
            # Fallback to filename parsing
            return extract_from_filename(video_path.name)

        episode_title = clean_episode_title(episode_title)
        return show_name, season_number, episode_number, episode_title
    except Exception as e:
        logger.error(f"Error extracting metadata from {video_path}: {e}")
        # Fallback to filename parsing
        return extract_from_filename(video_path.name)