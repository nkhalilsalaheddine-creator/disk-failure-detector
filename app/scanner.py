"""
scanner.py
Runs smartctl via subprocess on a given disk, parses the JSON output,
and returns a single-row DataFrame matching the model's expected features.
"""

import subprocess
import json
import pandas as pd


# SMART attribute IDs the model was trained on
SMART_ATTRS = [
    'smart_1_raw',
    'smart_3_raw',
    'smart_4_raw',
    'smart_5_raw',
    'smart_7_raw',
    'smart_9_raw',
    'smart_12_raw',
    'smart_187_raw',
    'smart_188_raw',
    'smart_191_raw',
    'smart_192_raw',
    'smart_193_raw',
    'smart_197_raw',
    'smart_198_raw',
]


def get_connected_disks() -> list[str]:
    """
    Uses smartctl --scan to find all connected disks.
    Returns a list of device paths e.g. ['/dev/sda', '/dev/sdb'].
    """
    try:
        result = subprocess.run(
            ['smartctl', '--scan'],
            capture_output=True, text=True, timeout=10
        )
        disks = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                disks.append(parts[0])  # e.g. /dev/sda
        return disks
    except Exception:
        return []


def run_smartctl(disk_path: str) -> dict:
    """
    Runs smartctl -a --json on the given disk path.
    Returns the parsed JSON dict or raises RuntimeError on failure.
    """
    try:
        result = subprocess.run(
            ['smartctl', '-a', '--json', disk_path],
            capture_output=True, text=True, timeout=30
        )
        if not result.stdout.strip():
            raise RuntimeError(f"smartctl returned no output for {disk_path}.")

        data = json.loads(result.stdout)
        return data

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"smartctl timed out scanning {disk_path}.")
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse smartctl JSON output for {disk_path}.")
    except FileNotFoundError:
        raise RuntimeError("smartctl not found. Please install smartmontools.")


def parse_smartctl_to_row(smartctl_data: dict) -> pd.DataFrame:
    """
    Parses a smartctl JSON dict into a single-row DataFrame
    matching the features expected by the trained model.
    """
    row = {}

    # --- Disk identity ---
    model_name = smartctl_data.get('model_name', 'Unknown')
    capacity_bytes = smartctl_data.get('user_capacity', {}).get('bytes', 0)
    row['capacity_gigabytes'] = round(capacity_bytes / (1024 ** 3), 2)

    # --- SSD flag ---
    rotation_rate = smartctl_data.get('rotation_rate', None)
    row['is_ssd'] = 1 if rotation_rate == 0 else 0

    # --- SMART attributes ---
    ata_attrs = smartctl_data.get('ata_smart_attributes', {}).get('table', [])
    attr_map = {f"smart_{entry['id']}_raw": entry['raw']['value'] for entry in ata_attrs}

    for col in SMART_ATTRS:
        attr_id = int(col.split('_')[1])
        raw_val = attr_map.get(col, 0)
        # For mechanical columns, if disk is SSD fill with 0
        mechanical = ['smart_3_raw', 'smart_4_raw', 'smart_193_raw']
        if col in mechanical and row['is_ssd'] == 1:
            row[col] = 0
        else:
            row[col] = raw_val if raw_val is not None else 0

    # --- Engineered features ---
    critical = ['smart_5_raw', 'smart_187_raw', 'smart_197_raw', 'smart_198_raw']
    total_errors = sum(row.get(c, 0) for c in critical)
    row['any_critical_error'] = 1 if total_errors > 0 else 0
    row['total_error_count'] = total_errors
    row['error_per_gb'] = total_errors / row['capacity_gigabytes'] if row['capacity_gigabytes'] > 0 else 0

    # --- Store model name separately for display (not passed to model) ---
    row['_model_name'] = model_name
    row['_disk_path'] = smartctl_data.get('_disk_path', '')

    return pd.DataFrame([row])


def scan_disk(disk_path: str) -> pd.DataFrame:
    """
    Full pipeline: runs smartctl on disk_path and returns a model-ready DataFrame row.
    """
    raw_data = run_smartctl(disk_path)
    raw_data['_disk_path'] = disk_path
    return parse_smartctl_to_row(raw_data)
