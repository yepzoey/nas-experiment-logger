# NAS Experiment Folder Logger & Google Drive Uploader

This tool scans one or more mounted NAS directories to identify large experiment folders based on folder naming conventions and size thresholds. It logs relevant metadata (name, size, path, timestamps) to a timestamped Excel file and automatically uploads the file to a specified Google Drive folder using a Google Cloud service account.

## Features

- Recursively scans specified NAS mount points (e.g., `/mnt/merfish15`)
- Identifies experiment folders based on:
  - Prefixes like `R1234`, `M567`, or `D104`
  - Date-based formats like `20230801...`
- Filters out small folders (<500 GB by default), hidden/system folders
- Records folder name, path, size, timestamps, and parent folder
- Outputs results into a timestamped `.xlsx` file
- Automatically uploads the log to a shared Google Drive folder

## Requirements

- Python 3.10+
- Conda environment with required packages:
  - `pandas`
  - `google-api-python-client`
  - `google-auth`
  - `google-auth-oauthlib`
  - `xlsxwriter`

You can install dependencies with:

```bash
pip install -r requirements.txt
