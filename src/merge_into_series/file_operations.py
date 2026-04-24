"""File operations for moving and copying episodes."""

import os
import re
import shutil
import xml.sax.saxutils as saxutils
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.mpg', '.mpeg', '.m4v', '.wmv', '.ts'}
_EPISODE_CODE_RE = re.compile(r'^S(\d+)E(\d+)', re.IGNORECASE)


class FileOperations:
    """Handle file move and copy operations."""

    def __init__(self, dry_run: bool = False, overwrite: bool = False, generate_nfo: bool = True):
        self.dry_run = dry_run
        self.overwrite = overwrite
        self.generate_nfo = generate_nfo

    def _normalise_air_date(self, air_date: str) -> str:
        """Convert air date to ISO 8601 (YYYY-MM-DD). Returns input unchanged if unrecognised."""
        if not air_date:
            return air_date
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(air_date, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return air_date

    def _generate_nfo_content(self, episode) -> str:
        """Generate NFO XML content for an episode."""
        def esc(text: str) -> str:
            return saxutils.escape(text) if text else ''

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<episodedetails>',
            f'  <title>{esc(episode.title)}</title>',
            f'  <plot>{esc(episode.description)}</plot>',
            f'  <aired>{esc(self._normalise_air_date(episode.air_date))}</aired>',
            f'  <season>{episode.season}</season>',
            f'  <episode>{episode.episode}</episode>',
            '</episodedetails>',
        ]
        return '\n'.join(lines)

    def _write_nfo_file(self, target_video_path: Path, episode) -> None:
        """Write a .nfo sidecar file alongside the video file."""
        nfo_path = target_video_path.with_suffix('.nfo')
        try:
            nfo_path.write_text(self._generate_nfo_content(episode), encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not write NFO file {nfo_path}: {e}")

    def execute_operations(self, operations: List[Dict]) -> bool:
        """Execute a list of file operations."""
        success = True

        for op in operations:
            try:
                success &= self._execute_single_operation(op)
            except Exception as e:
                print(f"Error processing {op['source']}: {e}")
                success = False

        return success

    def _find_existing_episode_file(self, target_dir: Path, episode_code: str) -> Optional[Path]:
        """Find existing file with same SnnEnn designation."""
        pattern = f"{episode_code}*"
        matches = list(target_dir.glob(pattern))
        return matches[0] if matches else None

    def _files_are_identical(self, file1: Path, file2: Path) -> bool:
        """Compare files by size, then by content if sizes match."""
        if file1.stat().st_size != file2.stat().st_size:
            return False
        # Compare content in chunks
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                chunk1 = f1.read(8192)
                chunk2 = f2.read(8192)
                if chunk1 != chunk2:
                    return False
                if not chunk1:
                    return True

    def _get_unique_filename(self, target_dir: Path, base_name: str, extension: str) -> str:
        """Add (1), (2), etc. suffix if file exists."""
        candidate = f"{base_name}{extension}"
        counter = 1
        while (target_dir / candidate).exists():
            candidate = f"{base_name} ({counter}){extension}"
            counter += 1
        return candidate

    def _execute_single_operation(self, operation: Dict) -> bool:
        """Execute a single file operation."""
        source_path = Path(operation['source'])
        target_dir = Path(operation['target_dir'])
        new_filename = operation['new_filename']
        op_type = operation['operation']
        episode = operation['episode']

        if not source_path.exists():
            print(f"Error: Source file does not exist: {source_path}")
            return False

        # Create target directory if it doesn't exist
        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[DRY RUN] Would create directory: {target_dir}")

        target_path = target_dir / new_filename

        # Handle conflict detection (unless overwrite flag is set)
        if not self.overwrite:
            # Check for existing file with same episode code
            existing_file = self._find_existing_episode_file(target_dir, episode.season_episode_code)
            if existing_file:
                # Check if files are identical
                if self._files_are_identical(source_path, existing_file):
                    print(f"Skipping {source_path.name} (identical file already exists: {existing_file.name})")
                    return True
                else:
                    # Files are different - generate unique filename
                    base_name = Path(new_filename).stem
                    extension = Path(new_filename).suffix
                    new_filename = self._get_unique_filename(target_dir, base_name, extension)
                    target_path = target_dir / new_filename
                    print(f"Conflict detected: existing file differs. Using unique name: {new_filename}")

        try:
            if self.dry_run:
                print(f"[DRY RUN] Would {op_type} {source_path} -> {target_path}")
                if self.generate_nfo:
                    print(f"[DRY RUN] Would write NFO file: {target_path.with_suffix('.nfo')}")
                return True

            if op_type == 'move':
                print(f"Moving {source_path.name} -> {episode.season_episode_code} {episode.title}")
                shutil.move(str(source_path), str(target_path))
            elif op_type == 'copy':
                print(f"Copying {source_path.name} -> {episode.season_episode_code} {episode.title}")
                # Use shutil.copy instead of copy2 to avoid metadata issues on network filesystems
                shutil.copy(str(source_path), str(target_path))
            else:
                print(f"Error: Unknown operation type: {op_type}")
                return False

            if self.generate_nfo:
                self._write_nfo_file(target_path, episode)

            return True

        except Exception as e:
            print(f"Error during {op_type} operation: {e}")
            return False

    def update_nfo_files(self, target_path: str, episodes: List, overwrite: bool = False) -> bool:
        """Scan target directory and write NFO files for existing video files.

        If overwrite=False, skips video files that already have a .nfo sidecar.
        If overwrite=True, rewrites all NFO files.
        """
        target = Path(target_path)
        episode_lookup = {(ep.season, ep.episode): ep for ep in episodes}

        written = skipped = unmatched = 0

        for video_file in sorted(target.rglob('*')):
            if not video_file.is_file() or video_file.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            nfo_path = video_file.with_suffix('.nfo')

            if nfo_path.exists() and not overwrite:
                skipped += 1
                continue

            m = _EPISODE_CODE_RE.match(video_file.stem)
            if not m:
                print(f"Warning: Could not parse episode code from {video_file.name} — skipping")
                unmatched += 1
                continue

            season, episode_num = int(m.group(1)), int(m.group(2))
            episode = episode_lookup.get((season, episode_num))

            if not episode:
                print(f"Warning: No TVDB entry for S{season:04d}E{episode_num:02d} ({video_file.name}) — skipping")
                unmatched += 1
                continue

            if self.dry_run:
                action = "overwrite" if nfo_path.exists() else "write"
                print(f"[DRY RUN] Would {action} NFO: {nfo_path}")
            else:
                action = "Overwrote" if nfo_path.exists() else "Wrote"
                self._write_nfo_file(video_file, episode)
                print(f"{action} NFO: {nfo_path.name}")

            written += 1

        print(f"NFO update: {written} written, {skipped} already present (skipped), {unmatched} unmatched")
        return True

    def check_target_writable(self, target_path: str) -> bool:
        """Check if the target directory is writable."""
        target = Path(target_path)

        # If target doesn't exist, check parent
        check_path = target if target.exists() else target.parent

        if not check_path.exists():
            print(f"Error: Target path does not exist and cannot be created: {target}")
            return False

        return os.access(check_path, os.W_OK)