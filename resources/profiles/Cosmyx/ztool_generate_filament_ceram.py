#!/usr/bin/env python3
"""
Script to generate machine-specific filament JSON variants from the common filament library.
Creates filament configurations for each machine/nozzle combination in Machine/*/*/filament/ directories.
"""

import json
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ==================== CONFIGURATION CONSTANTS ====================

MACHINE_DISPLAY_MAP = {
    'NOVA_CERAM': 'Nova Metal Ceramique',
    'SNV2_DT_CERAM': 'SuperNova DT Metal Ceramique'
}

STANDARD_MACHINES = ['NOVA_CERAM', 'SNV2_DT_CERAM']
NOZZLE_SIZES = ['0.2', '0.4', '0.6', '0.8']
VERSION = "01.07.00.18"

BASE_DIR = Path(__file__).parent
COMMON_FILAMENT_DIR = BASE_DIR / 'Common Filament library' / 'ceramics'
MACHINE_DIR = BASE_DIR / 'Machine'


# ==================== DATA STRUCTURES ====================

@dataclass
class FilamentInfo:
    """Metadata for a common filament file"""
    file_path: Path
    name: str  # Full name with @Cosmyx Common
    inherits: str
    nozzle_specific: Optional[str] = None  # e.g., "0.4"


@dataclass
class MachineInfo:
    """Metadata for a machine configuration"""
    machine_type: str  # e.g., "NOVA"
    nozzle_size: str  # e.g., "0.4"
    printer_name: str  # e.g., "Cosmyx Nova 0.4 nozzle"
    filament_dir: Path  # e.g., Machine/NOVA/NOVA 0.4/filament


@dataclass
class GenerationResult:
    """Result tracking for the generation process"""
    total_source_filaments: int = 0
    total_variants_generated: int = 0
    files_created: List[Path] = field(default_factory=list)
    files_skipped: List[Path] = field(default_factory=list)
    errors: List[Tuple[Path, str]] = field(default_factory=list)


# ==================== UTILITY FUNCTIONS ====================

def scan_common_filaments() -> List[FilamentInfo]:
    """
    Scan the common filament library for processable filament files.

    Returns:
        List of FilamentInfo objects for valid source filaments
    """
    filaments = []

    if not COMMON_FILAMENT_DIR.exists():
        print(f"Error: Common filament directory not found: {COMMON_FILAMENT_DIR}")
        return filaments

    for file_path in COMMON_FILAMENT_DIR.glob('*.json'):
        filename = file_path.name

        # Filter: must contain @Cosmyx Common
        if '@Cosmyx Common' not in filename:
            continue

        # Exclude base files and generic filament definitions
        if '@base.json' in filename or filename.startswith('fdm_filament_'):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            name = data.get('name', filename.replace('.json', ''))
            inherits = data.get('inherits', '')

            # Check if nozzle-specific
            nozzle_specific = None
            for nozzle in NOZZLE_SIZES:
                if f'{nozzle} nozzle' in filename:
                    nozzle_specific = nozzle
                    break

            filaments.append(FilamentInfo(
                file_path=file_path,
                name=name,
                inherits=inherits,
                nozzle_specific=nozzle_specific
            ))

        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse {file_path.name}: {e}")
        except Exception as e:
            print(f"Warning: Error reading {file_path.name}: {e}")

    return filaments


def find_highest_mil_id(filaments: List[FilamentInfo]) -> int:
    """
    Find the highest MIL ID number in the source filaments.

    Returns:
        The next available MIL number
    """
    max_mil = 0
    mil_pattern = re.compile(r'MIL(\d+)')

    for filament in filaments:
        # Read the JSON to get filament_id
        try:
            with open(filament.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            filament_id = data.get('filament_id', '')
            match = mil_pattern.search(filament_id)
            if match:
                mil_num = int(match.group(1))
                max_mil = max(max_mil, mil_num)
        except:
            pass

    return max_mil + 1


def scan_machine_configs() -> Dict[str, Dict[str, MachineInfo]]:
    """
    Scan machine configurations to find all machine/nozzle combinations.

    Returns:
        Nested dict: {machine_type: {nozzle_size: MachineInfo}}
    """
    machines = {}

    if not MACHINE_DIR.exists():
        print(f"Error: Machine directory not found: {MACHINE_DIR}")
        return machines

    for machine_type in STANDARD_MACHINES:
        machine_type_dir = MACHINE_DIR / machine_type

        if not machine_type_dir.exists():
            continue

        machines[machine_type] = {}

        for nozzle_size in NOZZLE_SIZES:
            nozzle_dir = machine_type_dir / f"{machine_type} {nozzle_size}"

            if not nozzle_dir.exists():
                continue

            # Find the machine JSON file
            json_files = list(nozzle_dir.glob('*.json'))
            machine_json = None

            for json_file in json_files:
                # Skip files in subdirectories
                if json_file.parent != nozzle_dir:
                    continue
                # Look for the main machine config (not in filament subdir)
                if 'filament' not in json_file.parts:
                    machine_json = json_file
                    break

            if not machine_json:
                continue

            try:
                with open(machine_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                printer_name = data.get('name', f'Cosmyx {MACHINE_DISPLAY_MAP[machine_type]} {nozzle_size} nozzle')
                filament_dir = nozzle_dir / 'filament' / 'ceramics'

                machines[machine_type][nozzle_size] = MachineInfo(
                    machine_type=machine_type,
                    nozzle_size=nozzle_size,
                    printer_name=printer_name,
                    filament_dir=filament_dir
                )

            except Exception as e:
                print(f"Warning: Error reading {machine_json}: {e}")

    return machines


def transform_filament_name(source_name: str, machine_type: str, nozzle_size: str) -> str:
    """
    Transform the source filament name to the machine-specific variant name.

    Args:
        source_name: Original name from common library
        machine_type: Target machine type (e.g., "NOVA")
        nozzle_size: Target nozzle size (e.g., "0.4")

    Returns:
        Transformed name for the variant
    """
    machine_display = MACHINE_DISPLAY_MAP.get(machine_type, machine_type)

    # Handle nozzle-specific source names
    # e.g., "Cosmyx ABS @Cosmyx Common 0.2 nozzle" -> "Cosmyx ABS @Nova 0.2 nozzle"
    if ' nozzle' in source_name:
        # Replace @Cosmyx Common with @{machine}
        new_name = source_name.replace('@Cosmyx Common', f'@{machine_display}')
    else:
        # Standard case: add nozzle size
        # e.g., "CAPIFIL PLA BLANC @Cosmyx Common" -> "CAPIFIL PLA BLANC @Nova 0.2"
        new_name = source_name.replace('@Cosmyx Common', f'@{machine_display} {nozzle_size}')

    return new_name


def write_filament_file(variant_data: dict, output_path: Path) -> bool:
    """
    Write a filament variant JSON file to disk.

    Args:
        variant_data: The JSON data to write
        output_path: Target file path

    Returns:
        True if file was created, False if skipped (already exists)
    """
    # Skip if file already exists
    if output_path.exists():
        return False

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(variant_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing {output_path}: {e}")
        return False


# ==================== MAIN GENERATION LOGIC ====================

def generate_all_variants() -> GenerationResult:
    """
    Main function to generate all filament variants.

    Returns:
        GenerationResult with statistics
    """
    results = GenerationResult()

    print("=" * 60)
    print("Filament Variant Generator")
    print("=" * 60)

    # Step 1: Scan common filaments
    print("\nScanning common filament library...")
    common_filaments = scan_common_filaments()
    results.total_source_filaments = len(common_filaments)
    print(f"Found {len(common_filaments)} source filaments")

    if not common_filaments:
        print("No filaments found to process!")
        return results

    # Step 2: Find starting MIL ID
    starting_mil = find_highest_mil_id(common_filaments)
    print(f"Starting MIL ID: MIL{starting_mil:02d}")

    # Step 3: Scan machine configurations
    print("\nScanning machine configurations...")
    machines = scan_machine_configs()
    total_configs = sum(len(nozzles) for nozzles in machines.values())
    print(f"Found {total_configs} machine/nozzle configurations")

    if not machines:
        print("No machine configurations found!")
        return results

    # Step 4: Generate variants
    print("\nGenerating variants...")
    current_mil = starting_mil

    for source_filament in common_filaments:
        print(f"\nProcessing: {source_filament.name}")

        for machine_type in STANDARD_MACHINES:
            if machine_type not in machines:
                continue

            for nozzle_size in NOZZLE_SIZES:
                if nozzle_size not in machines[machine_type]:
                    continue

                machine_info = machines[machine_type][nozzle_size]

                # Skip if nozzle-specific source doesn't match
                if source_filament.nozzle_specific:
                    if source_filament.nozzle_specific != nozzle_size:
                        continue

                # Transform name
                new_name = transform_filament_name(
                    source_filament.name,
                    machine_type,
                    nozzle_size
                )

                # Generate unique ID
                nozzle_suffix = nozzle_size.replace('.', '')  # 0.2 -> 02
                filament_id = f"MIL{current_mil:02d}_{machine_type}_{nozzle_suffix}"

                # Build variant JSON
                variant = {
                    "type": "filament",
                    "filament_id": filament_id,
                    "name": new_name,
                    "from": "system",
                    "instantiation": "true",
                    "inherits": source_filament.name,
                    "compatible_printers": [machine_info.printer_name],
                    "version": VERSION
                }

                # Write file
                output_path = machine_info.filament_dir / f"{new_name}.json"

                if write_filament_file(variant, output_path):
                    results.files_created.append(output_path)
                    results.total_variants_generated += 1
                else:
                    results.files_skipped.append(output_path)

        # Increment MIL number for next source filament
        current_mil += 1

    return results


def print_report(results: GenerationResult):
    """Print a summary report of the generation process"""
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Source filaments processed: {results.total_source_filaments}")
    print(f"Variants generated: {results.total_variants_generated}")
    print(f"Files created: {len(results.files_created)}")
    print(f"Files skipped (already exist): {len(results.files_skipped)}")
    print(f"Errors: {len(results.errors)}")
    print("=" * 60)


# ==================== MAIN ENTRY POINT ====================

def main():
    """Main entry point"""
    try:
        results = generate_all_variants()
        print_report(results)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
