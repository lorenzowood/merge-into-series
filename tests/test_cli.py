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
    assert 'merge-into-series' in result.output.lower()
    assert 'SERIES_NAME' in result.output
    assert 'SOURCE_PATTERN' in result.output


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
def test_no_episodes_found(mock_scraper_class, temp_config, temp_video_files):
    """Test behavior when no episodes are found from TVDB."""
    # Mock scraper to return no episodes
    mock_scraper = Mock()
    mock_scraper.scrape_episodes.return_value = []
    mock_scraper_class.return_value = mock_scraper

    runner = CliRunner()

    result = runner.invoke(main, [
        '--config', temp_config,
        'storyville',
        str(temp_video_files)
    ])

    assert result.exit_code == 1
    assert 'No episodes found' in result.output


def test_no_video_files(temp_config):
    """Test behavior when no video files are found."""
    with tempfile.TemporaryDirectory() as empty_dir:
        runner = CliRunner()

        # Mock scraper to avoid network calls
        with patch('merge_into_series.cli.TVDBScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper.scrape_episodes.return_value = [Mock()]
            mock_scraper_class.return_value = mock_scraper

            result = runner.invoke(main, [
                '--config', temp_config,
                'storyville',
                empty_dir
            ])

            assert result.exit_code == 1
            assert 'No video files found' in result.output


@patch('merge_into_series.cli.TVDBScraper')
@patch('merge_into_series.cli.InteractiveInterface')
def test_dry_run(mock_interface_class, mock_scraper_class, temp_config, temp_video_files):
    """Test dry run functionality."""
    # Mock scraper
    mock_scraper = Mock()
    mock_scraper.scrape_episodes.return_value = [Mock(title="Test Episode")]
    mock_scraper_class.return_value = mock_scraper

    # Mock interface
    mock_interface = Mock()
    mock_interface.get_user_matches.return_value = {"test.mkv": Mock()}
    mock_interface.confirm_operations.return_value = True
    mock_interface.get_pending_operations.return_value = []
    mock_interface_class.return_value = mock_interface

    runner = CliRunner()

    result = runner.invoke(main, [
        '--config', temp_config,
        '--dry-run',
        'storyville',
        str(temp_video_files)
    ])

    assert result.exit_code == 0
    assert 'DRY RUN' in result.output


def test_keyboard_interrupt(temp_config):
    """Test handling of keyboard interrupt."""
    runner = CliRunner()

    # Mock scraper to raise KeyboardInterrupt
    with patch('merge_into_series.cli.TVDBScraper') as mock_scraper_class:
        mock_scraper_class.side_effect = KeyboardInterrupt()

        result = runner.invoke(main, [
            '--config', temp_config,
            'storyville',
            '/tmp/test'
        ])

        assert result.exit_code == 1
        assert 'cancelled' in result.output.lower()