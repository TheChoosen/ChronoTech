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
from io import BytesIO
import mimetypes
from typing import List, Dict, Optional
import time

from .safe_token_manager import SafeTokenManager

from .base_helper import BaseGoogleDriveHelper

class GoogleDriveOAuthHelper(BaseGoogleDriveHelper):
    """Google Drive helper for OAuth2 user authentication."""

    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.token_manager = SafeTokenManager(token_file)
        super().__init__()

    def _build_service(self):
        """Builds the Google Drive service using OAuth2 credentials."""
        creds = self.token_manager.safe_read()
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.token_manager.safe_write(creds)
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return None
            else:
                print("Authentication required. Please run the authentication setup.")
                return None
        
        return build('drive', 'v3', credentials=creds)

    def authenticate_user(self):
        """Enhanced authentication with corruption prevention"""
        if not os.path.exists(self.credentials_file):
            print(f"❌ {self.credentials_file} not found!")
            print("Please download OAuth2 credentials from Google Cloud Console")
            return False
        
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file, 
                scopes=self.scopes,
                redirect_uri='http://localhost:5000/oauth2callback'  # Match credentials.json
            )
            
            # Get authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print("🔗 Please visit this URL to authorize the application:")
            print(auth_url)
            print()
            print("📋 After authorizing, paste the full redirect URL or just the code:")
            
            # Get authorization code from user
            redirect_response = input().strip()
            
            if not redirect_response:
                print("❌ No input provided")
                return False
            
            # Extract code from URL or use as-is
            if 'code=' in redirect_response:
                import urllib.parse as urlparse
                parsed = urlparse.urlparse(redirect_response)
                auth_code = urlparse.parse_qs(parsed.query)['code'][0]
            else:
                auth_code = redirect_response
            
            print(f"🔑 Using authorization code: {auth_code[:10]}...")
            
            # Exchange code for credentials
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # Safe save with corruption prevention
            if self.token_manager.safe_write(creds):
                self.service = self._build_service()
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Failed to save credentials")
                return False
                
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def health_check(self):
        """Perform health check on authentication"""
        try:
            if not self.service:
                return {'status': 'error', 'message': 'No service available'}
            
            # Test API call
            self.service.files().list(pageSize=1, fields="files(id, name)").execute()
            
            # Check token file integrity
            creds = self.token_manager.safe_read()
            if not creds:
                return {'status': 'warning', 'message': 'Token file issues detected'}
            
            # Check if token is close to expiry
            if hasattr(creds, 'expiry') and creds.expiry:
                import datetime
                time_until_expiry = creds.expiry - datetime.datetime.utcnow()
                if time_until_expiry.total_seconds() < 300:  # Less than 5 minutes
                    return {'status': 'warning', 'message': 'Token expires soon'}
            
            return {'status': 'healthy', 'message': 'All systems operational'}
            
        except Exception as e:
            return {'status': 'error', 'message': f'Health check failed: {e}'}
    
    def is_authenticated(self):
        """Check if properly authenticated"""
        return self.service is not None
    
    
    def update_file_description(self, file_id: str, description: str) -> bool:
        """Update file description/metadata"""
        if not self.service:
            return False
            
        try:
            file_metadata = {'description': description}
            self.service.files().update(
                fileId=file_id,
                body=file_metadata
            ).execute()
            
            #print(f"Successfully updated description for file {file_id}")
            return True
        except Exception as e:
            print(f"Error updating file description {file_id}: {e}")
            return False
    
    def move_file(self, file_id: str, new_parent_id: str, old_parent_id: str = None) -> bool:
        """Move a file to a different folder"""
        if not self.service:
            return False
            
        try:
            # Get current parents if not provided
            if not old_parent_id:
                file = self.service.files().get(fileId=file_id, fields='parents').execute()
                old_parent_id = ','.join(file.get('parents', []))
            
            # Move the file
            self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=old_parent_id,
                fields='id, parents'
            ).execute()
            
            #print(f"Successfully moved file {file_id} to folder {new_parent_id}")
            return True
        except Exception as e:
            print(f"Error moving file {file_id}: {e}")
            return False
    
    def _get_direct_image_url(self, file_id: str) -> str:
        """Convert Google Drive file ID to proxy URL for authenticated access"""
        # Use our proxy endpoint instead of direct Google Drive URLs
        return f"/api/drive-thumbnail/{file_id}"
    
    def upload_vehicle_photos(self, company, unite_id, files):
        """Upload photos for a specific vehicle to user's own Google Drive - returns Google Drive file info only"""
        # Create path directly in Google Drive root: BDM/BDM/{unite_id}/Photos
        path_parts = [company, company, str(unite_id), 'Photos']
        
        # Create folder structure in user's own Google Drive (starting from root)
        folder_id = self.create_folder_path(path_parts)
        
        if not folder_id:
            return {'success': False, 'error': 'Failed to create folder structure'}
        
        uploaded_files = []
        
        for file in files:
            if file and file.filename:
                # Read file content
                file.seek(0)
                file_content = file.read()
                
                # Determine MIME type
                mime_type = file.content_type or 'image/jpeg'
                
                # Upload file
                result = self.upload_file(file_content, file.filename, folder_id, mime_type)
                
                if result:
                    uploaded_files.append(result)
                else:
                    print(f"Failed to upload {file.filename}")
        
        return {
            'success': True,
            'uploaded_files': uploaded_files,
            'folder_id': folder_id,
            'path': '/'.join(path_parts),
            'owner': 'user_account'  # Indicate this is owned by user
        }
    
    def batch_rename_files(self, file_operations: List[Dict]) -> Dict:
        """Batch rename multiple files"""
        if not self.service:
            return {'success': False, 'error': 'No Google Drive service available'}
        
        results = {
            'success': True,
            'renamed_files': [],
            'failed_files': [],
            'total_operations': len(file_operations)
        }
        
        for operation in file_operations:
            file_id = operation.get('file_id')
            new_name = operation.get('new_name')
            old_name = operation.get('old_name', 'Unknown')
            
            if not file_id or not new_name:
                results['failed_files'].append({
                    'file_id': file_id,
                    'old_name': old_name,
                    'error': 'Missing file_id or new_name'
                })
                continue
            
            if self.rename_file(file_id, new_name):
                results['renamed_files'].append({
                    'file_id': file_id,
                    'old_name': old_name,
                    'new_name': new_name
                })
            else:
                results['failed_files'].append({
                    'file_id': file_id,
                    'old_name': old_name,
                    'new_name': new_name,
                    'error': 'Rename operation failed'
                })
        
        if results['failed_files']:
            results['success'] = len(results['renamed_files']) > 0
        
        return results

    def batch_create_files(self, filenames: List[str], parent_id: str) -> bool:
        """
        Creates multiple blank text files in a single batch request for high performance.
        """
        if not self.service:
            return False

        try:
            batch = self.service.new_batch_http_request()
            
            def callback(request_id, response, exception):
                if exception:
                    # Handle error
                    print(f"Error creating file in batch request {request_id}: {exception}")
            
            for name in filenames:
                file_metadata = {
                    'name': name,
                    'mimeType': 'text/plain',
                    'parents': [parent_id]
                }

                batch.add(self.service.files().create(body=file_metadata), callback=callback)
            
            batch.execute()
            print(f"Successfully processed batch creation for {len(filenames)} files in folder {parent_id}.")
            return True
        except Exception as e:
            print(f"Error during batch file creation: {e}")
            return False

    def get_file_content_as_text(self, file_id: str) -> Optional[str]:
        """Get text content from a Google Drive file"""
        if not self.service:
            return None
        
        try:
            # Get file metadata first to check MIME type
            file_metadata = self.service.files().get(fileId=file_id, fields='mimeType,name').execute()
            mime_type = file_metadata.get('mimeType', '')
            file_name = file_metadata.get('name', '')
            
            # Handle different file types
            if mime_type == 'application/vnd.google-apps.document':
                # Google Docs - export as plain text
                content = self.service.files().export(fileId=file_id, mimeType='text/plain').execute()
                return content.decode('utf-8')
            elif mime_type.startswith('text/') or file_name.endswith(('.txt', '.log', '.md', '.csv')):
                # Plain text files
                content = self.service.files().get_media(fileId=file_id).execute()
                return content.decode('utf-8')
            elif mime_type == 'application/pdf':
                # For PDF, we'll return a message since we can't easily extract text without additional libraries
                return "[PDF File - Content preview not available. Please download to view.]"
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                            'application/msword']:
                # Word documents - would need python-docx library for full support
                return "[Word Document - Content preview not available. Please download to view.]"
            else:
                return f"[{mime_type} - Content preview not supported]"
                
        except Exception as e:
            print(f"Error getting file content {file_id}: {e}")
            return f"[Error reading file: {str(e)}]"

    def update_text_file_content(self, file_id: str, new_content: str) -> bool:
        """Update the content of a text file in Google Drive"""
        if not self.service:
            return False
        
        try:
            # Get file metadata to check if it's editable
            file_metadata = self.service.files().get(fileId=file_id, fields='mimeType,name').execute()
            mime_type = file_metadata.get('mimeType', '')
            
            if mime_type.startswith('text/') or mime_type == 'application/vnd.google-apps.document':
                # Convert content to bytes
                content_bytes = new_content.encode('utf-8')
                media = MediaIoBaseUpload(
                    BytesIO(content_bytes),
                    mimetype='text/plain' if mime_type.startswith('text/') else mime_type
                )
                
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                
                print(f"Successfully updated content for file {file_id}")
                return True
            else:
                print(f"File type {mime_type} is not editable as text")
                return False
                
        except Exception as e:
            print(f"Error updating file content {file_id}: {e}")
            return False

    def get_folder_info(self, folder_id):
        """Get folder information"""
        if not self.service:
            return None
            
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields='id, name, webViewLink, parents'
            ).execute()
            
            return {
                'id': folder.get('id'),
                'name': folder.get('name'),
                'link': folder.get('webViewLink'),
                'parents': folder.get('parents', [])
            }
        except Exception as e:
            print(f"Error getting folder info {folder_id}: {e}")
            return None