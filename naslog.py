import os
import re
import sys
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def is_experiment_folder_name(folder_name):
    return bool(
        re.search(r'[RMD]\d{1,5}', folder_name) or   # Match R, M, D + 1-5 digits anywhere
        re.match(r'^20\d{6}', folder_name)           # Match if starts with 8-digit year date
    )

def get_folder_size_du(path):
    try:
        output = subprocess.check_output(['du', '-sBG', path], stderr=subprocess.DEVNULL).decode()
        size_str, _ = output.strip().split('\t')
        return int(size_str.rstrip('G'))
    except Exception:
        return 0
    
def get_nas_mounts_from_df():
    try:
        output = subprocess.check_output(['df', '-h'], text=True)
        mounts = []
        for line in output.splitlines():
            if ' /mnt/' in line and not any(x in line for x in ['tmpfs', 'udev']):
                mount_point = line.split()[-1]
                mounts.append(mount_point)
        return sorted(set(mounts))
    except subprocess.CalledProcessError:
        return []
    
def get_mounted_nas_overview():
    try:
        output = subprocess.check_output(['df', '-h'], text=True)
    except subprocess.CalledProcessError:
        print("Failed to run df -h")
        return []

    lines = output.strip().split('\n')
    header = lines[0]
    entries = lines[1:]

    cols = header.split()
    filesystem_i = cols.index('Filesystem')
    size_i = cols.index('Size')
    used_i = cols.index('Used')
    avail_i = cols.index('Avail')
    usep_i = cols.index('Use%')
    mounted_i = cols.index('Mounted')

    results = []
    for line in entries:
        parts = line.split()
        if len(parts) < 6:
            continue

        mount_point = parts[mounted_i]
        if not mount_point.startswith('/mnt/'):
            continue

        fs_type = parts[filesystem_i]
        if 'tmpfs' in fs_type or 'devtmpfs' in fs_type:
            continue

        results.append({
            'Mount': Path(mount_point).name,
            'Size': parts[size_i],
            'Used': parts[used_i],
            'Avail': parts[avail_i],
            'Use%': parts[usep_i],
        })

    return results

def collect_experiment_folders(base_path, min_size_gb):
    results = []

    print(f"Scanning {base_path} using du...")

    for root, dirs, _ in os.walk(base_path):
        # Skip hidden/system files and folders
        dirs[:] = [d for d in dirs if not (d.startswith('@') or d.startswith('.') or d.lower() in {'trash', 'recycle'})]

        for entry in dirs:
            dirpath = os.path.join(root, entry)

            # Skip hidden/system folders
            if not os.path.isdir(dirpath):
                continue

            # Check if folder name looks like an experiment
            if not is_experiment_folder_name(entry):
                continue

            # Skip folders nested within already-logged experiment folders
            if any(dirpath.startswith(p + os.sep) for p in [r['Path'] for r in results]):
                continue

            print(f"Checking: {dirpath}")
            size_gb = get_folder_size_du(dirpath)
            if size_gb < min_size_gb:
                continue
            print(f"Found {entry} with size: {size_gb} GB")

            try:
                last_modified = datetime.fromtimestamp(os.path.getmtime(dirpath))
                created = datetime.fromtimestamp(os.path.getctime(dirpath))
            except Exception:
                last_modified = created = None

            results.append({
                'Folder Name': entry,
                'Size (GB)': size_gb,
                'Size': f"{round(size_gb / 1024, 2)} TB" if size_gb >= 1024 else f"{round(size_gb, 2)} GB",
                'Path': dirpath,
                'Parent Folder': os.path.dirname(dirpath),
                'Last Modified': last_modified.strftime('%Y-%m-%d %H:%M') if last_modified else '',
                'Created Date': created.strftime('%Y-%m-%d %H:%M') if created else '',
            })

        dirs[:] = [d for d in dirs if not is_experiment_folder_name(d)]

    print(f"Found {len(results)} experiment folders.")
    return pd.DataFrame(results)

# --- Load configuration ---
# Load variables from .env
load_dotenv(dotenv_path=Path(__file__).parent / "juicebox.env")

PYTHON_BIN          = Path(os.getenv("PYTHON_BIN", sys.executable))
UPLOAD_SCRIPT       = Path(os.environ["UPLOAD_SCRIPT"])
SERVICE_ACCOUNT_JSON= Path(os.environ["SERVICE_ACCOUNT"])
DRIVE_FOLDER_ID     = os.environ["DRIVE_FOLDER_ID"]
MIN_SIZE_GB         = int(os.getenv("MIN_FOLDER_GB", 500))

nas_mounts = get_nas_mounts_from_df()
print(nas_mounts)
nas_logs = {}
# --- END CONFIG ---

# Collect Overview data
overview_data = get_mounted_nas_overview()
df_overview = pd.DataFrame(overview_data)
df_overview = df_overview.sort_values(by="Mount").reset_index(drop=True)

# NAS Scan
print("Starting NAS scan and log generation...")

for nas_path in nas_mounts:
    nas_name = os.path.basename(nas_path)
    df = collect_experiment_folders(nas_path, min_size_gb=MIN_SIZE_GB)
    if not df.empty:
        nas_logs[nas_name] = df
    else:
        print(f"No valid folders found in {nas_path}. Skipping...")

# Generate a timestamped filename
timestamp = datetime.now().strftime("%Y-%m-%d")
log_dir = Path.home() / "juicebox" / "nas_logs"
log_dir.mkdir(parents=True, exist_ok=True)
output_file = log_dir / f"nas_log_{timestamp}.xlsx"

print(f"Writing results to: {output_file}")

# Save the same nas_logs data into the timestamped file
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Write Overview first
    df_overview.to_excel(writer, sheet_name='Overview', index=False)
    workbook = writer.book
    overview_sheet = writer.sheets['Overview']

    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9D9D9',
        'border': 1
    })
    for col_num, value in enumerate(df_overview.columns.values):
        overview_sheet.write(0, col_num, value, header_format)

    # Right-align numeric columns
    right_align_format = workbook.add_format({'align': 'right'})
    for col in ["Size", "Used", "Avail"]:
        col_idx = df_overview.columns.get_loc(col)
        overview_sheet.set_column(col_idx, col_idx, None, right_align_format)

    # Write each NAS tab
    for nas_name, df in nas_logs.items():
        df.to_excel(writer, sheet_name=nas_name, index=False)

        # Formatting
        workbook  = writer.book
        worksheet = writer.sheets[nas_name]

        # Format for header row
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',  # light gray
            'border': 1
        })

        # Header format to each column in the header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

print("Log generation complete.")

# Call uploadplt3.py with the generated file
print("Starting upload to Google Drive...")
try:
    subprocess.run(
        [str(PYTHON_BIN), str(UPLOAD_SCRIPT),
         str(output_file), DRIVE_FOLDER_ID, str(SERVICE_ACCOUNT_JSON)],
        check=True
    )
    print("Upload successful.")
except subprocess.CalledProcessError as e:
    print("Upload failed:", e)