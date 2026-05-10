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


def _resolve_series(config_handler, series_name: str, strict: bool, yes: bool):
    """Return series config for series_name, with optional fuzzy fallback.

    Returns None if no match is found or the user declines the suggestion.
    """
    series_config = config_handler.get_series_config(series_name)
    if series_config or strict:
        return series_config

    fuzzy_matches = config_handler.find_fuzzy_matches(series_name)

    if len(fuzzy_matches) == 1:
        match = fuzzy_matches[0]
        if yes:
            print(f'Matched: "{match["name"]}"')
            return match
        try:
            confirm = input(f'Did you mean "{match["name"]}"? [y/N] ').strip().lower()
        except KeyboardInterrupt:
            return None
        if confirm == 'y':
            return match

    elif 2 <= len(fuzzy_matches) <= 3:
        print("Did you mean one of these?")
        for i, m in enumerate(fuzzy_matches, 1):
            print(f"  {i}. {m['name']}")
        if yes:
            match = fuzzy_matches[0]
            print(f"Auto-selected: {match['name']}")
            return match
        while True:
            try:
                choice = input("Choice (or Enter to cancel): ").strip()
            except KeyboardInterrupt:
                return None
            if not choice:
                return None
            try:
                n = int(choice)
                if 1 <= n <= len(fuzzy_matches):
                    return fuzzy_matches[n - 1]
            except ValueError:
                pass
            print("Invalid choice.")

    return None


@click.command()
@click.argument('series_name', required=False)
@click.argument('source_pattern', nargs=-1, required=False)
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be done without actually doing it')
@click.option('--threshold', '-t', default=80, help='Fuzzy matching threshold (0-100)')
@click.option('--create-config', is_flag=True, help='Create example configuration file and exit')
@click.option('--overwrite', '-o', is_flag=True, help='Overwrite existing files without prompting')
@click.option('--yes', '-y', is_flag=True,
              help='Auto-confirm prompts: accept fuzzy series match, pick first episode match, move files.')
@click.option('--strict', is_flag=True,
              help='Disable fuzzy series name matching; require an exact name from the config.')
@click.option('--generate-nfo', default=True, show_default=True, type=bool,
              help='Generate .nfo metadata sidecar files alongside video files. '
                   'These let Plex find episode title, summary, and air date for series '
                   'with non-standard season numbers (e.g. year-based seasons). '
                   'Use --generate-nfo=false to disable.')
@click.option('--update-nfo', type=click.Choice(['missing', 'all']), default=None,
              help='Scan the target directory and generate .nfo files for already-merged episodes. '
                   '"missing" adds NFOs only where absent; "all" overwrites existing ones too. '
                   'Cannot be combined with SOURCE_PATTERN.')
def main(series_name: Optional[str] = None, source_pattern: tuple = (), config: Optional[str] = None,
         dry_run: bool = False, threshold: int = 80, create_config: bool = False, overwrite: bool = False,
         yes: bool = False, strict: bool = False,
         generate_nfo: bool = True, update_nfo: Optional[str] = None):
    """
    Merge downloaded TV episodes into organized series directories using TVDB metadata.

    SERIES_NAME: Name of the series to look up in configuration (or 'add')
    SOURCE_PATTERN: Path pattern to source files (file, directory, or glob)

    To add a series to the configuration:

        merge-into-series add NAME DIR_OR_PATH TVDB_URL
    """
    # Handle config creation
    if create_config:
        config_handler = Config(config)
        config_handler.create_example_config()
        return

    if series_name == 'add':
        if len(source_pattern) != 3:
            click.echo("Usage: merge-into-series add NAME DIR_OR_PATH TVDB_URL")
            sys.exit(1)
        name, path, url = source_pattern
        config_handler = Config(config)
        if config_handler.add_series(name, path, url):
            print(f'Added "{name}" to configuration.')
        else:
            print(f'"{name}" already exists in configuration.')
        return

    if update_nfo:
        # --- update-nfo mode ---
        if source_pattern:
            click.echo("Error: SOURCE_PATTERN cannot be used with --update-nfo")
            sys.exit(1)
        if not series_name:
            click.echo("Error: SERIES_NAME is required with --update-nfo")
            sys.exit(1)

        try:
            config_handler = Config(config)
            series_config = _resolve_series(config_handler, series_name, strict, yes)

            if not series_config:
                print(f"Error: Series '{series_name}' not found in configuration.")
                print(f"Available series: {', '.join(config_handler.list_series().keys())}")
                sys.exit(1)

            target_path = series_config['target_path']
            tvdb_url = series_config['tvdb_url']

            print(f"Updating NFO files for: {series_config['name']}")
            print(f"Target path: {target_path}")
            print("Fetching episode data from TVDB...")

            scraper = TVDBScraper()
            episodes = scraper.scrape_episodes(tvdb_url)

            if not episodes:
                print("Error: No episodes found. Please check the TVDB URL.")
                sys.exit(1)

            print(f"Found {len(episodes)} episodes in database")

            if dry_run:
                print("\n--- DRY RUN MODE ---")

            file_ops = FileOperations(dry_run=dry_run)
            file_ops.update_nfo_files(target_path, episodes, overwrite=(update_nfo == 'all'))

        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        return

    # --- normal merge mode ---
    if not series_name or not source_pattern:
        click.echo("Error: SERIES_NAME and SOURCE_PATTERN are required unless using --create-config or --update-nfo")
        sys.exit(1)

    try:
        # Load configuration
        config_handler = Config(config)
        series_config = _resolve_series(config_handler, series_name, strict, yes)

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

        # Find video files (collect and deduplicate across all source patterns)
        matcher = EpisodeMatcher(episodes)
        seen_paths = set()
        video_files = []
        for pattern in source_pattern:
            for vf in matcher.find_video_files(pattern):
                resolved = vf.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    video_files.append(vf)
        video_files = sorted(video_files)

        if not video_files:
            print(f"No video files found matching pattern: {source_pattern}")
            sys.exit(1)

        # Match files to episodes
        files_and_matches = {}
        for video_file in video_files:
            matches = matcher.match_episode(str(video_file), threshold)
            files_and_matches[str(video_file)] = matches

        # Interactive matching
        interface = InteractiveInterface(yes=yes)
        final_matches = interface.get_user_matches(files_and_matches, matcher)

        if not final_matches:
            print("No matches selected. Exiting.")
            sys.exit(0)

        # Confirm operations
        if not interface.confirm_operations(target_path, final_matches, matcher):
            print("Operations cancelled.")
            sys.exit(0)

        # Execute file operations
        file_ops = FileOperations(dry_run=dry_run, overwrite=overwrite, generate_nfo=generate_nfo)
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