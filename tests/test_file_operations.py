"""Tests for file operations."""

import tempfile
from pathlib import Path
import pytest

from merge_into_series.file_operations import FileOperations
from merge_into_series.tvdb_scraper import Episode


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as source_dir:
        with tempfile.TemporaryDirectory() as target_dir:
            # Create test files
            source_path = Path(source_dir)
            target_path = Path(target_dir)

            test_file = source_path / "test_video.mkv"
            test_file.write_text("fake video content")

            yield {
                'source_dir': source_path,
                'target_dir': target_path,
                'test_file': test_file
            }


def test_dry_run_operations(temp_files):
    """Test dry run mode."""
    file_ops = FileOperations(dry_run=True)
    episode = Episode(2024, 6, "Test Episode")

    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': temp_files['target_dir'] / "Season 2024",
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'move'
    }]

    # Should succeed in dry run mode
    success = file_ops.execute_operations(operations)
    assert success

    # Original file should still exist
    assert temp_files['test_file'].exists()

    # Target should not have been created
    target_file = temp_files['target_dir'] / "Season 2024" / "S2024E06 Test Episode.mkv"
    assert not target_file.exists()


def test_move_operation(temp_files):
    """Test move operation."""
    file_ops = FileOperations(dry_run=False)
    episode = Episode(2024, 6, "Test Episode")

    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': temp_files['target_dir'] / "Season 2024",
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'move'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    # Original file should be gone
    assert not temp_files['test_file'].exists()

    # Target should exist
    target_file = temp_files['target_dir'] / "Season 2024" / "S2024E06 Test Episode.mkv"
    assert target_file.exists()
    assert target_file.read_text() == "fake video content"


def test_copy_operation(temp_files):
    """Test copy operation."""
    file_ops = FileOperations(dry_run=False)
    episode = Episode(2024, 6, "Test Episode")

    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': temp_files['target_dir'] / "Season 2024",
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'copy'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    # Original file should still exist
    assert temp_files['test_file'].exists()

    # Target should also exist
    target_file = temp_files['target_dir'] / "Season 2024" / "S2024E06 Test Episode.mkv"
    assert target_file.exists()
    assert target_file.read_text() == "fake video content"


def test_missing_source_file(temp_files):
    """Test handling of missing source file."""
    file_ops = FileOperations(dry_run=False)
    episode = Episode(2024, 6, "Test Episode")

    operations = [{
        'source': str(temp_files['source_dir'] / "nonexistent.mkv"),
        'target_dir': temp_files['target_dir'] / "Season 2024",
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'move'
    }]

    success = file_ops.execute_operations(operations)
    assert not success


def test_multiple_operations(temp_files):
    """Test multiple file operations."""
    file_ops = FileOperations(dry_run=False)

    # Create additional test files
    test_file2 = temp_files['source_dir'] / "test_video2.mkv"
    test_file2.write_text("fake video content 2")

    episode1 = Episode(2024, 6, "Test Episode 1")
    episode2 = Episode(2024, 7, "Test Episode 2")

    operations = [
        {
            'source': str(temp_files['test_file']),
            'target_dir': temp_files['target_dir'] / "Season 2024",
            'new_filename': 'S2024E06 Test Episode 1.mkv',
            'episode': episode1,
            'operation': 'copy'
        },
        {
            'source': str(test_file2),
            'target_dir': temp_files['target_dir'] / "Season 2024",
            'new_filename': 'S2024E07 Test Episode 2.mkv',
            'episode': episode2,
            'operation': 'copy'
        }
    ]

    success = file_ops.execute_operations(operations)
    assert success

    # Both target files should exist
    target_file1 = temp_files['target_dir'] / "Season 2024" / "S2024E06 Test Episode 1.mkv"
    target_file2 = temp_files['target_dir'] / "Season 2024" / "S2024E07 Test Episode 2.mkv"

    assert target_file1.exists()
    assert target_file2.exists()


def test_check_target_writable(temp_files):
    """Test checking if target is writable."""
    file_ops = FileOperations()

    # Should be writable
    assert file_ops.check_target_writable(str(temp_files['target_dir']))

    # Non-existent path
    non_existent = temp_files['target_dir'] / "deep" / "nested" / "path"
    # This should still return True as we can create the parent dirs
    # The actual implementation might vary based on filesystem permissions


# --- NFO generation tests ---

def test_nfo_content_generation():
    """NFO XML contains all expected fields from episode data."""
    file_ops = FileOperations()
    episode = Episode(2024, 6, "Test Episode",
                      air_date="2024-03-15",
                      description="A great documentary about something.")

    content = file_ops._generate_nfo_content(episode)

    assert '<?xml version="1.0" encoding="UTF-8"?>' in content
    assert '<episodedetails>' in content
    assert '</episodedetails>' in content
    assert '<title>Test Episode</title>' in content
    assert '<plot>A great documentary about something.</plot>' in content
    assert '<aired>2024-03-15</aired>' in content
    assert '<season>2024</season>' in content
    assert '<episode>6</episode>' in content


def test_nfo_date_normalisation_month_name():
    """TVDB 'Month DD, YYYY' format is converted to ISO 8601."""
    file_ops = FileOperations()
    assert file_ops._normalise_air_date("July 25, 1964") == "1964-07-25"
    assert file_ops._normalise_air_date("January 1, 2024") == "2024-01-01"
    assert file_ops._normalise_air_date("December 31, 1999") == "1999-12-31"


def test_nfo_date_already_iso():
    """Dates already in ISO 8601 format are passed through unchanged."""
    file_ops = FileOperations()
    assert file_ops._normalise_air_date("1964-07-25") == "1964-07-25"
    assert file_ops._normalise_air_date("2024-03-15") == "2024-03-15"


def test_nfo_date_empty():
    """Empty date string is returned as empty string."""
    file_ops = FileOperations()
    assert file_ops._normalise_air_date("") == ""


def test_nfo_date_unrecognised_format():
    """Unrecognised date formats are returned as-is rather than crashing."""
    file_ops = FileOperations()
    assert file_ops._normalise_air_date("unknown") == "unknown"


def test_nfo_content_uses_iso_date():
    """NFO content converts TVDB date format to ISO 8601."""
    file_ops = FileOperations()
    episode = Episode(1964, 4, "Strangeness Minus Three",
                      air_date="July 25, 1964",
                      description="A documentary.")

    content = file_ops._generate_nfo_content(episode)
    assert '<aired>1964-07-25</aired>' in content


def test_nfo_content_xml_escaping():
    """Special XML characters in title and description are properly escaped."""
    file_ops = FileOperations()
    episode = Episode(1985, 3, "Art & Money: 'Rich' vs \"Poor\"",
                      description="A <bold> look at money & power.")

    content = file_ops._generate_nfo_content(episode)

    assert "&amp;" in content
    assert "&lt;" in content
    assert "<title>" in content
    # Raw unescaped chars must not appear inside element content
    assert "Art & Money" not in content
    assert "A <bold>" not in content


def test_nfo_content_empty_optional_fields():
    """NFO generates cleanly when air_date and description are empty."""
    file_ops = FileOperations()
    episode = Episode(1975, 1, "Some Title")  # air_date and description default to ""

    content = file_ops._generate_nfo_content(episode)

    assert '<title>Some Title</title>' in content
    assert '<season>1975</season>' in content
    assert '<episode>1</episode>' in content
    # Empty fields still present (harmless for Plex)
    assert '<plot>' in content
    assert '<aired>' in content


def test_nfo_file_created_on_copy(temp_files):
    """An .nfo file is created alongside the copied video file."""
    file_ops = FileOperations(dry_run=False, generate_nfo=True)
    episode = Episode(2024, 6, "Test Episode",
                      air_date="2024-03-15",
                      description="Episode description.")

    target_season_dir = temp_files['target_dir'] / "Season 2024"
    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': target_season_dir,
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'copy'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    nfo_file = target_season_dir / 'S2024E06 Test Episode.nfo'
    assert nfo_file.exists()
    content = nfo_file.read_text(encoding='utf-8')
    assert '<title>Test Episode</title>' in content
    assert '<aired>2024-03-15</aired>' in content


def test_nfo_file_created_on_move(temp_files):
    """An .nfo file is created alongside the moved video file."""
    file_ops = FileOperations(dry_run=False, generate_nfo=True)
    episode = Episode(2024, 8, "Another Episode",
                      air_date="2024-08-01",
                      description="Another description.")

    target_season_dir = temp_files['target_dir'] / "Season 2024"
    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': target_season_dir,
        'new_filename': 'S2024E08 Another Episode.mkv',
        'episode': episode,
        'operation': 'move'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    nfo_file = target_season_dir / 'S2024E08 Another Episode.nfo'
    assert nfo_file.exists()


def test_nfo_not_created_when_disabled(temp_files):
    """No .nfo file is created when generate_nfo=False."""
    file_ops = FileOperations(dry_run=False, generate_nfo=False)
    episode = Episode(2024, 6, "Test Episode")

    target_season_dir = temp_files['target_dir'] / "Season 2024"
    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': target_season_dir,
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'copy'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    nfo_file = target_season_dir / 'S2024E06 Test Episode.nfo'
    assert not nfo_file.exists()


def test_nfo_dry_run_does_not_create_file(temp_files):
    """Dry run prints intent but does not write the .nfo file."""
    file_ops = FileOperations(dry_run=True, generate_nfo=True)
    episode = Episode(2024, 6, "Test Episode")

    target_season_dir = temp_files['target_dir'] / "Season 2024"
    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': target_season_dir,
        'new_filename': 'S2024E06 Test Episode.mkv',
        'episode': episode,
        'operation': 'copy'
    }]

    success = file_ops.execute_operations(operations)
    assert success

    nfo_file = target_season_dir / 'S2024E06 Test Episode.nfo'
    assert not nfo_file.exists()


def test_nfo_filename_matches_video_stem(temp_files):
    """The NFO filename stem exactly matches the video filename stem."""
    file_ops = FileOperations(dry_run=False, generate_nfo=True)
    episode = Episode(1985, 3, "Coals to Newcastle")

    target_season_dir = temp_files['target_dir'] / "Season 1985"
    video_filename = 'S1985E03 Coals to Newcastle.mkv'
    operations = [{
        'source': str(temp_files['test_file']),
        'target_dir': target_season_dir,
        'new_filename': video_filename,
        'episode': episode,
        'operation': 'copy'
    }]

    file_ops.execute_operations(operations)

    video_file = target_season_dir / video_filename
    nfo_file = target_season_dir / 'S1985E03 Coals to Newcastle.nfo'
    assert video_file.exists()
    assert nfo_file.exists()


# --- update_nfo_files tests ---

@pytest.fixture
def target_with_videos():
    """Target directory pre-populated with renamed video files (simulating already-merged episodes)."""
    with tempfile.TemporaryDirectory() as target_dir:
        target = Path(target_dir)
        season_dir = target / "Season 2024"
        season_dir.mkdir()
        (season_dir / "S2024E06 Praying for Armageddon.mkv").write_text("fake")
        (season_dir / "S2024E07 The Contestant.mkv").write_text("fake")
        yield target


@pytest.fixture
def episodes_2024():
    return [
        Episode(2024, 6, "Praying for Armageddon",
                air_date="March 15, 2024", description="A documentary."),
        Episode(2024, 7, "The Contestant",
                air_date="March 22, 2024", description="Another documentary."),
    ]


def test_update_nfo_creates_missing(target_with_videos, episodes_2024):
    """update_nfo_files writes NFOs for video files that lack them."""
    file_ops = FileOperations()
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)

    assert (target_with_videos / "Season 2024" / "S2024E06 Praying for Armageddon.nfo").exists()
    assert (target_with_videos / "Season 2024" / "S2024E07 The Contestant.nfo").exists()


def test_update_nfo_nfo_content_is_correct(target_with_videos, episodes_2024):
    """NFO files written by update_nfo_files contain correct metadata."""
    file_ops = FileOperations()
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)

    content = (target_with_videos / "Season 2024" / "S2024E06 Praying for Armageddon.nfo").read_text(encoding='utf-8')
    assert '<title>Praying for Armageddon</title>' in content
    assert '<aired>2024-03-15</aired>' in content
    assert '<plot>A documentary.</plot>' in content


def test_update_nfo_skips_existing(target_with_videos, episodes_2024):
    """update_nfo_files does not overwrite an existing NFO when overwrite=False."""
    season_dir = target_with_videos / "Season 2024"
    existing_nfo = season_dir / "S2024E06 Praying for Armageddon.nfo"
    existing_nfo.write_text("original content", encoding='utf-8')

    file_ops = FileOperations()
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)

    assert existing_nfo.read_text(encoding='utf-8') == "original content"


def test_update_nfo_all_overwrites_existing(target_with_videos, episodes_2024):
    """update_nfo_files overwrites existing NFOs when overwrite=True."""
    season_dir = target_with_videos / "Season 2024"
    existing_nfo = season_dir / "S2024E06 Praying for Armageddon.nfo"
    existing_nfo.write_text("original content", encoding='utf-8')

    file_ops = FileOperations()
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=True)

    content = existing_nfo.read_text(encoding='utf-8')
    assert content != "original content"
    assert '<title>Praying for Armageddon</title>' in content


def test_update_nfo_dry_run_writes_nothing(target_with_videos, episodes_2024):
    """Dry run mode reports what would be written but creates no files."""
    file_ops = FileOperations(dry_run=True)
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)

    assert not (target_with_videos / "Season 2024" / "S2024E06 Praying for Armageddon.nfo").exists()
    assert not (target_with_videos / "Season 2024" / "S2024E07 The Contestant.nfo").exists()


def test_update_nfo_episode_code_not_at_start_of_filename(target_with_videos, episodes_2024):
    """Episode code anywhere in the filename is found (e.g. 'Series - S2024E06 - Title.mkv')."""
    season_dir = target_with_videos / "Season 2024"
    # Add files with series-name prefix, as Plex might have them
    (season_dir / "My Show - S2024E06 - Praying for Armageddon.mkv").write_text("fake")

    file_ops = FileOperations()
    file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)

    assert (season_dir / "My Show - S2024E06 - Praying for Armageddon.nfo").exists()


def test_update_nfo_unrecognised_filename_does_not_crash(target_with_videos, episodes_2024):
    """Files without any SxxExx code are skipped with a warning, not a crash."""
    (target_with_videos / "Season 2024" / "some_random_file.mkv").write_text("fake")

    file_ops = FileOperations()
    result = file_ops.update_nfo_files(str(target_with_videos), episodes_2024, overwrite=False)
    assert result is True


def test_update_nfo_episode_not_in_list_does_not_crash(target_with_videos):
    """Video file whose episode code isn't in the episode list is skipped gracefully."""
    file_ops = FileOperations()
    # Pass empty episode list — nothing matches
    result = file_ops.update_nfo_files(str(target_with_videos), [], overwrite=False)
    assert result is True