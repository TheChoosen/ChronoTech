# API_Documentation/google_drive_helper.py

import os
from .oauth_helper import GoogleDriveOAuthHelper


def get_drive_helper():
    """
    Factory function to get the appropriate Google Drive helper instance.
    - GOOGLE_DRIVE_USE_OAUTH=true: Uses OAuth2 for user-based authentication.
    - Otherwise, tries Service Account credentials.
    - Falls back to the simulator if no credentials are found.
    """
    if os.getenv('GOOGLE_DRIVE_USE_OAUTH', 'false').lower() == 'true':
        #print("Attempting to use OAuth2 Google Drive helper.")
        helper = GoogleDriveOAuthHelper()
        if helper.is_authenticated():
            return helper
        #print("OAuth2 helper not authenticated, falling back.")
    else:
        return None
