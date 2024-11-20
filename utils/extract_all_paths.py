import os
import sys

def extract_all_paths(base_path):
    """
    Extract all paths, filenames, and subdirectories from a given path.

    Args:
        base_path (str): The root directory path to scan.

    Returns:
        None: Prints directories and files.
    """
    result = {
        "directories": [],
        "files": []
    }

    for root, dirs, files in os.walk(base_path):
        # Add directories to the result
        for d in dirs:
            result["directories"].append(os.path.join(root, d))
        
        # Add files to the result
        for f in files:
            result["files"].append(os.path.join(root, f))
    
    # Display results
    print("Directories:")
    for directory in result["directories"]:
        print(directory)

    print("\nFiles:")
    for file in result["files"]:
        print(file)

if __name__ == "__main__":
    # Ensure a directory path is provided as an argument
    if len(sys.argv) < 2:
        print("Usage: python utils\\extract_all_paths.py <directory>")
        sys.exit(1)

    # Get the directory path from the command-line arguments
    directory_path = sys.argv[1]

    # Execute the function
    if os.path.exists(directory_path):
        extract_all_paths(directory_path)
    else:
        print(f"Error: The path '{directory_path}' does not exist.")
