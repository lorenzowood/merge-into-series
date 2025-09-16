"""File operations for moving and copying episodes."""

import os
import shutil
from pathlib import Path
from typing import List, Dict


class FileOperations:
    """Handle file move and copy operations."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

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

        # Check if target already exists
        if target_path.exists():
            print(f"Warning: Target file already exists: {target_path}")
            overwrite = input("Overwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("Skipping file.")
                return True

        try:
            if self.dry_run:
                print(f"[DRY RUN] Would {op_type} {source_path} -> {target_path}")
                return True

            if op_type == 'move':
                print(f"Moving {source_path.name} -> {episode.season_episode_code} {episode.title}")
                shutil.move(str(source_path), str(target_path))
            elif op_type == 'copy':
                print(f"Copying {source_path.name} -> {episode.season_episode_code} {episode.title}")
                shutil.copy2(str(source_path), str(target_path))
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