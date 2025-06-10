import sys
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_drive(file_path, drive_folder_id, service_account_json):
    credentials = service_account.Credentials.from_service_account_file(
        service_account_json,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [drive_folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    file = service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
    print(f"Uploaded file ID: {file.get('id')}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python upload_to_drive.py <file_path> <drive_folder_id> <service_account_json>")
        sys.exit(1)

    file_path = sys.argv[1]
    drive_folder_id = sys.argv[2]
    service_account_json = sys.argv[3]

    upload_to_drive(file_path, drive_folder_id, service_account_json)
