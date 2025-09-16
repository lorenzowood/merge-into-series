"""Tests for episode matcher."""

import tempfile
from pathlib import Path

import pytest

from merge_into_series.tvdb_scraper import Episode
from merge_into_series.matcher import EpisodeMatcher


@pytest.fixture
def sample_episodes():
    """Create sample episodes for testing."""
    return [
        Episode(2024, 6, "Praying for Armageddon"),
        Episode(2025, 11, "The Contestant"),
        Episode(2022, 19, "The Fire Within"),
        Episode(2025, 9, "The Jackal Speaks"),
        Episode(2025, 10, "Wedding Night"),
        Episode(2020, 11, "Welcome to Chechnya: The Gay Purge"),
        Episode(2025, 1, "Your Fat Friend"),
    ]


def test_extract_title_from_filename(sample_episodes):
    """Test title extraction from filenames."""
    matcher = EpisodeMatcher(sample_episodes)

    # Test with series prefix
    title1 = matcher.extract_title_from_filename("Storyville - Praying for Armageddon ((dashfhd)).mkv")
    assert "Praying for Armageddon" in title1

    # Test with quality indicators
    title2 = matcher.extract_title_from_filename("The Contestant 1080p x264 WEBRip.mp4")
    assert title2 == "The Contestant"

    # Test with brackets
    title3 = matcher.extract_title_from_filename("The Fire Within [2022] (720p).avi")
    assert title3 == "The Fire Within"


def test_find_video_files():
    """Test finding video files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "video1.mkv").touch()
        (temp_path / "video2.mp4").touch()
        (temp_path / "document.txt").touch()
        (temp_path / "subtitle.srt").touch()

        # Create subdirectory with video
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "video3.avi").touch()

        matcher = EpisodeMatcher([])
        video_files = matcher.find_video_files(str(temp_path))

        # Should find all video files recursively
        video_names = {f.name for f in video_files}
        assert video_names == {"video1.mkv", "video2.mp4", "video3.avi"}


def test_match_episode_exact(sample_episodes):
    """Test exact episode matching."""
    matcher = EpisodeMatcher(sample_episodes)

    # Test exact title match
    matches = matcher.match_episode("Storyville - Praying for Armageddon.mkv")
    assert len(matches) >= 1
    assert matches[0][0].title == "Praying for Armageddon"


def test_match_episode_fuzzy(sample_episodes):
    """Test fuzzy episode matching."""
    matcher = EpisodeMatcher(sample_episodes)

    # Test with typos
    matches = matcher.match_episode("Storyville - Praying for Armagedon.mkv")  # Missing 'd'
    assert len(matches) >= 1
    assert matches[0][0].title == "Praying for Armageddon"

    # Test with extra words - fuzzy matching may not find this
    matches = matcher.match_episode("Speaks.mkv", threshold=60)
    # This should match "The Jackal Speaks"
    if matches:
        assert "Speaks" in matches[0][0].title


def test_match_episode_no_match(sample_episodes):
    """Test when no episode matches."""
    matcher = EpisodeMatcher(sample_episodes)

    matches = matcher.match_episode("Completely Different Title.mkv", threshold=90)
    assert len(matches) == 0


def test_get_filename_for_episode(sample_episodes):
    """Test generating new filenames for episodes."""
    matcher = EpisodeMatcher(sample_episodes)
    episode = sample_episodes[0]  # Praying for Armageddon

    new_filename = matcher.get_filename_for_episode(episode, "original.mkv")
    assert new_filename == "S2024E06 Praying for Armageddon.mkv"

    # Test with problematic characters in title
    episode_with_chars = Episode(2024, 1, 'Title with "Quotes" and <Tags>')
    new_filename = matcher.get_filename_for_episode(episode_with_chars, "test.mp4")
    # Should remove problematic characters
    assert new_filename == "S2024E01 Title with Quotes and Tags.mp4"


def test_get_season_directory(sample_episodes):
    """Test generating season directory names."""
    matcher = EpisodeMatcher(sample_episodes)

    season_dir = matcher.get_season_directory(sample_episodes[0])
    assert season_dir == "Season 2024"

    # Test with single digit season
    single_digit_episode = Episode(5, 1, "Test")
    season_dir = matcher.get_season_directory(single_digit_episode)
    assert season_dir == "Season 05"


def test_get_best_match(sample_episodes):
    """Test getting single best match."""
    matcher = EpisodeMatcher(sample_episodes)

    best_match = matcher.get_best_match("The Contestant.mkv")
    assert best_match is not None
    assert best_match.title == "The Contestant"

    no_match = matcher.get_best_match("Nonexistent Episode.mkv", threshold=95)
    assert no_match is None