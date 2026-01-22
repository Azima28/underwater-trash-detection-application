import os
import time
import shutil
import threading

def delete_file(path):
    """Safe deletion of a file"""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Cleanup: Deleted {path}")
    except Exception as e:
        print(f"Cleanup error deleting {path}: {e}")

def clear_folders(folders):
    """Empty the specified folders"""
    for folder in folders:
        if os.path.exists(folder):
            print(f"Cleanup: Clearing folder {folder}...")
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

def cleanup_old_files(folders, max_age_seconds=600):
    """Delete files older than max_age_seconds in specified folders"""
    now = time.time()
    for folder in folders:
        if not os.path.exists(folder):
            continue
        
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.getmtime(file_path) < now - max_age_seconds:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        print(f"Cleanup: Removed old file {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"Cleanup: Removed old directory {file_path}")
            except Exception as e:
                print(f"Cleanup error for {file_path}: {e}")

def start_cleanup_worker(folders, interval=300, max_age=900):
    """Start a background thread that periodically cleans up folders"""
    def worker():
        while True:
            print("Cleanup Worker: Running periodic cleanup...")
            cleanup_old_files(folders, max_age)
            time.sleep(interval)
            
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
