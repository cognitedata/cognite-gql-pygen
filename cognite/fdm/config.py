import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PWD = Path().absolute()

CONFIG_FILE = os.environ.get("FDM_CONFIG", PWD / "config.yaml")

__all__ = [
    "CONFIG",
    "PWD",
]

# TODO since this is in an installable package now, we should refactor to remove the need for a config file.
try:
    with open(CONFIG_FILE) as f:
        CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    logger.error("config.yaml not found. Please see README.md to setup information.")
    exit(1)