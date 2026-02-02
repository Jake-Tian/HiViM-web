#!/usr/bin/env python3
"""
Download YouTube videos from web.json or a URLs file.
Usage:
    python download_web_videos.py                    # Download all videos
    python download_web_videos.py Efk3K4epEzg ...    # Download specific videos
    python download_web_videos.py --urls-file video_url.txt --output-dir /videos
"""

import argparse
import json
import subprocess
import sys
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Configuration
WEB_JSON_PATH = Path("data/web.json")

def check_yt_dlp():
    """Check if yt-dlp is available."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_video(video_id, video_url, local_dir):
    """
    Download a YouTube video using yt-dlp.
    
    Args:
        video_id: YouTube video ID (e.g., "Efk3K4epEzg")
        video_url: Full YouTube URL
    
    Returns:
        bool: True if successful, False otherwise
    """
    local_file = local_dir / f"{video_id}.mp4"
    
    # Check if file already exists (including files with format codes)
    if local_file.exists():
        print(f"✓ {video_id}.mp4 already exists, skipping...")
        return True
    
    # Check for existing files with format codes (e.g., .f399.mp4) that might need renaming
    existing_files = list(local_dir.glob(f"{video_id}.*"))
    if existing_files:
        # Check if there's a merged mp4 file with format code
        mp4_files = [f for f in existing_files if f.suffix == '.mp4' and '.f' in f.stem]
        if mp4_files:
            # Rename the largest mp4 file (likely the merged one) to the expected name
            largest = max(mp4_files, key=lambda f: f.stat().st_size)
            print(f"Found existing file {largest.name}, renaming to {local_file.name}...")
            largest.rename(local_file)
            # Clean up any other partial files (re-list after rename)
            remaining = [f for f in local_dir.glob(f"{video_id}.*") if f != local_file]
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
            existing_files = list(local_dir.glob(f"{video_id}.*"))
            mp4_files = [f for f in existing_files if f.suffix == '.mp4' and f != local_file and f.stat().st_size > 0]
            
            if mp4_files:
                # Use the largest mp4 file (likely the merged one)
                largest = max(mp4_files, key=lambda f: f.stat().st_size)
                print(f"Renaming {largest.name} to {local_file.name}...")
                largest.rename(local_file)
                # Clean up any other partial files
                for f in local_dir.glob(f"{video_id}.*"):
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
            for f in local_dir.glob(f"{video_id}.*"):
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
        for f in local_dir.glob(f"{video_id}.*"):
            f.unlink()
        return False


def load_web_json():
    """Load web.json and return video data."""
    if not WEB_JSON_PATH.exists():
        print(f"✗ Error: {WEB_JSON_PATH} not found")
        sys.exit(1)
    
    with open(WEB_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_video_id(url):
    """Extract YouTube video ID from a URL."""
    parsed = urlparse(url.strip())
    if parsed.netloc in {"www.youtube.com", "youtube.com"} and parsed.path == "/watch":
        query = parse_qs(parsed.query)
        vid = query.get("v", [None])[0]
        if vid:
            return vid
    if parsed.netloc == "youtu.be":
        return parsed.path.lstrip("/") or None
    return None


def main():
    """Main function to download videos."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls-file", help="Path to a file with one URL per line")
    parser.add_argument("--output-dir", default="data/videos", help="Output directory for videos")
    parser.add_argument("video_ids", nargs="*", help="Specific video IDs from web.json")
    args = parser.parse_args()

    if not check_yt_dlp():
        print("✗ Error: yt-dlp is not installed or not in PATH")
        print("Please install it:")
        print("  pip install yt-dlp")
        print("  or: conda install -c conda-forge yt-dlp")
        sys.exit(1)

    local_dir = Path(args.output_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    if args.urls_file:
        urls_path = Path(args.urls_file)
        if not urls_path.exists():
            print(f"✗ Error: URLs file not found: {urls_path}")
            sys.exit(1)
        urls = [line.strip() for line in urls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        videos_to_download = []
        for url in urls:
            vid = extract_video_id(url)
            if not vid:
                print(f"⚠ Warning: Could not extract video id from URL: {url}")
                continue
            videos_to_download.append((vid, url))
        print(f"Downloading {len(videos_to_download)} video(s) to {local_dir}...")
        print()
        success_count = 0
        failed_videos = []
        for video_id, video_url in videos_to_download:
            if download_video(video_id, video_url, local_dir):
                success_count += 1
            else:
                failed_videos.append(video_id)
            print()
    else:
        video_data = load_web_json()
        if args.video_ids:
            videos_to_download = {}
            for vid_id in args.video_ids:
                if vid_id in video_data:
                    videos_to_download[vid_id] = video_data[vid_id]
                else:
                    print(f"⚠ Warning: Video ID '{vid_id}' not found in web.json")
        else:
            videos_to_download = video_data

        print(f"Downloading {len(videos_to_download)} video(s) to {local_dir}...")
        print()
        success_count = 0
        failed_videos = []
        for video_id, video_info in videos_to_download.items():
            video_url = video_info.get("video_url", f"https://www.youtube.com/watch?v={video_id}")
            if download_video(video_id, video_url, local_dir):
                success_count += 1
            else:
                failed_videos.append(video_id)
            print()

    print("=" * 60)
    print("Download Summary:")
    print(f"  Successful: {success_count}/{len(videos_to_download)}")
    if failed_videos:
        print(f"  Failed: {', '.join(failed_videos)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
