"""File operations for moving and copying episodes."""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional


class FileOperations:
    """Handle file move and copy operations."""

    def __init__(self, dry_run: bool = False, overwrite: bool = False):
        self.dry_run = dry_run
        self.overwrite = overwrite

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

            return True

        except Exception as e:
            print(f"Error during {op_type} operation: {e}")
            return False

    def check_target_writable(self, target_path: str) -> bool:
        """Check if the target directory is writable."""
        target = Path(target_path)

        # If target doesn't exist, check parent
        check_path = target if target.exists() else target.parent

        if not check_path.exists():
            print(f"Error: Target path does not exist and cannot be created: {target}")
            return False

        return os.access(check_path, os.W_OK)