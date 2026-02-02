#!/usr/bin/env python3
"""
Download M3-Bench-web YouTube videos listed in data/annotations/web.json.

Usage:
    # Install yt-dlp first: pip install yt-dlp
    # From project root:
    python scripts/download_videos.py
    python scripts/download_videos.py --workers 8          # 8 parallel downloads
    python scripts/download_videos.py --force               # re-download existing
    python scripts/download_videos.py --dry-run            # print URLs only
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def download_one(video_id: str, video_url: str, video_path: str, force: bool = False) -> tuple[str, bool, Optional[str]]:
    """Download a single video. Returns (video_id, success, error_message)."""
    if os.path.exists(video_path) and not force:
        return (video_id, True, None)
    out_dir = os.path.dirname(video_path)
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", video_path,
        "--no-overwrites" if not force else "--force-overwrites",
        "--quiet",
        "--no-warnings",
        video_url,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            return (video_id, False, result.stderr or result.stdout or f"exit code {result.returncode}")
        return (video_id, True, None)
    except subprocess.TimeoutExpired:
        return (video_id, False, "timeout")
    except Exception as e:
        return (video_id, False, str(e))


def main():
    parser = argparse.ArgumentParser(description="Download M3-Bench-web videos from YouTube using web.json")
    parser.add_argument(
        "--annotations",
        default="data/annotations/web.json",
        help="Path to web.json (default: data/annotations/web.json)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel downloads (default: 4)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if file already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print video URLs and output paths, do not download",
    )
    args = parser.parse_args()

    if not os.path.exists(args.annotations):
        print(f"Error: annotations file not found: {args.annotations}", file=sys.stderr)
        sys.exit(1)

    with open(args.annotations) as f:
        data = json.load(f)

    items = [
        (vid, entry["video_url"], entry["video_path"])
        for vid, entry in data.items()
        if "video_url" in entry and "video_path" in entry
    ]
    print(f"Found {len(items)} videos in {args.annotations}")

    if args.dry_run:
        for vid, url, path in items[:5]:
            print(f"  {vid}: {url} -> {path}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        return

    # Check yt-dlp is available
    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: yt-dlp not found. Install with: pip install yt-dlp", file=sys.stderr)
        sys.exit(1)

    failed = []
    iterator = items
    if tqdm:
        iterator = tqdm(items, desc="Downloading", unit="video")

    if args.workers <= 1:
        for vid, url, path in iterator:
            _, ok, err = download_one(vid, url, path, force=args.force)
            if not ok:
                failed.append((vid, err))
                if tqdm:
                    tqdm.write(f"Failed {vid}: {err}")
                else:
                    print(f"Failed {vid}: {err}", file=sys.stderr)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(download_one, vid, url, path, args.force): vid
                for vid, url, path in items
            }
            for fut in as_completed(futures):
                vid = futures[fut]
                try:
                    _, ok, err = fut.result()
                    if not ok:
                        failed.append((vid, err))
                        if tqdm:
                            tqdm.write(f"Failed {vid}: {err}")
                        else:
                            print(f"Failed {vid}: {err}", file=sys.stderr)
                except Exception as e:
                    failed.append((vid, str(e)))
                    if tqdm:
                        tqdm.write(f"Failed {vid}: {e}")
                    else:
                        print(f"Failed {vid}: {e}", file=sys.stderr)

    if failed:
        fail_log = "data/download_web_failed.txt"
        os.makedirs(os.path.dirname(fail_log) or ".", exist_ok=True)
        with open(fail_log, "w") as f:
            for vid, err in failed:
                f.write(f"{vid}\t{err}\n")
        print(f"\n{len(failed)} download(s) failed. IDs and errors written to {fail_log}")
    else:
        print("\nAll downloads completed successfully.")


if __name__ == "__main__":
    main()
