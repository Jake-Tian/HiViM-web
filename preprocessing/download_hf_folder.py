#!/usr/bin/env python3
"""
Download a folder from Hugging Face dataset/repository.
Usage: python download_hf_folder.py
"""

from huggingface_hub import snapshot_download
from pathlib import Path

# Configuration
repo_id = "JakeTian/M3-web"
folder_path = ""  # No subfolder in this repo; download from repo root
local_dir = Path("data/frames")  # Where to save locally

# Create local directory if it doesn't exist
local_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading from {repo_id}...")
print(f"Destination: {local_dir}")

try:
    # Download from repo root
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        allow_patterns=None,  # Download everything in the repo
        local_dir=str(local_dir),  # Base directory
        local_dir_use_symlinks=False,
    )
    
    print(f"\n✓ Successfully downloaded to {local_dir}")
except Exception as e:
    print(f"\n✗ Error downloading: {e}")
    print("\nMake sure you have huggingface_hub installed:")
    print("  pip install huggingface_hub")
    print("\nAlternative: Try using the command line:")
    print(f"  huggingface-cli download {repo_id} --repo-type dataset --local-dir {local_dir}")

