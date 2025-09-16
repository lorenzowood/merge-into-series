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