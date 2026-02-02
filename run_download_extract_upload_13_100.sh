# Usage: bash run_download_extract_upload_13_100.sh 2>&1 | tee log.txt
#!/usr/bin/env bash
set -euo pipefail

# Download missing videos, extract frames, and upload frames to HF.
# Targets the 5 missing video folders from the first 100 list.


ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

REPO_ID="JakeTian/M3-web"
export HF_HUB_UPLOAD_TIMEOUT=600
export HF_HUB_DOWNLOAD_TIMEOUT=600

if [[ ! -f "data/web.json" ]]; then
  echo "✗ Error: data/web.json not found."
  exit 1
fi

if ! command -v hf >/dev/null 2>&1; then
  echo "✗ Error: huggingface-cli (hf) not found. Install with:"
  echo "  pip install -U huggingface_hub"
  exit 1
fi

VIDEOS=(
  "eeumL7Fz-8M"
  "aO-wNDaRBkk"
  "-wzFQKrEDaM"
)

if [[ ${#VIDEOS[@]} -eq 0 ]]; then
  echo "✗ Error: No videos configured."
  exit 1
fi

echo "Processing ${#VIDEOS[@]} missing videos."

for video in "${VIDEOS[@]}"; do
  echo ""
  echo "============================================================"
  echo "Processing video: ${video}"
  echo "============================================================"

  # Step 1: Download video (skip if already present)
  if [[ -f "data/videos/${video}.mp4" && -s "data/videos/${video}.mp4" ]]; then
    echo "✓ Video already exists, skipping download: data/videos/${video}.mp4"
  else
    if ! python3 preprocessing/download_web_videos.py "$video"; then
      echo "✗ Download failed for ${video}"
      continue
    fi
  fi

  # Step 2: Add subtitles + extract frames (skip if already extracted)
  if [[ -d "data/frames/${video}" ]] && compgen -G "data/frames/${video}/*/*.jpg" > /dev/null; then
    echo "✓ Frames already exist, skipping extraction: data/frames/${video}"
  else
    if ! python3 preprocessing/add_subtitles_and_extract_frames.py "$video"; then
      echo "✗ Frame extraction failed for ${video}"
      continue
    fi
  fi

  # Step 3: Upload frames only (one video folder at a time)
  if [[ -d "data/frames/${video}" ]]; then
    upload_ok=0
    for attempt in 1 2 3; do
      echo "Uploading frames for ${video} (attempt ${attempt}/3)..."
      if python3 - <<PY
from huggingface_hub import HfApi
from pathlib import Path

repo_id = "${REPO_ID}"
folder_path = Path("data/frames/${video}")
api = HfApi()
api.upload_folder(
    repo_id=repo_id,
    repo_type="dataset",
    folder_path=str(folder_path),
    path_in_repo="${video}",
    commit_message=f"Upload frames for ${video}",
)
PY
      then
        upload_ok=1
        break
      else
        echo "⚠ Upload attempt ${attempt} failed for ${video}"
        sleep 10
      fi
    done
    if [[ "$upload_ok" -ne 1 ]]; then
      echo "✗ Upload failed for ${video}"
      continue
    fi
    echo "✓ Uploaded frames for ${video}"
  else
    echo "✗ Frames directory not found: data/frames/${video}"
    continue
  fi
done

echo ""
echo "Done."
