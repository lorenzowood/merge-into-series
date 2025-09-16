"""Interactive user interface for episode matching and confirmation."""

from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .tvdb_scraper import Episode
from .matcher import EpisodeMatcher


class InteractiveInterface:
    """Handle user interaction for episode matching and confirmation."""

    def __init__(self):
        self.pending_operations = []

    def get_user_matches(self, files_and_matches: Dict[str, List[Tuple[Episode, int]]]) -> Dict[str, Optional[Episode]]:
        """Interactively get user confirmation for episode matches."""
        final_matches = {}

        print(f"Found {len(files_and_matches)} files")

        for filename, matches in files_and_matches.items():
            if len(matches) == 1:
                # Single match - show it but don't require confirmation
                episode, score = matches[0]
                print(f"{filename} -> {episode.season_episode_code} {episode.title}")
                final_matches[filename] = episode
            elif len(matches) > 1:
                # Multiple matches - let user choose
                print(f"{filename} ->")
                for i, (episode, score) in enumerate(matches[:7], 1):  # Show top 7 matches
                    print(f"{i}. {episode.season_episode_code} {episode.title}")
                print(f"{len(matches[:7]) + 1}. Manual entry")
                print(f"{len(matches[:7]) + 2}. Skip")

                while True:
                    try:
                        choice = input("Choice: ").strip()
                        if not choice:
                            continue

                        choice_num = int(choice)
                        if 1 <= choice_num <= len(matches[:7]):
                            selected_episode = matches[choice_num - 1][0]
                            final_matches[filename] = selected_episode
                            break
                        elif choice_num == len(matches[:7]) + 1:
                            # Manual entry
                            manual_episode = self._get_manual_episode_entry()
                            if manual_episode:
                                final_matches[filename] = manual_episode
                            else:
                                final_matches[filename] = None
                            break
                        elif choice_num == len(matches[:7]) + 2:
                            # Skip
                            final_matches[filename] = None
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except (ValueError, KeyboardInterrupt):
                        print("Invalid input. Please enter a number.")
                        continue
            else:
                # No matches found
                print(f"{filename} -> No matches found")
                print("1. Manual entry")
                print("2. Skip")

                while True:
                    try:
                        choice = input("Choice: ").strip()
                        if choice == "1":
                            manual_episode = self._get_manual_episode_entry()
                            if manual_episode:
                                final_matches[filename] = manual_episode
                            else:
                                final_matches[filename] = None
                            break
                        elif choice == "2":
                            final_matches[filename] = None
                            break
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
                    except KeyboardInterrupt:
                        print("\nOperation cancelled.")
                        return {}

        return final_matches

    def _get_manual_episode_entry(self) -> Optional[Episode]:
        """Get manual episode entry from user."""
        try:
            print("Manual entry:")
            season_str = input("Season (YYYY): ").strip()
            episode_str = input("Episode: ").strip()
            title = input("Title: ").strip()

            if not all([season_str, episode_str, title]):
                print("All fields are required for manual entry.")
                return None

            season = int(season_str)
            episode_num = int(episode_str)

            return Episode(season=season, episode=episode_num, title=title)

        except (ValueError, KeyboardInterrupt):
            print("Invalid input or operation cancelled.")
            return None

    def confirm_operations(self, target_path: str, final_matches: Dict[str, Optional[Episode]],
                          matcher: EpisodeMatcher) -> bool:
        """Show final operations and get user confirmation."""
        operations_to_process = {k: v for k, v in final_matches.items() if v is not None}

        if not operations_to_process:
            print("No files to process.")
            return False

        print("\nReady to process:")
        for filename, episode in operations_to_process.items():
            print(f"{Path(filename).name} -> {episode.season_episode_code} {episode.title}")

        print(f"\nProcess to target {target_path} by:")
        print("1. Moving")
        print("2. Copying")

        while True:
            try:
                choice = input("Choice: ").strip()
                if choice == "1":
                    operation_type = "move"
                    print("Warning: Moving files will remove them from the source location.")
                    confirm = input("Are you sure? (y/N): ").strip().lower()
                    if confirm != 'y':
                        print("Operation cancelled.")
                        return False
                    break
                elif choice == "2":
                    operation_type = "copy"
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return False

        # Store operations for processing
        self.pending_operations = []
        for filename, episode in operations_to_process.items():
            new_filename = matcher.get_filename_for_episode(episode, filename)
            season_dir = matcher.get_season_directory(episode)

            self.pending_operations.append({
                'source': filename,
                'target_dir': Path(target_path) / season_dir,
                'new_filename': new_filename,
                'episode': episode,
                'operation': operation_type
            })

        return True

    def get_pending_operations(self) -> List[Dict]:
        """Get the list of pending file operations."""
        return self.pending_operations