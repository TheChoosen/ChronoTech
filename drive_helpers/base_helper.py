# API_Documentation/drive_helpers/base_helper.py - FIXED VERSION

import os
import json
import pickle
import fcntl
import tempfile
import shutil
import threading
from contextlib import contextmanager
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseUpload, BatchHttpRequest
from googleapiclient.errors import HttpError
from io import BytesIO
import mimetypes
from typing import List, Dict, Optional
import time

class BaseGoogleDriveHelper:
    """
    Base class for Google Drive helpers, containing common API interaction logic.
    Subclasses must implement the _build_service method.
    """
    def __init__(self):
        self.service = self._build_service()
        self.deleted_folder_id = None # Initialize to None

    def _build_service(self):
        """
        This method must be implemented by subclasses to build the Google Drive service
        using a specific authentication method (OAuth2 or Service Account).
        """
        raise NotImplementedError("Subclasses must implement the _build_service method.")

    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self.service is not None

    def find_folder(self, folder_name, parent_id='root'):
        """Find a folder by name under the given parent. Returns the folder ID if found, else None."""
        if not self.service:
            return None
        try:
            query = (
                f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
                f"and '{parent_id}' in parents and trashed=false"
            )
            results = self.service.files().list(q=query, fields='files(id)').execute()
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
        except Exception as e:
            print(f"Error finding folder '{folder_name}': {e}")
            return None

            
    def _get_or_create_deleted_items_folder(self) -> str:
        """Gets or creates a 'Deleted Items' folder for files that cannot be permanently deleted."""
        if self.deleted_folder_id:
            return self.deleted_folder_id

        folder_name = "Deleted Items (Managed)"
        # Try to find the folder first
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])

        if files:
            self.deleted_folder_id = files[0]['id']
            print(f"Found 'Deleted Items (Managed)' folder: {self.deleted_folder_id}")
            return self.deleted_folder_id
        else:
            # Create the folder if it doesn't exist
            print(f"'{folder_name}' folder not found, creating it...")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            try:
                folder = self.service.files().create(body=folder_metadata, fields='id').execute()
                self.deleted_folder_id = folder.get('id')
                print(f"Created 'Deleted Items (Managed)' folder: {self.deleted_folder_id}")
                return self.deleted_folder_id
            except Exception as e:
                print(f"Error creating 'Deleted Items (Managed)' folder: {e}")
                return 'root' # Fallback to root if folder creation fails

    def _move_to_deleted_items_folder(self, file_id: str) -> bool:
        """Moves a file or folder to the 'Deleted Items' folder."""
        deleted_items_folder_id = self._get_or_create_deleted_items_folder()
        if not deleted_items_folder_id:
            print(f"Could not find or create 'Deleted Items' folder. Cannot move {file_id}.")
            return False

        try:
            # Get current parents to remove them
            file_metadata = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file_metadata.get('parents', []))

            self.service.files().update(
                fileId=file_id,
                addParents=deleted_items_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print(f"Moved {file_id} to 'Deleted Items (Managed)' folder.")
            return True
        except HttpError as e:
            if e.resp.status == 403:
                print(f"Permission denied to move {file_id} to 'Deleted Items' folder. It will remain in its current location.")
            else:
                print(f"Error moving {file_id} to 'Deleted Items' folder: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while moving {file_id}: {e}")
            return False

    def create_folder(self, folder_name: str, parent_id: str = 'root') -> Optional[str]:
        """Creates a single folder."""
        if not self.is_authenticated():
            return None
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            #print(f"Created folder: '{folder_name}' (ID: {folder.get('id')})")
            return folder.get('id')
        except Exception as e:
            print(f"Error creating folder '{folder_name}': {e}")
            return None

    def create_folder_path(self, path_parts: List[str], parent_folder_id: str = 'root') -> Optional[str]:
        """Ensures a folder path exists, creating folders as needed."""
        current_parent_id = parent_folder_id
        for part in path_parts:
            folder_id = self.find_folder(part, current_parent_id)
            if not folder_id:
                folder_id = self.create_folder(part, current_parent_id)
                if not folder_id:
                    return None  # Failed to create a folder in the path
            current_parent_id = folder_id
        return current_parent_id

    def upload_file(self, file_content: bytes, filename: str, folder_id: str, mime_type: Optional[str] = None) -> Optional[Dict]:
        """Uploads a file to a specified folder in Google Drive."""
        if not self.is_authenticated():
            return None
        try:
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = 'application/octet-stream'

            file_metadata = {'name': filename, 'parents': [folder_id]}
            media = MediaIoBaseUpload(BytesIO(file_content), mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink, size, createdTime, mimeType'
            ).execute()
            
            # CRITICAL FIX: Return the correct proxy URL for images
            file_id = file.get('id')
            
            return {
                'id': file_id,
                'name': file.get('name'),
                'link': file.get('webViewLink'),
                'download_link': file.get('webContentLink'),
                'direct_link': f"/api/drive-image/{file_id}",  # Fixed proxy URL
                'size': int(file.get('size', 0)),
                'created_time': file.get('createdTime'),
                'mime_type': file.get('mimeType')
            }
        except Exception as e:
            print(f"Error uploading file '{filename}': {e}")
            return None

    def delete_file(self, file_id: str) -> bool:
        """
        Deletes a file from Google Drive by moving it to trash.
        If permission is denied to trash, it attempts to move it to a 'Deleted Items (Managed)' folder.
        """
        if not self.is_authenticated():
            print("Not authenticated. Cannot delete file.")
            return False

        try:
            # Try to move to trash first
            self.service.files().update(
                fileId=file_id,
                body={'trashed': True},
                supportsAllDrives=True # Important for Shared Drives
            ).execute()
            print(f"File {file_id} moved to trash successfully.")
            return True
        except HttpError as e:
            if e.resp.status == 403: # Permission denied (e.g., trying to delete a file not owned)
                print(f"Permission denied to trash file {file_id}. Attempting to move to 'Deleted Items (Managed)' folder.")
                return self._move_to_deleted_items_folder(file_id)
            else:
                print(f"An error occurred while trashing file {file_id}: {e}")
                return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False

