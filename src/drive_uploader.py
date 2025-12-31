# ABOUTME: Google Drive file upload and folder management functionality
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class DriveUploader:
    """Handles uploading files to Google Drive with folder organization"""

    def __init__(self, config):
        self.config = config
        self.drive_service = self._get_drive_service()

    def _get_drive_service(self):
        """Create a Google Drive service instance"""
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise Exception("GOOGLE_APPLICATION_CREDENTIALS is not set.")

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
        return build("drive", "v3", credentials=credentials)

    def get_or_create_folder(self, folder_name, parent_folder_id=None):
        """
        Checks if a folder with the given name exists in Drive;
        if not, creates it. Returns the folder ID.
        """
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        results = (
            self.drive_service.files()
            .list(q=query, fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])

        if files:
            print(f"Folder '{folder_name}' found with ID: {files[0]['id']}")
            return files[0]["id"]
        else:
            print(f"Folder '{folder_name}' not found. Creating new folder.")
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            folder = (
                self.drive_service.files()
                .create(body=file_metadata, fields="id")
                .execute()
            )
            folder_id = folder.get("id")
            print(f"Folder '{folder_name}' created with ID: {folder_id}")
            return folder_id

    def upload_file(self, file_path, folder_id, mimetype=None):
        """
        Uploads a file to Google Drive into the specified folder.
        If a file with the same name already exists, it skips the upload.
        Returns the file ID if successful, None otherwise.
        """
        file_name = os.path.basename(file_path)

        # Check if file already exists
        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        logging.info(f"Querying Drive with: {query}")

        results = (
            self.drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        existing_files = results.get("files", [])
        logging.info(
            f"Query returned {len(existing_files)} result(s) for file '{file_name}'."
        )

        if existing_files:
            logging.info(
                f"File '{file_name}' already exists in folder ID {folder_id}. Skipping upload."
            )
            return existing_files[0]["id"]

        # Upload new file
        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = (
            MediaFileUpload(file_path, mimetype=mimetype)
            if mimetype
            else MediaFileUpload(file_path)
        )
        file = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = file.get("id")
        logging.info(
            f"Uploaded '{file_path}' to Drive folder ID: {folder_id} as file ID: {file_id}"
        )
        return file_id
