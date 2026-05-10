"""Configuration file handling for merge-into-series."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _normalize_to_words(name: str) -> List[str]:
    """Split a name into lowercase words, handling camelCase, underscores, and hyphens."""
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    words = re.split(r'[^a-zA-Z0-9]+', name)
    return [w.lower() for w in words if w]


def _words_match_subsequence(query_words: List[str], series_words: List[str]) -> bool:
    """Return True if every query word is a prefix-match of some series word, in order."""
    series_idx = 0
    for qw in query_words:
        found = False
        while series_idx < len(series_words):
            if series_words[series_idx].startswith(qw):
                series_idx += 1
                found = True
                break
            series_idx += 1
        if not found:
            return False
    return True


class Config:
    """Handle configuration file parsing and series lookup."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.merge-into-series.conf")
        self.config_path = Path(config_path)
        self._root: Optional[Path] = None
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

                    if line.upper().startswith('ROOT:'):
                        self._root = Path(line[5:].strip())
                        continue

                    try:
                        # Split on the URL first (anchored to http) so commas in
                        # the directory name (e.g. "Maps: Power, Plunder...") don't
                        # confuse a simple split(',', 2).
                        url_match = re.search(r',\s*(https?://\S+)\s*$', line)
                        if not url_match:
                            print(f"Warning: Invalid config line {line_num}: {line}")
                            continue
                        tvdb_url = url_match.group(1)
                        remainder = line[:url_match.start()]
                        comma_idx = remainder.index(',')
                        series_name = remainder[:comma_idx].strip()
                        target_path = remainder[comma_idx + 1:].strip()
                        resolved = self._resolve_path(target_path)
                        self._series_config[series_name.lower()] = {
                            'name': series_name,
                            'target_path': str(resolved),
                            'tvdb_url': tvdb_url
                        }
                    except Exception as e:
                        print(f"Warning: Error parsing config line {line_num}: {e}")

        except Exception as e:
            print(f"Error reading config file {self.config_path}: {e}")

    def _resolve_path(self, target_path: str) -> Path:
        """Return an absolute path, joining against ROOT if the path is relative."""
        p = Path(target_path)
        if p.is_absolute() or self._root is None:
            return p
        return self._root / p

    def get_series_config(self, series_name: str) -> Optional[Dict[str, str]]:
        """Get configuration for a series (case-insensitive exact lookup)."""
        return self._series_config.get(series_name.lower())

    def find_fuzzy_matches(self, query: str) -> List[Dict[str, str]]:
        """Return configs whose names fuzzy-match query (word-prefix subsequence).

        All query words (≥3 chars) must appear in order as prefixes of words in
        the series name. E.g. 'mankind' matches 'For_All_Mankind' but not 'Landman'.
        """
        query_words = [w for w in _normalize_to_words(query) if len(w) >= 3]
        if not query_words:
            return []
        return [
            cfg for cfg in self._series_config.values()
            if _words_match_subsequence(query_words, _normalize_to_words(cfg['name']))
        ]

    def add_series(self, name: str, path: str, url: str) -> bool:
        """Append a new series entry to the config file.

        Returns False without writing if the name already exists (case-insensitive).
        """
        if self.get_series_config(name):
            return False

        existing = self.config_path.read_text(encoding='utf-8') if self.config_path.exists() else ''
        with open(self.config_path, 'a', encoding='utf-8') as f:
            if existing and not existing.endswith('\n'):
                f.write('\n')
            f.write(f"{name}, {path}, {url}\n")

        return True

    def list_series(self) -> Dict[str, Dict[str, str]]:
        """Get all configured series."""
        return dict(self._series_config)

    def create_example_config(self):
        """Create an example configuration file."""
        example_content = """# merge-into-series configuration file
# Format: Series Name, Target Path, TVDB URL
#
# Optional: set ROOT to a shared parent directory. Series paths that don't
# start with / are then treated as subdirectories of ROOT.
ROOT: /Media/TV

Storyville, Storyville (1997) {tvdb-82300}, https://thetvdb.com/series/storyville/allseasons/official
Arena, Arena (1975) {tvdb-80379}, https://thetvdb.com/series/arena/allseasons/official

# Absolute paths still work and override ROOT:
# Other_Show, /Different/Location/Other Show, https://thetvdb.com/series/other-show/allseasons/official
"""

        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(example_content)

        print(f"Created example configuration file at {self.config_path}")
        print("Please edit it to add your series configurations.")