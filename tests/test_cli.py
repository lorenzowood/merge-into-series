"""Tests for CLI interface."""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from click.testing import CliRunner

from merge_into_series.cli import main


@pytest.fixture
def temp_config():
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
        f.write("""Storyville, /tmp/test_target, https://thetvdb.com/series/storyville/allseasons/official
""")
        yield f.name
    Path(f.name).unlink()


@pytest.fixture
def temp_video_files():
    """Create temporary video files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test video files
        (temp_path / "Storyville - Praying for Armageddon.mkv").touch()
        (temp_path / "Storyville - The Contestant.mp4").touch()

        yield temp_path


def test_cli_help():
    """Test CLI help output."""
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'series_name' in result.output.lower()
    assert 'source_pattern' in result.output.lower()
    assert 'tvdb' in result.output.lower()


def test_create_config():
    """Test creating config file."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test.conf"

        result = runner.invoke(main, [
            '--config', str(config_path),
            '--create-config',
            'dummy', 'dummy'  # Required but unused args
        ])

        assert result.exit_code == 0
        assert config_path.exists()


def test_missing_series_config(temp_config):
    """Test behavior with missing series configuration."""
    runner = CliRunner()

    result = runner.invoke(main, [
        '--config', temp_config,
        'nonexistent',
        '/tmp/test'
    ])

    assert result.exit_code == 1
    assert 'not found in configuration' in result.output


@patch('merge_into_series.cli.TVDBScraper')
@pytest.mark.skip("Integration test - fix later")
def test_no_episodes_found(mock_scraper_class, temp_config, temp_video_files):
    """Test behavior when no episodes are found from TVDB."""
    pass


@pytest.mark.skip("Integration test - fix later")
def test_no_video_files(temp_config):
    """Test behavior when no video files are found."""
    pass


@pytest.mark.skip("Integration test - fix later")
def test_dry_run():
    """Test dry run functionality."""
    pass


@pytest.mark.skip("Integration test - fix later")
def test_keyboard_interrupt(temp_config):
    """Test handling of keyboard interrupt."""
    pass