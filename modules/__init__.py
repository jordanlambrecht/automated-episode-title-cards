# File: ./modules/__init__.py

from .file_utils import (
    extract_episode_metadata,
    get_video_duration,
    clean_episode_title,
    load_fonts_from_directory
)
from .image_utils import (
    enhance_image,
    resize_image_to_target_dimensions,
    detect_and_remove_letterbox
)
from .text_utils import add_episode_title
from .log_config import setup_logger, log_message, error
from .introduction import introduction
from .load_config import load_config
from .prompts import prompt_fonts, prompt_user_text_customization

# Load configuration and set up the logger globally
config = load_config()
logger = setup_logger()

__all__ = [
    'extract_episode_metadata',
    'get_video_duration',
    'clean_episode_title',
    'enhance_image',
    'resize_image_to_target_dimensions',
    'detect_and_remove_letterbox',
    'add_episode_title',
    'setup_logger',
    'load_config',
    'log_message',
    'load_fonts_from_directory',
    'config',
    'error',
    'introduction',
    'prompt_user_text_customization',
    'prompt_fonts'
]
