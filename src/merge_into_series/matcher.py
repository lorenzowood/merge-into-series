"""Episode matching logic using fuzzy string matching."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz, process

from .tvdb_scraper import Episode


class EpisodeMatcher:
    """Match filenames to episode data using fuzzy matching."""

    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.mpg', '.mpeg', '.m4v', '.wmv', '.ts'}

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

        # Convert underscores to spaces
        title = title.replace('_', ' ')

        # Normalize ampersand to 'and'
        title = re.sub(r'\s*&\s*', ' and ', title)

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

    def _normalize_for_matching(self, text: str) -> str:
        """Normalize text for matching purposes (not for output)."""
        # Convert & to 'and' for matching
        normalized = re.sub(r'\s*&\s*', ' and ', text)
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized.lower()

    def match_episode(self, filename: str, threshold: int = 80) -> List[Tuple[Episode, int]]:
        """Find matching episodes for a filename."""
        extracted_title = self.extract_title_from_filename(filename)

        # Try to remove common series prefixes
        # Look for patterns like "Series Name - Episode Title"
        if ' - ' in extracted_title:
            parts = extracted_title.split(' - ', 1)
            if len(parts) == 2:
                extracted_title = parts[1].strip()

        # Normalize the extracted title for matching
        normalized_extracted = self._normalize_for_matching(extracted_title)

        matches = []

        # Create normalized title -> episode mapping for matching
        normalized_to_episode = {}
        normalized_titles = []
        for ep in self.episodes:
            norm_title = self._normalize_for_matching(ep.title)
            normalized_to_episode[norm_title] = ep
            normalized_titles.append(norm_title)

        # Use fuzzy matching with normalized titles
        fuzzy_matches = process.extract(
            normalized_extracted,
            normalized_titles,
            scorer=fuzz.token_sort_ratio,
            limit=10
        )

        for norm_match_title, score in fuzzy_matches:
            if score >= threshold:
                episode = normalized_to_episode[norm_match_title]
                matches.append((episode, score))

        # Also try partial matching (in case the title is contained within filename)
        for episode in self.episodes:
            norm_ep_title = self._normalize_for_matching(episode.title)
            if norm_ep_title in normalized_extracted:
                score = fuzz.partial_ratio(norm_ep_title, normalized_extracted)
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

    def find_candidate_matches(self, filename: str, limit: int = 5) -> List[Tuple[Episode, int]]:
        """Find candidate matches using relaxed matching criteria.

        Uses multiple strategies:
        1. Lower threshold fuzzy matching (50 instead of 80)
        2. Word subsequence matching - checks if episode title words appear in filename in order
        """
        extracted_title = self.extract_title_from_filename(filename)

        # Try to remove common series prefixes
        if ' - ' in extracted_title:
            parts = extracted_title.split(' - ', 1)
            if len(parts) == 2:
                extracted_title = parts[1].strip()

        # Normalize for matching
        normalized_extracted = self._normalize_for_matching(extracted_title)

        candidates = {}  # episode.title -> (episode, score)

        # Create normalized title -> episode mapping for matching
        normalized_to_episode = {}
        normalized_titles = []
        for ep in self.episodes:
            norm_title = self._normalize_for_matching(ep.title)
            normalized_to_episode[norm_title] = ep
            normalized_titles.append(norm_title)

        # Strategy 1: Lower threshold fuzzy matching with normalized titles
        fuzzy_matches = process.extract(
            normalized_extracted,
            normalized_titles,
            scorer=fuzz.token_sort_ratio,
            limit=limit * 2
        )

        for norm_match_title, score in fuzzy_matches:
            if score >= 50:  # Lower threshold for candidates
                episode = normalized_to_episode[norm_match_title]
                if episode.title not in candidates or candidates[episode.title][1] < score:
                    candidates[episode.title] = (episode, score)

        # Strategy 2: Word subsequence matching (using normalized text)
        filename_words = self._extract_words(normalized_extracted)

        for episode in self.episodes:
            norm_ep_title = self._normalize_for_matching(episode.title)
            episode_words = self._extract_words(norm_ep_title)
            if not episode_words:
                continue

            # Check what fraction of episode words appear in filename in order
            subsequence_score = self._word_subsequence_score(episode_words, filename_words)

            if subsequence_score >= 60:  # At least 60% of words match in order
                # Convert to 0-100 scale
                if episode.title not in candidates or candidates[episode.title][1] < subsequence_score:
                    candidates[episode.title] = (episode, subsequence_score)

        # Sort by score and return top candidates
        sorted_candidates = sorted(candidates.values(), key=lambda x: x[1], reverse=True)
        return sorted_candidates[:limit]

    def _extract_words(self, text: str) -> List[str]:
        """Extract meaningful words from text, ignoring short words and numbers."""
        words = re.findall(r'[a-z]+', text.lower())
        # Filter out very short words (1-2 chars) that are likely noise
        return [w for w in words if len(w) > 2]

    def _word_subsequence_score(self, episode_words: List[str], filename_words: List[str]) -> int:
        """Calculate what percentage of episode words appear in filename words in order."""
        if not episode_words:
            return 0

        matches = 0
        filename_idx = 0

        for episode_word in episode_words:
            # Look for this word in remaining filename words
            while filename_idx < len(filename_words):
                if filename_words[filename_idx] == episode_word:
                    matches += 1
                    filename_idx += 1
                    break
                filename_idx += 1

        return int((matches / len(episode_words)) * 100)

    def get_filename_for_episode(self, episode: Episode, original_filename: str) -> str:
        """Generate a new filename for an episode."""
        original_path = Path(original_filename)
        extension = original_path.suffix

        # Clean the episode title for use in filename
        clean_title = episode.title.replace(':', ' -')  # Replace colon with space-dash
        clean_title = re.sub(r'[<>"/\\|?*]', '', clean_title)  # Remove other illegal chars
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()

        return f"{episode.season_episode_code} {clean_title}{extension}"

    def get_season_directory(self, episode: Episode) -> str:
        """Get the season directory name for an episode."""
        return f"Season {episode.season:02d}"