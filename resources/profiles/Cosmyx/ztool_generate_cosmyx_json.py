#!/usr/bin/env python3
"""
Script to generate cosmyx.json by scanning all JSON files in the directory structure.
This script:
1. Scans all folders and subfolders
2. Reads every JSON file found
3. Extracts: relative path, name, and type
4. Generates cosmyx.json with proper structure
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

# Base directory for scanning (current directory)
BASE_DIR = Path(__file__).parent

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    'machine_old',
    '__pycache__',
    '.git',
    'node_modules',
    '.vscode'
}

# File to exclude
EXCLUDE_FILES = {
    'cosmyx.json',
    'Cosmyx.json',
    'generate_cosmyx_json.py'
}


def scan_json_files(base_dir: Path) -> List[Dict]:
    """
    Scan all directories for JSON files and extract metadata.

    Returns:
        List of dictionaries containing file metadata
    """
    json_files = []

    for root, dirs, files in os.walk(base_dir):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file.endswith('.json') and file not in EXCLUDE_FILES:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(base_dir)

                try:
                    # Read JSON file to extract type and name
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Extract metadata
                    file_type = data.get('type', 'unknown')
                    file_name = data.get('name', file.replace('.json', ''))
                    inherits = data.get('inherits', '')

                    json_files.append({
                        'name': file_name,
                        'type': file_type,
                        'inherits': inherits,
                        'sub_path': str(relative_path).replace('\\', '/'),
                        'file_path': str(file_path),
                        'relative_path': str(relative_path)
                    })

                    print(f"Found: {relative_path} (type: {file_type})")

                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse {relative_path}: {e}")
                except Exception as e:
                    print(f"Warning: Error reading {relative_path}: {e}")

    return json_files


def topological_sort_profiles(items: List[Dict], json_files_data: Dict[str, Dict]) -> List[Dict]:
    """
    Sort profiles based on their inheritance dependencies using topological sort.
    Profiles that are inherited from must come before profiles that inherit from them.

    Args:
        items: List of profile entries with 'name' and 'sub_path'
        json_files_data: Dict mapping name to full JSON data (including 'inherits')

    Returns:
        Sorted list of profile entries
    """
    # Build dependency graph
    dependencies = {}  # name -> list of names it depends on (inherits from)
    name_to_item = {item['name']: item for item in items}

    for item in items:
        name = item['name']
        data = json_files_data.get(name, {})
        inherits = data.get('inherits', '')

        if inherits:
            dependencies[name] = [inherits]
        else:
            dependencies[name] = []

    # Perform topological sort using Kahn's algorithm
    sorted_items = []

    # Calculate in-degrees: only count parents that exist in the current list
    in_degree = {}
    for name in name_to_item.keys():
        count = 0
        for parent in dependencies[name]:
            if parent in name_to_item:  # Only count if parent is in the same list
                count += 1
        in_degree[name] = count

    # Queue of items with no dependencies (or dependencies outside this list)
    queue = [name for name, degree in in_degree.items() if degree == 0]

    while queue:
        # Sort queue alphabetically for consistent ordering when there are no dependencies
        queue.sort()
        current = queue.pop(0)
        sorted_items.append(name_to_item[current])

        # Find all items that depend on current
        for name in dependencies:
            if current in dependencies[name]:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)

    # Check for circular dependencies
    if len(sorted_items) != len(items):
        print(f"Warning: Possible circular dependencies detected in profiles")
        # Add remaining items that weren't sorted
        remaining = [item for item in items if item not in sorted_items]
        sorted_items.extend(remaining)

    return sorted_items


def organize_by_type(json_files: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Organize JSON files by their type into separate lists.

    Returns:
        Tuple of (machine_models, machines, processes, filaments)
    """
    machine_models = []
    machines = []
    processes = []
    filaments = []

    # Create a dict to store full JSON data for dependency resolution
    json_files_data = {}
    for item in json_files:
        json_files_data[item['name']] = item

    for item in json_files:
        file_type = item['type']
        entry = {
            'name': item['name'],
            'sub_path': item['sub_path']
        }

        if file_type == 'machine_model':
            machine_models.append(entry)
        elif file_type == 'machine':
            machines.append(entry)
        elif file_type == 'process':
            processes.append(entry)
        elif file_type == 'filament':
            filaments.append(entry)
        else:
            print(f"Warning: Unknown type '{file_type}' for {item['sub_path']}")

    return machine_models, machines, processes, filaments, json_files_data


def generate_cosmyx_json(base_dir: Path, output_file: str = 'Cosmyx.json'):
    """
    Generate the Cosmyx.json file by scanning all JSON files.
    """
    print("=" * 60)
    print("Scanning directory for JSON files...")
    print("=" * 60)

    # Scan all JSON files
    json_files = scan_json_files(base_dir)

    print(f"\nTotal JSON files found: {len(json_files)}")

    # Organize by type
    machine_models, machines, processes, filaments, json_files_data = organize_by_type(json_files)

    print(f"\nOrganized files:")
    print(f"  - Machine Models: {len(machine_models)}")
    print(f"  - Machines: {len(machines)}")
    print(f"  - Processes: {len(processes)}")
    print(f"  - Filaments: {len(filaments)}")

    # Sort lists by dependency order (topological sort)
    print("\nSorting profiles by dependency order...")
    machine_models.sort(key=lambda x: x['name'])  # Machine models don't usually have inherits
    machines = topological_sort_profiles(machines, json_files_data)
    processes = topological_sort_profiles(processes, json_files_data)
    filaments = topological_sort_profiles(filaments, json_files_data)

    # Create the cosmyx.json structure
    cosmyx_data = {
        "name": "Cosmyx",
        "url": "http://www.cosmyx.com/Parameters/vendor/Cosmyx.json",
        "version": "01.07.00.18",
        "force_update": "0",
        "description": "Auto-generated Cosmyx configuration file",
        "machine_model_list": machine_models,
        "process_list": processes,
        "filament_list": filaments,
        "machine_list": machines
    }

    # Write to file (one level up from the script's directory)
    output_path = base_dir.parent / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cosmyx_data, f, indent=4, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Successfully generated: {output_path}")
    print(f"{'=' * 60}")

    return cosmyx_data


def print_summary(json_files: List[Dict]):
    """
    Print a summary of all scanned files grouped by type.
    """
    print("\n" + "=" * 60)
    print("SUMMARY OF SCANNED FILES")
    print("=" * 60)

    types = {}
    for item in json_files:
        file_type = item['type']
        if file_type not in types:
            types[file_type] = []
        types[file_type].append(item)

    for file_type, items in sorted(types.items()):
        print(f"\n{file_type.upper()} ({len(items)} files):")
        for item in sorted(items, key=lambda x: x['sub_path']):
            print(f"  - {item['name']}")
            print(f"    Path: {item['sub_path']}")


if __name__ == "__main__":
    try:
        # Generate the cosmyx.json file
        generate_cosmyx_json(BASE_DIR)

        print("\nDone!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
