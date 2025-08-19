import os

# Set your base directory and output file
source_folder = '/home/wgoyens/Documents/ChronoTech/'  # ⬅ Replace this with your source folder
output_file = 'combined_output.txt'

# Directories to skip
skip_dirs = {'__pycache__', '.git', 'venv', '.venv', 'env', '.env', '.idea', '.mypy_cache', '.pytest_cache', 'node_modules', 'report'}

# File extensions to skip (optional)
skip_extensions = {'.pyc', '.pyo', '.log', '.pickle'}

with open(output_file, 'w', encoding='utf-8') as outfile:
    # Walk through the directory tree
    for root, dirs, files in os.walk(source_folder):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in files:
            file_path = os.path.join(root, filename)

            # Skip non-files or unwanted extensions
            if not os.path.isfile(file_path) or os.path.splitext(filename)[1] in skip_extensions:
                continue

            # Write a header with the relative file path
            rel_path = os.path.relpath(file_path, source_folder)
            outfile.write(f"\n\n===== FILE: {rel_path} =====\n\n")

            # Read and append content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                    contents = infile.read()
                    outfile.write(contents)
            except Exception as e:
                outfile.write(f"[Could not read {rel_path}: {str(e)}]\n")

print(f"\n✅ All file contents written to: {output_file}")