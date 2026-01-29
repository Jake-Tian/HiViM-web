#!/usr/bin/env python3
"""
Download YouTube videos from web.json.
Usage: 
    python download_web_videos.py                    # Download all videos
    python download_web_videos.py Efk3K4epEzg ...    # Download specific videos
"""

import sys
import json
import subprocess
from pathlib import Path

# Configuration
WEB_JSON_PATH = Path("data/web.json")
LOCAL_DIR = Path("data/videos")
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

def check_yt_dlp():
    """Check if yt-dlp is available."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_video(video_id, video_url):
    """
    Download a YouTube video using yt-dlp.
    
    Args:
        video_id: YouTube video ID (e.g., "Efk3K4epEzg")
        video_url: Full YouTube URL
    
    Returns:
        bool: True if successful, False otherwise
    """
    local_file = LOCAL_DIR / f"{video_id}.mp4"
    
    # Check if file already exists (including files with format codes)
    if local_file.exists():
        print(f"✓ {video_id}.mp4 already exists, skipping...")
        return True
    
    # Check for existing files with format codes (e.g., .f399.mp4) that might need renaming
    existing_files = list(LOCAL_DIR.glob(f"{video_id}.*"))
    if existing_files:
        # Check if there's a merged mp4 file with format code
        mp4_files = [f for f in existing_files if f.suffix == '.mp4' and '.f' in f.stem]
        if mp4_files:
            # Rename the largest mp4 file (likely the merged one) to the expected name
            largest = max(mp4_files, key=lambda f: f.stat().st_size)
            print(f"Found existing file {largest.name}, renaming to {local_file.name}...")
            largest.rename(local_file)
            # Clean up any other partial files (re-list after rename)
            remaining = [f for f in LOCAL_DIR.glob(f"{video_id}.*") if f != local_file]
            for f in remaining:
                f.unlink()
            print(f"✓ Using existing file {video_id}.mp4")
            return True
    
    print(f"Downloading {video_id} from {video_url}...")
    
    try:
        # Use the format that works: best video+audio, merge to mp4
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio/best",
            "-o", str(local_file),
            "--merge-output-format", "mp4",
            "--no-playlist",
            "--no-warnings",
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Check for the exact filename first
            if local_file.exists() and local_file.stat().st_size > 0:
                print(f"✓ Successfully downloaded {video_id}.mp4")
                return True
            
            # Check for files with format codes that might have been created
            existing_files = list(LOCAL_DIR.glob(f"{video_id}.*"))
            mp4_files = [f for f in existing_files if f.suffix == '.mp4' and f != local_file and f.stat().st_size > 0]
            
            if mp4_files:
                # Use the largest mp4 file (likely the merged one)
                largest = max(mp4_files, key=lambda f: f.stat().st_size)
                print(f"Renaming {largest.name} to {local_file.name}...")
                largest.rename(local_file)
                # Clean up any other partial files
                for f in LOCAL_DIR.glob(f"{video_id}.*"):
                    if f != local_file:
                        f.unlink()
                print(f"✓ Successfully downloaded {video_id}.mp4")
                return True
            else:
                print(f"✗ Download completed but no valid mp4 file found")
                if result.stderr:
                    print(f"  Error: {result.stderr[:300]}")
                return False
        else:
            print(f"✗ Error downloading {video_id}")
            error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
            if error_msg:
                print(f"  {error_msg}")
            # Clean up partial files
            for f in LOCAL_DIR.glob(f"{video_id}.*"):
                f.unlink()
            return False
            
    except FileNotFoundError:
        print("✗ Error: yt-dlp not found. Please install it:")
        print("  pip install yt-dlp")
        print("  or: conda install -c conda-forge yt-dlp")
        return False
    except Exception as e:
        print(f"✗ Unexpected error downloading {video_id}: {e}")
        # Clean up partial files
        for f in LOCAL_DIR.glob(f"{video_id}.*"):
            f.unlink()
        return False


def load_web_json():
    """Load web.json and return video data."""
    if not WEB_JSON_PATH.exists():
        print(f"✗ Error: {WEB_JSON_PATH} not found")
        sys.exit(1)
    
    with open(WEB_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Main function to download videos."""
    if not check_yt_dlp():
        print("✗ Error: yt-dlp is not installed or not in PATH")
        print("Please install it:")
        print("  pip install yt-dlp")
        print("  or: conda install -c conda-forge yt-dlp")
        sys.exit(1)
    
    video_data = load_web_json()
    
    # Determine which videos to download
    if len(sys.argv) > 1:
        # Specific video IDs provided
        video_ids = sys.argv[1:]
        videos_to_download = {}
        for vid_id in video_ids:
            if vid_id in video_data:
                videos_to_download[vid_id] = video_data[vid_id]
            else:
                print(f"⚠ Warning: Video ID '{vid_id}' not found in web.json")
    else:
        # Download all videos
        videos_to_download = video_data
    
    print(f"Downloading {len(videos_to_download)} video(s) to {LOCAL_DIR}...")
    print()
    
    success_count = 0
    failed_videos = []
    
    # Download videos
    for video_id, video_info in videos_to_download.items():
        video_url = video_info.get("video_url", f"https://www.youtube.com/watch?v={video_id}")
        
        if download_video(video_id, video_url):
            success_count += 1
        else:
            failed_videos.append(video_id)
        print()
    
    # Summary
    print("=" * 60)
    print(f"Download Summary:")
    print(f"  Successful: {success_count}/{len(videos_to_download)}")
    if failed_videos:
        print(f"  Failed: {', '.join(failed_videos)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
