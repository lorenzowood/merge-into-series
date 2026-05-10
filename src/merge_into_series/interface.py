"""Interactive user interface for episode matching and confirmation."""

import readline
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .tvdb_scraper import Episode
from .matcher import EpisodeMatcher


def _input_prefilled(prompt: str, prefill: str = "") -> str:
    """Prompt for input with an editable pre-filled default value."""
    def hook():
        readline.insert_text(prefill)
        readline.redisplay()
    readline.set_pre_input_hook(hook)
    try:
        return input(prompt)
    finally:
        readline.set_pre_input_hook(None)


class InteractiveInterface:
    """Handle user interaction for episode matching and confirmation."""

    def __init__(self, yes: bool = False):
        self.pending_operations = []
        self.yes = yes

    def get_user_matches(self, files_and_matches: Dict[str, List[Tuple[Episode, int]]],
                         matcher: Optional['EpisodeMatcher'] = None) -> Dict[str, Optional[Episode]]:
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
                top = matches[:7]
                if self.yes:
                    episode = top[0][0]
                    print(f"{filename} -> {episode.season_episode_code} {episode.title}")
                    final_matches[filename] = episode
                else:
                    # Multiple matches - let user choose
                    print(f"{filename} ->")
                    for i, (episode, score) in enumerate(top, 1):
                        print(f"{i}. {episode.season_episode_code} {episode.title}")
                    print(f"{len(top) + 1}. Manual entry")
                    print(f"{len(top) + 2}. Skip")

                    while True:
                        try:
                            choice = input("Choice: ").strip()
                            if not choice:
                                continue

                            choice_num = int(choice)
                            if 1 <= choice_num <= len(top):
                                selected_episode = top[choice_num - 1][0]
                                final_matches[filename] = selected_episode
                                break
                            elif choice_num == len(top) + 1:
                                # Manual entry
                                manual_episode = self._get_manual_episode_entry(matcher)
                                if manual_episode:
                                    final_matches[filename] = manual_episode
                                else:
                                    final_matches[filename] = None
                                break
                            elif choice_num == len(top) + 2:
                                # Skip
                                final_matches[filename] = None
                                break
                            else:
                                print("Invalid choice. Please try again.")
                        except (ValueError, KeyboardInterrupt):
                            print("Invalid input. Please enter a number.")
                            continue
            else:
                # No confident matches found - try to find candidates
                candidates = []
                if matcher:
                    candidates = matcher.find_candidate_matches(filename, limit=5)

                if candidates:
                    if self.yes:
                        episode, score = candidates[0]
                        print(f"\n{Path(filename).name} -> {episode.season_episode_code} {episode.title} ({score}%)")
                        final_matches[filename] = episode
                    else:
                        print(f"\n{Path(filename).name} -> No exact match. Possible matches:")
                        for i, (episode, score) in enumerate(candidates, 1):
                            print(f"  {i}. {episode.season_episode_code} {episode.title} ({score}%)")
                        print(f"  {len(candidates) + 1}. Manual entry")
                        print(f"  {len(candidates) + 2}. Skip")

                        while True:
                            try:
                                choice = input("Choice: ").strip()
                                if not choice:
                                    continue

                                choice_num = int(choice)
                                if 1 <= choice_num <= len(candidates):
                                    selected_episode = candidates[choice_num - 1][0]
                                    final_matches[filename] = selected_episode
                                    break
                                elif choice_num == len(candidates) + 1:
                                    manual_episode = self._get_manual_episode_entry(matcher)
                                    if manual_episode:
                                        final_matches[filename] = manual_episode
                                    else:
                                        final_matches[filename] = None
                                    break
                                elif choice_num == len(candidates) + 2:
                                    final_matches[filename] = None
                                    break
                                else:
                                    print("Invalid choice. Please try again.")
                            except ValueError:
                                print("Invalid input. Please enter a number.")
                                continue
                            except KeyboardInterrupt:
                                print("\nOperation cancelled.")
                                return {}
                else:
                    if self.yes:
                        print(f"\n{Path(filename).name} -> No match found, skipping")
                        final_matches[filename] = None
                    else:
                        print(f"\n{Path(filename).name} -> No matches found")
                        print("  1. Manual entry")
                        print("  2. Skip")

                        while True:
                            try:
                                choice = input("Choice: ").strip()
                                if choice == "1":
                                    manual_episode = self._get_manual_episode_entry(matcher)
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

    def _get_manual_episode_entry(self, matcher: Optional['EpisodeMatcher'] = None) -> Optional[Episode]:
        """Get manual episode entry from user, pre-filling the title from metadata if known."""
        try:
            print("Manual entry:")
            season_str = input("Season (YYYY): ").strip()
            episode_str = input("Episode: ").strip()

            if not season_str or not episode_str:
                print("Season and episode are required.")
                return None

            season = int(season_str)
            episode_num = int(episode_str)

            # Look up the episode in metadata to pre-fill the title
            prefill = ""
            if matcher:
                known = next(
                    (ep for ep in matcher.episodes
                     if ep.season == season and ep.episode == episode_num),
                    None
                )
                if known:
                    prefill = known.title

            title = _input_prefilled("Title: ", prefill).strip()

            if not title:
                print("Title is required.")
                return None

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

        if self.yes:
            operation_type = "move"
            print("Choice: 1")
        else:
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