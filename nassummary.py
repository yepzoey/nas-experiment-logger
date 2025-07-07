import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime

def get_mounted_nas_overview():
    try:
        output = subprocess.check_output(['df', '-h'], text=True)
    except subprocess.CalledProcessError:
        print("Failed to run df -h")
        return []

    lines = output.strip().split('\n')
    header = lines[0]
    entries = lines[1:]

    # Extract columns by header positions
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

# --- Get overview data ---
overview_data = get_mounted_nas_overview()

if not overview_data:
    print("No mounts found!")
    exit(0)

# --- Write to Excel ---
timestamp = datetime.now().strftime("%Y-%m-%d")
output_file = Path.home() / "juicebox" / f"nas_overview_{timestamp}.xlsx"
output_file.parent.mkdir(parents=True, exist_ok=True)

df_overview = pd.DataFrame(overview_data)
df_overview = df_overview.sort_values(by="Mount").reset_index(drop=True)
print(df_overview)

with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    df_overview.to_excel(writer, sheet_name='Overview', index=False)

    workbook  = writer.book
    worksheet = writer.sheets['Overview']

    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9D9D9',
        'border': 1
    })

    for col_num, value in enumerate(df_overview.columns.values):
        worksheet.write(0, col_num, value, header_format)

    # Right-align format for data cells
    right_align_format = workbook.add_format({'align': 'right'})

    # Apply right-align to Size, Used, Avail columns
    for col in ["Size", "Used", "Avail"]:
        col_idx = df_overview.columns.get_loc(col)
        worksheet.set_column(col_idx, col_idx, None, right_align_format)

print(f"Wrote summary to {output_file}")