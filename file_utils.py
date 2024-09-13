import re
from typing import Tuple
from pathlib import Path
import subprocess
import logging
import json

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