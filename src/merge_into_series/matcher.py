"""Episode matching logic using fuzzy string matching."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz, process

from .tvdb_scraper import Episode


class EpisodeMatcher:
    """Match filenames to episode data using fuzzy matching."""

    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.mpg', '.mpeg', '.m4v', '.wmv'}

    def __init__(self, episodes: List[Episode]):
        self.episodes = episodes
        self.episode_by_title = {ep.title.lower(): ep for ep in episodes}

    def find_video_files(self, source_pattern: str) -> List[Path]:
        """Find all video files matching the source pattern."""
        source_path = Path(source_pattern)
        video_files = []

        if source_path.is_file():
            if source_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                video_files.append(source_path)
        elif source_path.is_dir():
            # Recursively find video files
            for file_path in source_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                    video_files.append(file_path)
        else:
            # Try glob pattern
            from glob import glob
            for match in glob(str(source_path)):
                path = Path(match)
                if path.is_file() and path.suffix.lower() in self.VIDEO_EXTENSIONS:
                    video_files.append(path)

        return sorted(video_files)

    def extract_title_from_filename(self, filename: str) -> str:
        """Extract the likely title from a filename."""
        # Remove file extension
        title = Path(filename).stem

        # Common patterns to remove
        patterns_to_remove = [
            r'\(\([^)]+\)\)',  # Remove ((dashfhd)) type patterns
            r'\([^)]+\)',      # Remove other parentheses content
            r'\[[^\]]+\]',     # Remove bracket content
            r'\b\d{4}\b',      # Remove years
            r'\b(720p|1080p|480p|4K|2160p)\b',  # Remove quality indicators
            r'\b(x264|x265|h264|h265)\b',       # Remove codec info
            r'\b(WEBRip|BluRay|DVDRip|HDTV)\b', # Remove source info
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Clean up multiple spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()

        return title

    def match_episode(self, filename: str, threshold: int = 80) -> List[Tuple[Episode, int]]:
        """Find matching episodes for a filename."""
        extracted_title = self.extract_title_from_filename(filename)

        # Try to remove common series prefixes
        # Look for patterns like "Series Name - Episode Title"
        if ' - ' in extracted_title:
            parts = extracted_title.split(' - ', 1)
            if len(parts) == 2:
                extracted_title = parts[1].strip()

        matches = []
        episode_titles = [ep.title for ep in self.episodes]

        # Use fuzzy matching to find similar titles
        fuzzy_matches = process.extract(
            extracted_title,
            episode_titles,
            scorer=fuzz.token_sort_ratio,
            limit=10
        )

        for match_title, score in fuzzy_matches:
            if score >= threshold:
                # Find the episode with this title
                episode = next(ep for ep in self.episodes if ep.title == match_title)
                matches.append((episode, score))

        # Also try partial matching (in case the title is contained within filename)
        for episode in self.episodes:
            if episode.title.lower() in extracted_title.lower():
                score = fuzz.partial_ratio(episode.title.lower(), extracted_title.lower())
                if score >= threshold:
                    # Avoid duplicates
                    if not any(ep.title == episode.title for ep, _ in matches):
                        matches.append((episode, score))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def get_best_match(self, filename: str, threshold: int = 80) -> Optional[Episode]:
        """Get the single best match for a filename."""
        matches = self.match_episode(filename, threshold)
        if matches:
            return matches[0][0]
        return None

    def get_filename_for_episode(self, episode: Episode, original_filename: str) -> str:
        """Generate a new filename for an episode."""
        original_path = Path(original_filename)
        extension = original_path.suffix

        # Clean the episode title for use in filename
        clean_title = re.sub(r'[<>:"/\\|?*]', '', episode.title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()

        return f"{episode.season_episode_code} {clean_title}{extension}"

    def get_season_directory(self, episode: Episode) -> str:
        """Get the season directory name for an episode."""
        return f"Season {episode.season:02d}"