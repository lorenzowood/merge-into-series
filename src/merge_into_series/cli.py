"""Command-line interface for merge-into-series."""

import sys
from pathlib import Path
from typing import Optional

import click

from .config import Config
from .tvdb_scraper import TVDBScraper
from .matcher import EpisodeMatcher
from .interface import InteractiveInterface
from .file_operations import FileOperations


@click.command()
@click.argument('series_name', required=False)
@click.argument('source_pattern', required=False)
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be done without actually doing it')
@click.option('--threshold', '-t', default=80, help='Fuzzy matching threshold (0-100)')
@click.option('--create-config', is_flag=True, help='Create example configuration file and exit')
def main(series_name: Optional[str] = None, source_pattern: Optional[str] = None, config: Optional[str] = None,
         dry_run: bool = False, threshold: int = 80, create_config: bool = False):
    """
    Merge downloaded TV episodes into organized series directories using TVDB metadata.

    SERIES_NAME: Name of the series to look up in configuration
    SOURCE_PATTERN: Path pattern to source files (file, directory, or glob)
    """
    # Handle config creation
    if create_config:
        config_handler = Config(config)
        config_handler.create_example_config()
        return

    # Validate required arguments if not creating config
    if not series_name or not source_pattern:
        click.echo("Error: SERIES_NAME and SOURCE_PATTERN are required unless using --create-config")
        sys.exit(1)

    try:
        # Load configuration
        config_handler = Config(config)
        series_config = config_handler.get_series_config(series_name)

        if not series_config:
            print(f"Error: Series '{series_name}' not found in configuration.")
            print(f"Available series: {', '.join(config_handler.list_series().keys())}")
            print(f"Use --create-config to create an example configuration file.")
            sys.exit(1)

        target_path = series_config['target_path']
        tvdb_url = series_config['tvdb_url']

        print(f"Processing series: {series_config['name']}")
        print(f"Target path: {target_path}")
        print(f"TVDB URL: {tvdb_url}")

        # Scrape episode data from TVDB
        print("Fetching episode data from TVDB...")
        scraper = TVDBScraper()
        episodes = scraper.scrape_episodes(tvdb_url)

        if not episodes:
            print("Error: No episodes found. Please check the TVDB URL.")
            sys.exit(1)

        print(f"Found {len(episodes)} episodes in database")

        # Find video files
        matcher = EpisodeMatcher(episodes)
        video_files = matcher.find_video_files(source_pattern)

        if not video_files:
            print(f"No video files found matching pattern: {source_pattern}")
            sys.exit(1)

        # Match files to episodes
        files_and_matches = {}
        for video_file in video_files:
            matches = matcher.match_episode(str(video_file), threshold)
            files_and_matches[str(video_file)] = matches

        # Interactive matching
        interface = InteractiveInterface()
        final_matches = interface.get_user_matches(files_and_matches)

        if not final_matches:
            print("No matches selected. Exiting.")
            sys.exit(0)

        # Confirm operations
        if not interface.confirm_operations(target_path, final_matches, matcher):
            print("Operations cancelled.")
            sys.exit(0)

        # Execute file operations
        file_ops = FileOperations(dry_run=dry_run)
        operations = interface.get_pending_operations()

        if dry_run:
            print("\n--- DRY RUN MODE ---")

        success = file_ops.execute_operations(operations)

        if success:
            if dry_run:
                print("\nDry run completed successfully.")
            else:
                print("\nAll operations completed successfully!")
        else:
            print("\nSome operations failed. Please check the output above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()