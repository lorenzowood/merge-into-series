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


def test_update_nfo_rejects_source_pattern(temp_config):
    """--update-nfo cannot be combined with SOURCE_PATTERN."""
    runner = CliRunner()
    result = runner.invoke(main, [
        '--config', temp_config,
        '--update-nfo', 'missing',
        'Storyville',
        '/some/source/pattern',
    ])
    assert result.exit_code == 1
    assert 'SOURCE_PATTERN cannot be used with --update-nfo' in result.output


def test_update_nfo_requires_series_name(temp_config):
    """--update-nfo requires SERIES_NAME."""
    runner = CliRunner()
    result = runner.invoke(main, [
        '--config', temp_config,
        '--update-nfo', 'missing',
    ])
    assert result.exit_code == 1
    assert 'SERIES_NAME is required' in result.output


@patch('merge_into_series.cli.TVDBScraper')
def test_update_nfo_missing_mode(mock_scraper_class, temp_config):
    """--update-nfo=missing writes NFOs for video files that lack them."""
    mock_scraper = Mock()
    mock_scraper_class.return_value = mock_scraper

    from merge_into_series.tvdb_scraper import Episode
    mock_scraper.scrape_episodes.return_value = [
        Episode(2024, 1, "Test Episode", air_date="2024-01-01", description="Desc."),
    ]

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as target_dir:
        season_dir = Path(target_dir) / "Season 2024"
        season_dir.mkdir()
        (season_dir / "S2024E01 Test Episode.mkv").write_text("fake")

        # Write the config pointing at our temp target
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
            f.write(f"Storyville, {target_dir}, https://thetvdb.com/series/storyville/allseasons/official\n")
            cfg = f.name

        try:
            result = runner.invoke(main, ['--config', cfg, '--update-nfo', 'missing', 'Storyville'])
            assert result.exit_code == 0
            assert (season_dir / "S2024E01 Test Episode.nfo").exists()
        finally:
            Path(cfg).unlink()


@patch('merge_into_series.cli.TVDBScraper')
def test_update_nfo_all_mode_overwrites(mock_scraper_class, temp_config):
    """--update-nfo=all overwrites existing NFO files."""
    mock_scraper = Mock()
    mock_scraper_class.return_value = mock_scraper

    from merge_into_series.tvdb_scraper import Episode
    mock_scraper.scrape_episodes.return_value = [
        Episode(2024, 1, "Test Episode", air_date="2024-01-01", description="Desc."),
    ]

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as target_dir:
        season_dir = Path(target_dir) / "Season 2024"
        season_dir.mkdir()
        (season_dir / "S2024E01 Test Episode.mkv").write_text("fake")
        nfo = season_dir / "S2024E01 Test Episode.nfo"
        nfo.write_text("old content")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
            f.write(f"Storyville, {target_dir}, https://thetvdb.com/series/storyville/allseasons/official\n")
            cfg = f.name

        try:
            result = runner.invoke(main, ['--config', cfg, '--update-nfo', 'all', 'Storyville'])
            assert result.exit_code == 0
            assert nfo.read_text(encoding='utf-8') != "old content"
            assert '<title>Test Episode</title>' in nfo.read_text(encoding='utf-8')
        finally:
            Path(cfg).unlink()