from pathlib import Path
import yaml

# Adjust this to point to the root directory, one level above `modules`
config_file = Path(__file__).parent.parent / "config.yaml"

def load_config():
    """Load the logging configuration from the YAML file."""
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config

config = load_config()  # Load the config