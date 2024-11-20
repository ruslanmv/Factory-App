import os
import sys

def display_directory_content(base_path):
    """
    Display all paths with directories and files along with their content.

    Args:
        base_path (str): The root directory path to scan.

    Returns:
        None: Prints paths and content.
    """
    for root, dirs, files in os.walk(base_path):
        # Display directories
        for d in dirs:
            dir_path = os.path.join(root, d)
            print(f"Directory: {dir_path}")
        
        # Display files and their content
        for f in files:
            file_path = os.path.join(root, f)
            print(f"\nFile: {file_path}")
            print("-" * 40)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    print(content)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
            print("-" * 40)

if __name__ == "__main__":
    # Ensure a directory path is provided as an argument
    if len(sys.argv) < 2:
        print("Usage: python utils\\extract_all_content.py <directory>")
        sys.exit(1)

    # Get the directory path from the command-line arguments
    directory_path = sys.argv[1]

    # Execute the function
    if os.path.exists(directory_path):
        display_directory_content(directory_path)
    else:
        print(f"Error: The path '{directory_path}' does not exist.")
