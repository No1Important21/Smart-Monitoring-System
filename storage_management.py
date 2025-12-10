import os

def manage_storage(folder_path, max_files=400):
    """
    Manages storage for a given folder by deleting the oldest file if the file count exceeds max_files.

    :param folder_path: Path to the folder to manage
    :param max_files: Maximum number of files allowed (default: 50)
    """
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return

    # List all files in the folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    if len(files) <= max_files:
        print(f"Folder {folder_path} has {len(files)} files, which is within the limit of {max_files}.")
        return

    # Get modification times and sort files by oldest first
    files_with_mtime = [(f, os.path.getmtime(os.path.join(folder_path, f))) for f in files]
    files_with_mtime.sort(key=lambda x: x[1])  # Sort by mtime (oldest first)

    # Delete oldest files until within limit
    files_to_delete = len(files) - max_files
    for i in range(files_to_delete):
        oldest_file = files_with_mtime[i][0]
        oldest_file_path = os.path.join(folder_path, oldest_file)
        try:
            os.remove(oldest_file_path)
            print(f"Deleted oldest file: {oldest_file_path}")
        except Exception as e:
            print(f"Error deleting file {oldest_file_path}: {e}")

if __name__ == "__main__":
    # Manage both folders
    manage_storage("images/")
    manage_storage("images_processed/")
