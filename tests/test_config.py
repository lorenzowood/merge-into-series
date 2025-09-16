"""Tests for configuration handling."""

import tempfile
from pathlib import Path

import pytest

from merge_into_series.config import Config


def test_config_loading():
    """Test loading configuration from file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
        f.write("""# Test config
Storyville, /path/to/storyville, https://thetvdb.com/series/storyville/allseasons/official
Arena, /path/to/arena, https://thetvdb.com/series/arena/allseasons/official
# Comment line
Invalid Line Without Commas
""")
        config_path = f.name

    try:
        config = Config(config_path)

        # Test case-insensitive lookup
        storyville = config.get_series_config('storyville')
        assert storyville is not None
        assert storyville['name'] == 'Storyville'
        assert storyville['target_path'] == '/path/to/storyville'
        assert storyville['tvdb_url'] == 'https://thetvdb.com/series/storyville/allseasons/official'

        # Test case-insensitive lookup
        arena = config.get_series_config('ARENA')
        assert arena is not None
        assert arena['name'] == 'Arena'

        # Test non-existent series
        missing = config.get_series_config('nonexistent')
        assert missing is None

        # Test list all series
        all_series = config.list_series()
        assert 'storyville' in all_series
        assert 'arena' in all_series

    finally:
        Path(config_path).unlink()


def test_empty_config():
    """Test handling of empty or non-existent config file."""
    with tempfile.NamedTemporaryFile(delete=True) as f:
        non_existent_path = f.name + "_not_exists"

    config = Config(non_existent_path)
    assert config.get_series_config('anything') is None
    assert len(config.list_series()) == 0


def test_create_example_config():
    """Test creating example configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.conf"
        config = Config(str(config_path))
        config.create_example_config()

        assert config_path.exists()
        content = config_path.read_text()
        assert 'Storyville' in content
        assert 'Arena' in content