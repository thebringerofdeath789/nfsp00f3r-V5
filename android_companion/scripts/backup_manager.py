#!/usr/bin/env python3
"""
Backup Manager for nfsp00f3r-V5
Auto-backup before destructive operations and workspace restoration.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List

class BackupManager:
    """Workspace backup and restoration manager."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.backup_dir = self.workspace_root / ".backups"
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, backup_name: str = None) -> str:
        """Create a complete workspace backup."""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"nf_sp00f_backup_{timestamp}"

        backup_path = self.backup_dir / f"{backup_name}.zip"

        print(f"📦 Creating backup: {backup_name}")

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Backup Android app
            android_app_path = self.workspace_root / "android-app"
            if android_app_path.exists():
                for file_path in android_app_path.rglob("*"):
                    if file_path.is_file() and not self._should_exclude(file_path):
                        arc_name = file_path.relative_to(self.workspace_root)
                        backup_zip.write(file_path, arc_name)

            # Backup project files
            project_files = [
                "README.md", "project_manifest.yaml", "CHANGELOG.md",
                ".vscode/tasks.json", "docs/mem/project_memory.json"
            ]

            for project_file in project_files:
                file_path = self.workspace_root / project_file
                if file_path.exists():
                    backup_zip.write(file_path, project_file)

        # Create backup metadata
        metadata = {
            "backup_name": backup_name,
            "created": datetime.now().isoformat(),
            "workspace_root": str(self.workspace_root),
            "backup_size": backup_path.stat().st_size,
            "files_included": self._count_files_in_backup(backup_path)
        }

        metadata_path = self.backup_dir / f"{backup_name}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Backup created: {backup_path.name}")
        print(f"📊 Size: {backup_path.stat().st_size / 1024 / 1024:.1f} MB")

        return str(backup_path)

    def restore_backup(self, backup_name: str, confirm: bool = False) -> bool:
        """Restore workspace from backup."""
        backup_path = self.backup_dir / f"{backup_name}.zip"

        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_name}")
            return False

        if not confirm:
            print(f"⚠️  This will overwrite current workspace with backup: {backup_name}")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Restore cancelled")
                return False

        print(f"🔄 Restoring backup: {backup_name}")

        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                backup_zip.extractall(self.workspace_root)

            print(f"✅ Backup restored successfully")
            return True

        except Exception as e:
            print(f"❌ Restore failed: {str(e)}")
            return False

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []

        for backup_file in self.backup_dir.glob("*.zip"):
            backup_name = backup_file.stem
            metadata_file = self.backup_dir / f"{backup_name}.json"

            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except Exception:
                    # Fallback metadata
                    backups.append({
                        "backup_name": backup_name,
                        "created": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                        "backup_size": backup_file.stat().st_size,
                        "files_included": "unknown"
                    })

        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Remove old backups, keeping only the most recent."""
        backups = self.list_backups()

        if len(backups) <= keep_count:
            print(f"📦 {len(backups)} backups found, no cleanup needed")
            return 0

        backups_to_remove = backups[keep_count:]
        removed_count = 0

        for backup in backups_to_remove:
            backup_name = backup['backup_name']

            # Remove zip file
            backup_zip = self.backup_dir / f"{backup_name}.zip"
            if backup_zip.exists():
                backup_zip.unlink()

            # Remove metadata
            backup_meta = self.backup_dir / f"{backup_name}.json"
            if backup_meta.exists():
                backup_meta.unlink()

            removed_count += 1
            print(f"🗑️  Removed old backup: {backup_name}")

        print(f"✅ Cleanup complete: {removed_count} old backups removed")
        return removed_count

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from backup."""
        exclude_patterns = [
            'build/', '.gradle/', 'bin/', '.git/',
            '.idea/', '*.tmp', '*.log', '.DS_Store'
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in exclude_patterns)

    def _count_files_in_backup(self, backup_path: Path) -> int:
        """Count files in backup zip."""
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                return len(backup_zip.infolist())
        except Exception:
            return 0

    def print_backup_list(self):
        """Print formatted backup list."""
        backups = self.list_backups()

        if not backups:
            print("📦 No backups found")
            return

        print("\n📦 Available Backups:")
        print("=" * 60)

        for backup in backups:
            size_mb = backup['backup_size'] / 1024 / 1024
            created = datetime.fromisoformat(backup['created']).strftime("%Y-%m-%d %H:%M")

            print(f"📁 {backup['backup_name']}")
            print(f"   📅 Created: {created}")
            print(f"   📊 Size: {size_mb:.1f} MB")
            print(f"   📄 Files: {backup['files_included']}")
            print()

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python backup_manager.py <command> [args]")
        print("Commands: create, restore, list, cleanup")
        sys.exit(1)

    command = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    manager = BackupManager(workspace_root)

    if command == "create":
        backup_name = sys.argv[3] if len(sys.argv) > 3 else None
        manager.create_backup(backup_name)

    elif command == "restore":
        if len(sys.argv) < 4:
            print("Usage: python backup_manager.py restore <workspace_root> <backup_name>")
            sys.exit(1)
        backup_name = sys.argv[3]
        manager.restore_backup(backup_name)

    elif command == "list":
        manager.print_backup_list()

    elif command == "cleanup":
        keep_count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        manager.cleanup_old_backups(keep_count)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
