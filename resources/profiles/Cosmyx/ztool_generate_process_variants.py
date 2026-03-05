#!/usr/bin/env python3
"""
Script to generate machine-specific process JSON variants from the common process library.
Creates process configurations for each machine/nozzle combination in Machine/*/*/process/ directories.
"""

import json
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ==================== CONFIGURATION CONSTANTS ====================

MACHINE_DISPLAY_MAP = {
    'NOVA': 'Nova',
    'SNV2': 'SuperNova',
    'NOVA_DT': 'Nova DT',
    'SNV2_DT': 'SuperNova DT',
    'HT': 'Haute Temperature',
    'NOVA_CERAM': 'Nova Metal Ceramique',
    'SNV2_DT_CERAM': 'SuperNova DT Metal Ceramique',
    'NOVA_CAN_OUT': 'Cosmyx Nova can-out'
}

# Machine name patterns in process compatible_printers
MACHINE_PRINTER_NAMES = {
    'NOVA': 'Cosmyx Nova',
    'SNV2': 'Cosmyx SuperNova',
    'NOVA_DT': 'Cosmyx Nova Double Tete',
    'SNV2_DT': 'Cosmyx SuperNova Double Tete',
    'HT': 'Cosmyx Nova Haute Temperature',
    'NOVA_CERAM': 'Cosmyx Nova Metal Ceramique',
    'SNV2_DT_CERAM': 'Cosmyx SuperNova Double Tete Metal Ceramique',
    'NOVA_CAN_OUT': 'Cosmyx Nova can-out'
}

STANDARD_MACHINES = ['NOVA', 'SNV2', 'NOVA_DT', 'SNV2_DT', 'HT', 'NOVA_CERAM', 'SNV2_DT_CERAM', 'NOVA_CAN_OUT']
NOZZLE_SIZES = ['0.2', '0.4', '0.6', '0.8']
VERSION = "01.07.00.18"

BASE_DIR = Path(__file__).parent
COMMON_PROCESS_DIR = BASE_DIR / 'Common Process Library'
MACHINE_DIR = BASE_DIR / 'Machine'


# ==================== DATA STRUCTURES ====================

@dataclass
class ProcessInfo:
    """Metadata for a common process file"""
    file_path: Path
    name: str  # Full name with @Cosmyx Nova or @Metal and Ceramics
    inherits: str
    setting_id: str
    nozzle_size: str  # e.g., "0.4" (determined by directory structure)
    process_type: str  # "STANDARD" or "CERAM"
    layer_height: str  # e.g., "0.20mm"


@dataclass
class MachineInfo:
    """Metadata for a machine configuration"""
    machine_type: str  # e.g., "NOVA"
    nozzle_size: str  # e.g., "0.4"
    printer_name: str  # e.g., "Cosmyx Nova 0.4 nozzle"
    process_dir: Path  # e.g., Machine/NOVA/NOVA 0.4/process


@dataclass
class GenerationResult:
    """Result tracking for the generation process"""
    total_source_processes: int = 0
    total_variants_generated: int = 0
    files_created: List[Path] = field(default_factory=list)
    files_skipped: List[Path] = field(default_factory=list)
    errors: List[Tuple[Path, str]] = field(default_factory=list)


# ==================== UTILITY FUNCTIONS ====================

def scan_common_processes() -> List[ProcessInfo]:
    """
    Scan the common process library for processable process files.

    Returns:
        List of ProcessInfo objects for valid source processes
    """
    processes = []

    if not COMMON_PROCESS_DIR.exists():
        print(f"Error: Common process directory not found: {COMMON_PROCESS_DIR}")
        return processes

    # Scan each nozzle size directory
    for nozzle_dir in COMMON_PROCESS_DIR.iterdir():
        if not nozzle_dir.is_dir() or not nozzle_dir.name.startswith('Process '):
            continue

        # Extract nozzle size from directory name (e.g., "Process 0.4" -> "0.4")
        nozzle_size = nozzle_dir.name.replace('Process ', '')
        if nozzle_size not in NOZZLE_SIZES:
            continue

        # Scan both STANDARD and CERAM subdirectories
        for process_type_dir in nozzle_dir.iterdir():
            if not process_type_dir.is_dir():
                continue

            process_type = process_type_dir.name  # "STANDARD" or "CERAM"
            if process_type not in ['STANDARD', 'CERAM']:
                continue

            # Scan JSON files in this directory
            for file_path in process_type_dir.glob('*.json'):
                filename = file_path.name

                # Exclude base/template files
                if filename.startswith('fdm_process_'):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    name = data.get('name', filename.replace('.json', ''))
                    inherits = data.get('inherits', '')
                    setting_id = data.get('setting_id', '')

                    # Extract layer height from name (e.g., "0.20mm Standard @Cosmyx Nova")
                    layer_height_match = re.match(r'^(\d+\.\d+mm)', name)
                    layer_height = layer_height_match.group(1) if layer_height_match else ''

                    processes.append(ProcessInfo(
                        file_path=file_path,
                        name=name,
                        inherits=inherits,
                        setting_id=setting_id,
                        nozzle_size=nozzle_size,
                        process_type=process_type,
                        layer_height=layer_height
                    ))

                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse {file_path.name}: {e}")
                except Exception as e:
                    print(f"Warning: Error reading {file_path.name}: {e}")

    return processes


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
                # Look for the main machine config
                path_str = str(json_file).lower()
                if 'filament' not in path_str and 'process' not in path_str:
                    machine_json = json_file
                    break

            if not machine_json:
                continue

            try:
                with open(machine_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                printer_name = data.get('name', f'Cosmyx {MACHINE_DISPLAY_MAP[machine_type]} {nozzle_size} nozzle')
                process_dir = nozzle_dir / 'process'

                machines[machine_type][nozzle_size] = MachineInfo(
                    machine_type=machine_type,
                    nozzle_size=nozzle_size,
                    printer_name=printer_name,
                    process_dir=process_dir
                )

            except Exception as e:
                print(f"Warning: Error reading {machine_json}: {e}")

    return machines


def is_machine_compatible_with_process(machine_type: str, process_type: str) -> bool:
    """
    Determine if a machine type is compatible with a process type.

    Args:
        machine_type: Machine type (e.g., "NOVA", "NOVA_CERAM")
        process_type: Process type ("STANDARD" or "CERAM")

    Returns:
        True if compatible
    """
    if process_type == 'CERAM':
        # CERAM processes only for ceramic machines
        return machine_type in ['NOVA_CERAM', 'SNV2_DT_CERAM']
    else:
        # STANDARD processes for all machines
        return True


def transform_process_name(source_name: str, machine_type: str, nozzle_size: str) -> str:
    """
    Transform the source process name to the machine-specific variant name.

    Args:
        source_name: Original name from common library
        machine_type: Target machine type (e.g., "NOVA")
        nozzle_size: Target nozzle size (e.g., "0.4")

    Returns:
        Transformed name for the variant
    """
    machine_display = MACHINE_DISPLAY_MAP.get(machine_type, machine_type)

    # Handle standard processes
    # e.g., "0.20mm Standard @Cosmyx Nova" -> "0.20mm Standard @Nova 0.4"
    if '@Cosmyx Nova' in source_name:
        # Replace @Cosmyx Nova with @{machine} {nozzle}
        if ' nozzle' in source_name:
            # Already has nozzle size, replace machine part
            # e.g., "0.10mm Standard @Cosmyx Nova 0.2 nozzle" -> "0.10mm Standard @SuperNova 0.2 nozzle"
            new_name = re.sub(r'@Cosmyx Nova', f'@{machine_display}', source_name)
        else:
            # Add nozzle size
            # e.g., "0.20mm Standard @Cosmyx Nova" -> "0.20mm Standard @SuperNova 0.4"
            new_name = source_name.replace('@Cosmyx Nova', f'@{machine_display} {nozzle_size}')

    # Handle ceramic processes
    # e.g., "0.20mm Standard @Metal and Ceramics" -> "0.20mm Standard @Nova Metal Ceramique 0.4"
    elif '@Metal and Ceramics' in source_name:
        if ' nozzle' in source_name:
            # Already has nozzle size
            new_name = source_name.replace('@Metal and Ceramics', f'@{machine_display}')
        else:
            # Add nozzle size
            new_name = source_name.replace('@Metal and Ceramics', f'@{machine_display} {nozzle_size}')

    else:
        # Fallback: append machine and nozzle
        new_name = f"{source_name} @{machine_display} {nozzle_size}"

    return new_name


def get_compatible_printer_name(machine_type: str, nozzle_size: str) -> str:
    """
    Get the printer name for compatible_printers field.

    Args:
        machine_type: Machine type (e.g., "NOVA")
        nozzle_size: Nozzle size (e.g., "0.4")

    Returns:
        Printer name string
    """
    printer_base = MACHINE_PRINTER_NAMES.get(machine_type, f'Cosmyx {machine_type}')
    return f"{printer_base} {nozzle_size} nozzle"


def write_process_file(variant_data: dict, output_path: Path) -> bool:
    """
    Write a process variant JSON file to disk.

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
    Main function to generate all process variants.

    Returns:
        GenerationResult with statistics
    """
    results = GenerationResult()

    print("=" * 60)
    print("Process Variant Generator")
    print("=" * 60)

    # Step 1: Scan common processes
    print("\nScanning common process library...")
    common_processes = scan_common_processes()
    results.total_source_processes = len(common_processes)
    print(f"Found {len(common_processes)} source processes")

    if not common_processes:
        print("No processes found to process!")
        return results

    # Step 2: Scan machine configurations
    print("\nScanning machine configurations...")
    machines = scan_machine_configs()
    total_configs = sum(len(nozzles) for nozzles in machines.values())
    print(f"Found {total_configs} machine/nozzle configurations")

    if not machines:
        print("No machine configurations found!")
        return results

    # Step 3: Generate variants
    print("\nGenerating variants...")

    for source_process in common_processes:
        print(f"\nProcessing: {source_process.name}")

        for machine_type in STANDARD_MACHINES:
            if machine_type not in machines:
                continue

            # Check machine compatibility with process type
            if not is_machine_compatible_with_process(machine_type, source_process.process_type):
                continue

            # Only process for matching nozzle size
            if source_process.nozzle_size not in machines[machine_type]:
                continue

            machine_info = machines[machine_type][source_process.nozzle_size]

            # Transform name
            new_name = transform_process_name(
                source_process.name,
                machine_type,
                source_process.nozzle_size
            )

            # Get compatible printer name
            compatible_printer = get_compatible_printer_name(machine_type, source_process.nozzle_size)

            # Read source file to copy all properties
            try:
                with open(source_process.file_path, 'r', encoding='utf-8') as f:
                    source_data = json.load(f)
            except Exception as e:
                results.errors.append((source_process.file_path, str(e)))
                continue

            # Build variant JSON (copy source and override key fields)
            variant = source_data.copy()
            variant['name'] = new_name
            variant['compatible_printers'] = [compatible_printer]
            variant['version'] = VERSION

            # Write file
            output_path = machine_info.process_dir / f"{new_name}.json"

            if write_process_file(variant, output_path):
                results.files_created.append(output_path)
                results.total_variants_generated += 1
                print(f"  + Created: {machine_type} {source_process.nozzle_size} - {new_name}")
            else:
                results.files_skipped.append(output_path)

    return results


def print_report(results: GenerationResult):
    """Print a summary report of the generation process"""
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Source processes processed: {results.total_source_processes}")
    print(f"Variants generated: {results.total_variants_generated}")
    print(f"Files created: {len(results.files_created)}")
    print(f"Files skipped (already exist): {len(results.files_skipped)}")
    print(f"Errors: {len(results.errors)}")

    if results.errors:
        print("\nErrors encountered:")
        for file_path, error in results.errors:
            print(f"  - {file_path.name}: {error}")

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
