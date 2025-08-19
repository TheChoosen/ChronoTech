from contextlib import contextmanager
import fcntl
import os
import pickle
import shutil
import tempfile
import threading
import time


class SafeTokenManager:
    """Thread-safe token manager with corruption prevention"""
    
    def __init__(self, token_file='token.pickle'):
        self.token_file = token_file
        self.lock_file = f"{token_file}.lock"
        self._lock = threading.RLock()
    
    @contextmanager
    def file_lock(self):
        """File-level locking to prevent concurrent access"""
        lock_fd = None
        try:
            # Create lock file if it doesn't exist
            lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
            
            # Acquire exclusive lock
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield
            
        finally:
            if lock_fd:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                    os.unlink(self.lock_file)
                except:
                    pass
    
    def safe_write(self, credentials):
        """Atomically write credentials to prevent corruption"""
        with self._lock:
            with self.file_lock():
                # Create backup of existing token
                backup_file = f"{self.token_file}.backup"
                if os.path.exists(self.token_file):
                    try:
                        shutil.copy2(self.token_file, backup_file)
                    except Exception as e:
                        print(f"Warning: Could not create backup: {e}")
                
                # Write to temporary file first
                temp_fd, temp_path = tempfile.mkstemp(
                    suffix='.tmp', 
                    prefix='token_', 
                    dir=os.path.dirname(self.token_file) or '.'
                )
                
                try:
                    with os.fdopen(temp_fd, 'wb') as temp_file:
                        pickle.dump(credentials, temp_file)
                        temp_file.flush()
                        os.fsync(temp_file.fileno())  # Force write to disk
                    
                    # Verify the written file
                    with open(temp_path, 'rb') as verify_file:
                        pickle.load(verify_file)  # This will raise exception if corrupted
                    
                    # Atomic move to final location
                    if os.name == 'nt':  # Windows
                        if os.path.exists(self.token_file):
                            os.unlink(self.token_file)
                        shutil.move(temp_path, self.token_file)
                    else:  # Unix/Linux
                        os.rename(temp_path, self.token_file)
                    
                    print(f"✅ Token saved safely to {self.token_file}")
                    
                    # Remove backup after successful write
                    if os.path.exists(backup_file):
                        try:
                            os.unlink(backup_file)
                        except:
                            pass
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Error during safe write: {e}")
                    
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    # Restore from backup if available
                    if os.path.exists(backup_file) and not os.path.exists(self.token_file):
                        try:
                            shutil.move(backup_file, self.token_file)
                            print("🔄 Restored from backup")
                        except Exception as restore_error:
                            print(f"❌ Could not restore backup: {restore_error}")
                    
                    return False
    
    def safe_read(self):
        """Safely read credentials with corruption detection"""
        with self._lock:
            if not os.path.exists(self.token_file):
                return None
            
            # Check if file is empty or too small
            try:
                file_size = os.path.getsize(self.token_file)
                if file_size < 10:  # Pickle files are never this small
                    print(f"⚠️  Token file suspiciously small ({file_size} bytes), likely corrupted")
                    return None
            except OSError:
                return None
            
            with self.file_lock():
                try:
                    with open(self.token_file, 'rb') as token:
                        credentials = pickle.load(token)
                    
                    # Validate credentials object
                    if not hasattr(credentials, 'valid') or not hasattr(credentials, 'token'):
                        print("⚠️  Token file contains invalid credentials object")
                        return None
                    
                    return credentials
                    
                except (pickle.UnpicklingError, EOFError, OSError) as e:
                    print(f"🔍 Token file corrupted: {e}")
                    self._handle_corruption()
                    return None
                except Exception as e:
                    print(f"🔍 Unexpected error reading token: {e}")
                    return None
    
    def _handle_corruption(self):
        """Handle corrupted token file"""
        timestamp = int(time.time())
        corrupted_file = f"{self.token_file}.corrupted.{timestamp}"
        backup_file = f"{self.token_file}.backup"
        
        try:
            # Move corrupted file
            if os.path.exists(self.token_file):
                os.rename(self.token_file, corrupted_file)
                print(f"🗂️  Moved corrupted token to: {corrupted_file}")
            
            # Try to restore from backup
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'rb') as f:
                        pickle.load(f)  # Verify backup is valid
                    shutil.copy2(backup_file, self.token_file)
                    print("🔄 Restored valid backup")
                    return True
                except:
                    print("⚠️  Backup is also corrupted")
            
        except Exception as e:
            print(f"❌ Error handling corruption: {e}")
        
        return False
