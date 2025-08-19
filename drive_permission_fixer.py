#!/usr/bin/env python3
"""
drive_permission_fixer.py - Diagnose and fix Google Drive permission issues

This script helps diagnose why file deletion is failing and provides solutions.
"""

import os
import sys
from pathlib import Path

def main():
    print("🔧 Google Drive Permission Diagnosis and Fix")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found in current directory")
        print("\nPlease ensure you have:")
        print("1. Downloaded OAuth2 credentials from Google Cloud Console")
        print("2. Saved them as 'credentials.json' in this directory")
        print("3. Are running this script from your project root")
        return False
    
    print("✅ Found credentials.json")
    
    # Import our helper
    # ...existing code...
    try:
        from drive_helpers.oauth_helper import GoogleDriveOAuthHelper
#
        
        print("\n🔍 Testing current authentication...")
        helper = GoogleDriveOAuthHelper()
        
        if not helper.is_authenticated():
            print("❌ Not authenticated or token invalid")
            print("\n🔄 Would you like to re-authenticate? (y/N): ", end="")
            response = input().strip().lower()
            
            if response in ['y', 'yes']:
                print("\n🚀 Starting re-authentication...")
                if helper.authenticate_user():
                    print("✅ Re-authentication successful!")
                else:
                    print("❌ Re-authentication failed")
                    return False
            else:
                print("ℹ️  Skipping re-authentication")
                return False
        else:
            print("✅ Already authenticated")
        
        # Test file operations
        print("\n🧪 Testing file operations...")
        
        # Test basic service
        health = helper.health_check()
        print(f"Health status: {health['status']} - {health['message']}")
        
        # Test file listing
        try:
            if helper.service:
                results = helper.service.files().list(
                    pageSize=5, 
                    fields="files(id, name, capabilities, owners)"
                ).execute()
                files = results.get('files', [])
                
                print(f"\n📁 Found {len(files)} recent files:")
                for i, file in enumerate(files):
                    print(f"  {i+1}. {file.get('name', 'Unknown')} (ID: {file.get('id')})")
                    capabilities = file.get('capabilities', {})
                    can_delete = capabilities.get('canDelete', False)
                    owners = file.get('owners', [])
                    owner_emails = [owner.get('emailAddress', 'Unknown') for owner in owners]
                    print(f"      Can delete: {can_delete}")
                    print(f"      Owners: {', '.join(owner_emails)}")
                    print()
                
                # Offer to test deletion on a specific file
                if files:
                    print("🗑️  Would you like to test deletion permissions on a specific file? (y/N): ", end="")
                    test_response = input().strip().lower()
                    
                    if test_response in ['y', 'yes']:
                        print("Enter the file ID to test (or press Enter to skip): ", end="")
                        file_id = input().strip()
                        
                        if file_id:
                            print(f"\n🔍 Checking permissions for file: {file_id}")
                            permissions = helper.check_file_permissions(file_id)
                            
                            if 'error' in permissions:
                                print(f"❌ Error: {permissions['error']}")
                            else:
                                print(f"📄 File: {permissions.get('name')}")
                                print(f"🗑️  Can delete: {permissions.get('can_delete')}")
                                print(f"✏️  Can edit: {permissions.get('can_edit')}")
                                print(f"👤 Owners: {', '.join(permissions.get('owners', []))}")
                                
                                if not permissions.get('can_delete'):
                                    print("\n💡 Why this file cannot be deleted:")
                                    print("   • You may not be the owner")
                                    print("   • File permissions don't allow deletion")
                                    print("   • OAuth scopes may be insufficient")
                                    print("\n🔧 Possible solutions:")
                                    print("   1. Re-authenticate with full permissions")
                                    print("   2. Contact file owner for permission")
                                    print("   3. Use 'Move to Trash' instead")
                                else:
                                    print("✅ This file should be deletable!")
                
        except Exception as e:
            print(f"❌ Error testing file operations: {e}")
            return False
        
        print("\n✅ Diagnosis complete!")
        print("\n📋 Summary and Recommendations:")
        print("=" * 40)
        
        if helper.is_authenticated():
            print("✅ Authentication: Working")
        else:
            print("❌ Authentication: Failed")
            
        print("\n🔧 To fix deletion issues:")
        print("1. Ensure you're using the correct OAuth scopes")
        print("2. Re-authenticate if you've changed scopes")
        print("3. Check file ownership and permissions")
        print("4. Consider using 'Move to Trash' for problematic files")
        
        print(f"\n📁 OAuth Scopes currently used:")
        for scope in helper.scopes:
            print(f"   • {scope}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def force_reauth():
    """Force re-authentication by removing token file"""
    print("\n🔄 Force Re-authentication")
    print("-" * 30)
    
    token_files = ['token.pickle', 'token.json']
    removed_any = False
    
    for token_file in token_files:
        if os.path.exists(token_file):
            try:
                # Backup first
                backup_file = f"{token_file}.backup.{int(time.time())}"
                os.rename(token_file, backup_file)
                print(f"🗂️  Moved {token_file} to {backup_file}")
                removed_any = True
            except Exception as e:
                print(f"❌ Could not remove {token_file}: {e}")
    
    if removed_any:
        print("✅ Token files removed. Please run authentication again.")
        return True
    else:
        print("ℹ️  No token files found to remove.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force-reauth":
        import time
        force_reauth()
    else:
        print("🚀 Starting diagnosis...")
        success = main()
        
        if not success:
            print("\n🔄 Would you like to force re-authentication? (y/N): ", end="")
            response = input().strip().lower()
            if response in ['y', 'yes']:
                import time
                force_reauth()
                print("\n🚀 Now run this script again to re-authenticate.")
        
        print("\n🎉 Diagnosis completed!")
        print("💡 Run with --force-reauth to remove token files and start fresh")