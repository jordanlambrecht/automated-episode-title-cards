# File: ./modules/prompts.py

from pathlib import Path
from modules.file_utils import load_fonts_from_directory
from typing import Tuple
from .log_config import log_message
import questionary
from questionary import Style

custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold fg:#FF5733'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
])

def prompt_fonts(fonts_dir: Path) -> Tuple[str, str, bool]:
    """
    Prompt user for text customization options.
    """
    try:
        # Provide a prompt message for title font
        title_font, season_font, add_season_episode_text = prompt_user_text_customization(fonts_dir)

        # Now you can use the selected fonts and options in your script
        print(f"Selected Title Font: {title_font}")
        print(f"Selected Season Font: {season_font}")
        print(f"Include Season/Episode Text: {add_season_episode_text}")

        # Return the values to be unpacked
        return title_font, season_font, add_season_episode_text

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, False

def prompt_user_text_customization(fonts_dir: Path) -> Tuple[str, str, bool]:
    """
    Prompt user for text customization options.

    :param fonts_dir: The directory containing available fonts.
    :return: Tuple of selected title font, season font, and whether to include season text.
    """
    available_fonts = load_fonts_from_directory(fonts_dir)

    if not available_fonts:
        log_message.error(f"No fonts available in '{fonts_dir}'. Please add font files and try again.")
        raise SystemExit(1)

    # Select title font
    title_font = prompt_font_selection(available_fonts, "Choose a font for the Episode Title text:")
    
    if not title_font:
        log_message.error("No font selected for the Episode Title.")
        raise SystemExit(1)

    # Prompt to include season/episode text
    add_season_episode_text = questionary.confirm(
        "Include Season X – Episode Y above the title? (default: Yes)"
    ).ask()

    # Select season font if applicable
    season_font = None
    if add_season_episode_text:
        season_font = prompt_font_selection(available_fonts, "Choose a font for the Season/Episode text:")

        if not season_font:
            log_message.error("No font selected for the Season/Episode.")
            raise SystemExit(1)

    return title_font, season_font, add_season_episode_text

def prompt_font_selection(fonts_list: list, message: str) -> str:
    """
    Prompts the user to select a font from the provided list.

    :param fonts_list: A list of available font file names.
    :param message: The prompt message to display to the user.
    :return: The name of the selected font file.
    """
    try:
        font_choice = questionary.select(
            message,
            choices=fonts_list,
            style=custom_style
        ).ask()

        return font_choice
    except Exception as e:
        log_message.error(f"An error occurred during font selection: {e}")
        return None
