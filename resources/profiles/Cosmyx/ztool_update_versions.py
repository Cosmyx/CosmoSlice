#!/usr/bin/env python3
"""
Script to update version numbers in all Cosmyx JSON files.
Updates version field to format: DD.MM.YYYY.ITERATION
where ITERATION is auto-incremented starting from 1.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple


# ==================== CONFIGURATION ====================

BASE_DIR = Path(__file__).parent


# ==================== DATA STRUCTURES ====================

@dataclass
class UpdateResult:
    """Result tracking for the update process"""
    total_files_scanned: int = 0
    total_files_updated: int = 0
    files_updated: List[Path] = field(default_factory=list)
    files_skipped: List[Tuple[Path, str]] = field(default_factory=list)
    errors: List[Tuple[Path, str]] = field(default_factory=list)


# ==================== UTILITY FUNCTIONS ====================

def get_current_version_string(iteration: int) -> str:
    """
    Generate version string in format DD.MM.YYYY.ITERATION

    Args:
        iteration: Current iteration number

    Returns:
        Version string (e.g., "17.12.2025.01")
    """
    now = datetime.now()
    day = now.strftime("%d")
    month = now.strftime("%m")
    year = now.strftime("%Y")

    return f"{day}.{month}.{year}.{iteration:02d}"


def parse_version_iteration(version_string: str) -> int:
    """
    Parse iteration number from version string matching DD.MM.YYYY.XX pattern.

    Args:
        version_string: Version string to parse

    Returns:
        Iteration number if pattern matches, 0 otherwise
    """
    import re
    # Match pattern: DD.MM.YYYY.XX (where XX is 1-2 digits)
    pattern = r'^\d{2}\.\d{2}\.\d{4}\.(\d{1,2})$'
    match = re.match(pattern, str(version_string))

    if match:
        return int(match.group(1))
    return 0


def find_highest_iteration(base_path: Path) -> int:
    """
    Scan all JSON files and find the highest iteration number used.

    Args:
        base_path: Root directory to scan

    Returns:
        Highest iteration number found, or 0 if none found
    """
    max_iteration = 0

    for json_file in base_path.rglob('*.json'):
        # Skip tool scripts
        if json_file.name.startswith('ztool_'):
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'version' in data:
                iteration = parse_version_iteration(data['version'])
                max_iteration = max(max_iteration, iteration)

        except:
            # Skip files that can't be read or parsed
            pass

    return max_iteration


def scan_all_json_files(base_path: Path) -> List[Path]:
    """
    Recursively scan for all JSON files in the directory tree.

    Args:
        base_path: Root directory to scan

    Returns:
        List of Path objects for all JSON files found
    """
    json_files = []

    # Recursively find all .json files
    for json_file in base_path.rglob('*.json'):
        # Skip the tool scripts themselves (though they aren't JSON)
        if json_file.name.startswith('ztool_'):
            continue
        json_files.append(json_file)

    return sorted(json_files)


def update_version_in_file(file_path: Path, new_version: str) -> Tuple[bool, str]:
    """
    Update the version field in a JSON file.

    Args:
        file_path: Path to JSON file
        new_version: New version string to set

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if version field exists
        if 'version' not in data:
            return False, "No version field found"

        old_version = data.get('version', 'N/A')

        # Skip if already up to date
        if old_version == new_version:
            return False, f"Already up to date ({new_version})"

        # Update version
        data['version'] = new_version

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return True, f"Updated from {old_version} to {new_version}"

    except json.JSONDecodeError as e:
        return False, f"JSON parse error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


# ==================== MAIN LOGIC ====================

def update_all_versions(iteration: int = None, dry_run: bool = False) -> UpdateResult:
    """
    Main function to update all version numbers.

    Args:
        iteration: Iteration number (if None, auto-increments from highest found)
        dry_run: If True, only simulate changes without writing

    Returns:
        UpdateResult with statistics
    """
    results = UpdateResult()

    print("=" * 70)
    print("Version Update Tool")
    print("=" * 70)

    # Auto-detect iteration if not specified
    if iteration is None:
        print("\nScanning for highest existing iteration...")
        highest = find_highest_iteration(BASE_DIR)
        iteration = highest + 1
        print(f"Found highest iteration: {highest}")
        print(f"Using next iteration: {iteration}")
    else:
        print(f"\nUsing manually specified iteration: {iteration}")

    # Generate new version string
    new_version = get_current_version_string(iteration)
    print(f"New version: {new_version}")

    if dry_run:
        print("DRY RUN MODE - No files will be modified")

    # Scan for all JSON files
    print(f"\nScanning directory: {BASE_DIR}")
    json_files = scan_all_json_files(BASE_DIR)
    results.total_files_scanned = len(json_files)
    print(f"Found {len(json_files)} JSON files")

    if not json_files:
        print("No JSON files found!")
        return results

    # Update each file
    print("\nUpdating files...")

    for json_file in json_files:
        # Get relative path for display
        try:
            rel_path = json_file.relative_to(BASE_DIR)
        except ValueError:
            rel_path = json_file

        if dry_run:
            # Dry run: just check what would be updated
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'version' in data:
                    old_version = data.get('version', 'N/A')
                    if old_version != new_version:
                        print(f"  [WOULD UPDATE] {rel_path}")
                        print(f"                 {old_version} -> {new_version}")
                        results.files_updated.append(json_file)
                        results.total_files_updated += 1
                    else:
                        results.files_skipped.append((json_file, "Already up to date"))
                else:
                    results.files_skipped.append((json_file, "No version field"))
            except Exception as e:
                results.errors.append((json_file, str(e)))
        else:
            # Real update
            success, message = update_version_in_file(json_file, new_version)

            if success:
                print(f"  + Updated: {rel_path}")
                print(f"             {message}")
                results.files_updated.append(json_file)
                results.total_files_updated += 1
            else:
                results.files_skipped.append((json_file, message))

    return results


def print_report(results: UpdateResult, dry_run: bool = False):
    """Print a summary report of the update process"""
    print("\n" + "=" * 70)
    if dry_run:
        print("DRY RUN COMPLETE")
    else:
        print("UPDATE COMPLETE")
    print("=" * 70)
    print(f"Files scanned: {results.total_files_scanned}")
    print(f"Files updated: {results.total_files_updated}")
    print(f"Files skipped: {len(results.files_skipped)}")
    print(f"Errors: {len(results.errors)}")

    if results.errors:
        print("\nErrors encountered:")
        for file_path, error in results.errors[:10]:  # Show first 10 errors
            try:
                rel_path = file_path.relative_to(BASE_DIR)
            except:
                rel_path = file_path
            print(f"  - {rel_path}: {error}")
        if len(results.errors) > 10:
            print(f"  ... and {len(results.errors) - 10} more errors")

    print("=" * 70)


# ==================== MAIN ENTRY POINT ====================

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Update version numbers in all Cosmyx JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ztool_update_versions.py              # Update with iteration 1
  python ztool_update_versions.py -i 2         # Update with iteration 2
  python ztool_update_versions.py --dry-run    # Preview changes without applying
  python ztool_update_versions.py -i 5 --dry-run  # Preview with iteration 5
        """
    )

    parser.add_argument(
        '-i', '--iteration',
        type=int,
        default=None,
        help='Iteration number (default: auto-increment from highest found)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )

    args = parser.parse_args()

    # Validate iteration if specified
    if args.iteration is not None and args.iteration < 1:
        print("Error: Iteration must be >= 1")
        return 1

    try:
        results = update_all_versions(
            iteration=args.iteration,
            dry_run=args.dry_run
        )
        print_report(results, dry_run=args.dry_run)

        if not args.dry_run and results.total_files_updated > 0:
            print(f"\nSuccessfully updated {results.total_files_updated} files!")

        return 0

    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
