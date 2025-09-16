"""Configuration file handling for merge-into-series."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class Config:
    """Handle configuration file parsing and series lookup."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.merge-into-series.conf")
        self.config_path = Path(config_path)
        self._series_config = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    try:
                        parts = line.split(',', 2)
                        if len(parts) != 3:
                            print(f"Warning: Invalid config line {line_num}: {line}")
                            continue

                        series_name, target_path, tvdb_url = [p.strip() for p in parts]
                        self._series_config[series_name.lower()] = {
                            'name': series_name,
                            'target_path': target_path,
                            'tvdb_url': tvdb_url
                        }
                    except Exception as e:
                        print(f"Warning: Error parsing config line {line_num}: {e}")

        except Exception as e:
            print(f"Error reading config file {self.config_path}: {e}")

    def get_series_config(self, series_name: str) -> Optional[Dict[str, str]]:
        """Get configuration for a series (case-insensitive lookup)."""
        return self._series_config.get(series_name.lower())

    def list_series(self) -> Dict[str, Dict[str, str]]:
        """Get all configured series."""
        return dict(self._series_config)

    def create_example_config(self):
        """Create an example configuration file."""
        example_content = """# merge-into-series configuration file
# Format: Series Name, Target Path, TVDB URL
#
# This assumes your TV shows are organized in /Media/TV/
# Adjust the paths below to match your setup.
#
# Examples:
Storyville, /Media/TV/Storyville (1997) {tvdb-82300}, https://thetvdb.com/series/storyville/allseasons/official
Arena, /Media/TV/Arena (1975) {tvdb-80379}, https://thetvdb.com/series/arena/allseasons/official
"""

        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(example_content)

        print(f"Created example configuration file at {self.config_path}")
        print("Please edit it to add your series configurations.")