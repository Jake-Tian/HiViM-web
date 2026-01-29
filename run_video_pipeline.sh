#!/usr/bin/env bash
set -euo pipefail

# ./run_video_pipeline.sh --start 1 --end 20 2>&1 | tee log.txt
# Run full pipeline sequentially per video to conserve storage:
# 1) Read web.json to get video list
# 2) Download MP4
# 3) Add subtitles + extract frames (using Whisper)
# 4) Build graph memory
# 5) Answer questions and update results.json
# 6) Cleanup MP4 and frames

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

cleanup_video() {
  local video_name="$1"
  rm -f "data/videos/${video_name}.mp4"
  rm -rf "data/frames/${video_name}"
}

# Parse command-line arguments
LIMIT=""
START=""
END=""
VIDEO_ARGS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --start)
      START="$2"
      shift 2
      ;;
    --end)
      END="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS] [VIDEO_IDS...]"
      echo ""
      echo "Options:"
      echo "  --limit N          Process first N videos from web.json"
      echo "  --start N --end M  Process videos from index N to M (1-indexed)"
      echo "  VIDEO_IDS...       Specific video IDs to process"
      echo ""
      echo "Examples:"
      echo "  $0 --limit 100                    # Process first 100 videos"
      echo "  $0 --start 1 --end 100            # Process videos 1-100"
      echo "  $0 Efk3K4epEzg ABC123xyz          # Process specific videos"
      exit 0
      ;;
    *)
      VIDEO_ARGS+=("$1")
      shift
      ;;
  esac
done

# Step 0: Read web.json to get video list
if [[ ${#VIDEO_ARGS[@]} -gt 0 ]]; then
  # Video IDs provided as arguments
  VIDEOS=("${VIDEO_ARGS[@]}")
else
  # Read from web.json
  if [[ ! -f "data/web.json" ]]; then
    echo "✗ Error: data/web.json not found. Pass video IDs as arguments or ensure web.json exists."
    exit 1
  fi
  
  echo "Reading video list from web.json..."
  ALL_VIDEOS=($(python3 -c "
import json
with open('data/web.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(' '.join(data.keys()))
"))
  
  if [[ ${#ALL_VIDEOS[@]} -eq 0 ]]; then
    echo "✗ Error: No videos found in web.json"
    exit 1
  fi
  
  echo "Found ${#ALL_VIDEOS[@]} video(s) in web.json"
  
  # Apply filters
  if [[ -n "$LIMIT" ]]; then
    # Limit to first N videos
    VIDEOS=("${ALL_VIDEOS[@]:0:$LIMIT}")
    echo "Processing first $LIMIT video(s) (out of ${#ALL_VIDEOS[@]})"
  elif [[ -n "$START" && -n "$END" ]]; then
    # Process range (convert to 0-indexed)
    START_IDX=$((START - 1))
    if [[ $START_IDX -lt 0 ]]; then
      echo "✗ Error: --start must be >= 1"
      exit 1
    fi
    if [[ $START -gt ${#ALL_VIDEOS[@]} ]]; then
      echo "✗ Error: --start ($START) exceeds total videos (${#ALL_VIDEOS[@]})"
      exit 1
    fi
    if [[ $END -gt ${#ALL_VIDEOS[@]} ]]; then
      echo "⚠ Warning: --end ($END) exceeds total videos (${#ALL_VIDEOS[@]}), using ${#ALL_VIDEOS[@]}"
      END=${#ALL_VIDEOS[@]}
    fi
    if [[ $START -gt $END ]]; then
      echo "✗ Error: --start ($START) must be <= --end ($END)"
      exit 1
    fi
    # Calculate length: if START=1, END=100, we want 100 videos (indices 0-99)
    LENGTH=$((END - START + 1))
    VIDEOS=("${ALL_VIDEOS[@]:$START_IDX:$LENGTH}")
    echo "Processing videos $START-$END (${#VIDEOS[@]} videos, out of ${#ALL_VIDEOS[@]})"
  else
    # Process all videos
    VIDEOS=("${ALL_VIDEOS[@]}")
    echo "Processing all ${#VIDEOS[@]} video(s)"
  fi
fi

for video in "${VIDEOS[@]}"; do
  if [[ -z "$video" ]]; then
    continue
  fi

  echo ""
  echo "============================================================"
  echo "Processing video: ${video}"
  echo "============================================================"

  # Step 1: Download video
  echo ""
  if [[ -f "data/videos/${video}.mp4" && -s "data/videos/${video}.mp4" ]]; then
    echo "Step 1: Video already exists, skipping download: data/videos/${video}.mp4"
  else
    echo "Step 1: Downloading video ${video}..."
    if ! python3 preprocessing/download_web_videos.py "$video"; then
      echo "✗ Download failed for ${video}"
      cleanup_video "$video"
      continue
    fi
    
    if [[ ! -f "data/videos/${video}.mp4" || ! -s "data/videos/${video}.mp4" ]]; then
      echo "✗ Video file not found (or empty) after download: data/videos/${video}.mp4"
      cleanup_video "$video"
      continue
    fi
  fi

  # Step 2: Add subtitles + extract frames (using Whisper)
  echo ""
  if [[ -d "data/frames/${video}" ]] && compgen -G "data/frames/${video}/*/*.jpg" > /dev/null; then
    echo "Step 2: Frames already extracted, skipping: data/frames/${video}"
  else
    echo "Step 2: Extracting subtitles and frames for ${video}..."
    if ! python3 preprocessing/add_subtitles_and_extract_frames.py "$video"; then
      echo "✗ Frame extraction failed for ${video}"
      cleanup_video "$video"
      continue
    fi
    
    if [[ ! -d "data/frames/${video}" ]]; then
      echo "✗ Frames directory not found after extraction: data/frames/${video}"
      cleanup_video "$video"
      continue
    fi
  fi

  # Step 3: Build graph memory
  if python3 - <<PY
from pathlib import Path
from process_full_video import process_full_video

video_name = "${video}"
frames_dir = Path(f"data/frames/{video_name}")
if not frames_dir.exists():
    raise SystemExit(f"Frames directory not found: {frames_dir}")

process_full_video(frames_dir)
print(f"✓ Graph memory built for {video_name}")
PY
  then
    : # success
  else
    echo "✗ Graph processing failed for ${video}"
    cleanup_video "$video"
    continue
  fi

  # Step 4: Answer questions and update results.json (process 2 questions in parallel)
  if python3 - <<PY
import json
import pickle
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from reason import reason
from reason_full import evaluate_answer

video_name = "${video}"

questions_path = Path("data/web.json")
results_path = Path("data/results/results.json")
graph_path = Path("data/semantic_memory") / f"{video_name}.pkl"

if not graph_path.exists():
    raise SystemExit(f"Graph file not found: {graph_path}")

with open(graph_path, "rb") as f:
    graph = pickle.load(f)

# Skip all questions if graph is empty (no nodes and no edges)
if not graph.characters and not graph.objects and not graph.edges:
    print(f"Graph for {video_name} is empty (no nodes and edges). Skipping all questions for this video.")
    video_questions = []
else:
    with open(questions_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)
    video_questions = questions_data.get(video_name, {}).get("qa_list", [])

existing_results = {}
if results_path.exists():
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            existing_results = json.load(f)
    except json.JSONDecodeError:
        existing_results = {}

def process_question(qa):
    """Process a single question and return (question_id, result_dict)"""
    question_id = qa["question_id"]
    question = qa["question"]
    ground_truth = qa["answer"]
    reasoning = qa.get("reasoning", "")
    timestamp = qa.get("timestamp", "")
    qa_type = qa.get("type", [])
    before_clip = qa.get("before_clip", None)

    try:
        reason_result = reason(question, graph, video_name)
        predicted_answer = reason_result.get("final_answer", "")
        is_correct = evaluate_answer(question, ground_truth, predicted_answer)

        reason_result["evaluator_correct"] = is_correct
        reason_result["ground_truth_answer"] = ground_truth
        reason_result["reasoning"] = reasoning
        reason_result["timestamp"] = timestamp
        reason_result["type"] = qa_type
        reason_result["before_clip"] = before_clip

        return (question_id, reason_result)
    except Exception as e:
        return (question_id, {
            "error": str(e),
            "video_name": video_name,
            "question": question,
            "ground_truth_answer": ground_truth,
            "reasoning": reasoning,
            "timestamp": timestamp,
            "type": qa_type,
            "before_clip": before_clip,
            "evaluator_correct": False,
        })

# Process questions in parallel (2 at a time)
new_results = {}
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(process_question, qa): qa for qa in video_questions}
    
    completed = 0
    for future in as_completed(futures):
        question_id, result = future.result()
        new_results[question_id] = result
        completed += 1
        if completed % 5 == 0:
            print(f"  Processed {completed}/{len(video_questions)} questions...")

# Update existing_results with new results (preserving results from other videos)
existing_results.update(new_results)

results_path.parent.mkdir(parents=True, exist_ok=True)
with open(results_path, "w", encoding="utf-8") as f:
    json.dump(existing_results, f, indent=2, ensure_ascii=False)

print(f"✓ Updated results.json for {video_name} ({len(video_questions)} questions)")
PY
  then
    : # success
  else
    echo "✗ Reasoning failed for ${video}"
    cleanup_video "$video"
    continue
  fi

  # Step 5: Cleanup to free storage
  # cleanup_video "$video"
  # echo "✓ Cleaned up video and frames for ${video}"
done

echo ""
echo "All videos processed."
