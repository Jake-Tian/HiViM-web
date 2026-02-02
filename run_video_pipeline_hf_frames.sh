#!/usr/bin/env bash
set -euo pipefail

# ./run_video_pipeline_hf_frames.sh --start 1 --end 100 2>&1 | tee log.txt
# Pipeline using frames from Hugging Face:
# 1) Read web.json to get video list
# 2) Download frames folder from HF dataset
# 3) Build graph memory
# 4) Answer questions and update results.json
# 5) Cleanup frames

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

REPO_ID="JakeTian/M3-web"
export HF_HUB_DOWNLOAD_TIMEOUT="${HF_HUB_DOWNLOAD_TIMEOUT:-600}"

cleanup_frames() {
  local video_name="$1"
  rm -rf "data/frames/${video_name}"
}

download_frames() {
  local video_name="$1"

  if [[ -d "data/frames/${video_name}" ]] && compgen -G "data/frames/${video_name}/*/*.jpg" > /dev/null; then
    echo "Step 1: Frames already exist, skipping download: data/frames/${video_name}"
    return 0
  fi

  echo "Step 1: Downloading frames for ${video_name} from HF..."
  if ! python3 - <<PY
from pathlib import Path
from huggingface_hub import snapshot_download

repo_id = "${REPO_ID}"
video_name = "${video_name}"
local_dir = Path("data/frames")
local_dir.mkdir(parents=True, exist_ok=True)

snapshot_download(
    repo_id=repo_id,
    repo_type="dataset",
    allow_patterns=[f"{video_name}/**"],
    local_dir=str(local_dir),
    local_dir_use_symlinks=False,
)
print(f"✓ Downloaded frames for {video_name}")
PY
  then
    echo "✗ Frame download failed for ${video_name}"
    cleanup_frames "$video_name"
    return 1
  fi

  if [[ ! -d "data/frames/${video_name}" ]] || ! compgen -G "data/frames/${video_name}/*/*.jpg" > /dev/null; then
    echo "✗ Frames not found after download: data/frames/${video_name}"
    cleanup_frames "$video_name"
    return 1
  fi

  return 0
}

# Parse command-line arguments
LIMIT=""
START=""
END=""
WORKERS=2
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
    --workers)
      WORKERS="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS] [VIDEO_IDS...]"
      echo ""
      echo "Options:"
      echo "  --limit N          Process first N videos from web.json"
      echo "  --start N --end M  Process videos from index N to M (1-indexed)"
      echo "  --workers N        Number of parallel workers (default: 2)"
      echo "  VIDEO_IDS...       Specific video IDs to process"
      echo ""
      echo "Examples:"
      echo "  $0 --limit 100                    # Process first 100 videos"
      echo "  $0 --start 1 --end 100            # Process videos 1-100"
      echo "  $0 Efk3K4epEzg ABC123xyz          # Process specific videos"
      echo "  $0 --workers 4 --limit 20         # Process with 4 workers"
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
  VIDEOS=("${VIDEO_ARGS[@]}")
else
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

  if [[ -n "$LIMIT" ]]; then
    VIDEOS=("${ALL_VIDEOS[@]:0:$LIMIT}")
    echo "Processing first $LIMIT video(s) (out of ${#ALL_VIDEOS[@]})"
  elif [[ -n "$START" && -n "$END" ]]; then
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
    LENGTH=$((END - START + 1))
    VIDEOS=("${ALL_VIDEOS[@]:$START_IDX:$LENGTH}")
    echo "Processing videos $START-$END (${#VIDEOS[@]} videos, out of ${#ALL_VIDEOS[@]})"
  else
    VIDEOS=("${ALL_VIDEOS[@]}")
    echo "Processing all ${#VIDEOS[@]} video(s)"
  fi
fi

worker() {
  local start_idx="$1"

  for ((i=start_idx; i<${#VIDEOS[@]}; i+=WORKERS)); do
    video="${VIDEOS[$i]}"
    if [[ -z "$video" ]]; then
      continue
    fi

    echo ""
    echo "============================================================"
    echo "Processing video: ${video}"
    echo "============================================================"

    # Step 1: Download frames from HF
    if ! download_frames "$video"; then
      continue
    fi

    # Step 2: Build graph memory (frames already downloaded)
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
      cleanup_frames "$video"
      continue
    fi

    # Step 3: Answer questions and update results.json (sequential per video)
    if python3 - <<PY
import json
import pickle
from pathlib import Path
import fcntl

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

if not graph.characters and not graph.objects and not graph.edges:
    print(f"Graph for {video_name} is empty (no nodes and edges). Skipping all questions for this video.")
    video_questions = []
else:
    with open(questions_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)
    video_questions = questions_data.get(video_name, {}).get("qa_list", [])

existing_results = {}

def process_question(qa):
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

new_results = {}
completed = 0
for qa in video_questions:
    question_id, result = process_question(qa)
    new_results[question_id] = result
    completed += 1
    if completed % 5 == 0:
        print(f"  Processed {completed}/{len(video_questions)} questions...")

lock_path = results_path.with_suffix(results_path.suffix + ".lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)
with open(lock_path, "w") as lock_file:
    fcntl.flock(lock_file, fcntl.LOCK_EX)
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
        except json.JSONDecodeError:
            existing_results = {}
    existing_results.update(new_results)

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)
    fcntl.flock(lock_file, fcntl.LOCK_UN)

print(f"✓ Updated results.json for {video_name} ({len(video_questions)} questions)")
PY
    then
      : # success
    else
      echo "✗ Reasoning failed for ${video}"
      cleanup_frames "$video"
      continue
    fi

    # Step 4: Cleanup frames to free storage (after reasoning complete)
    cleanup_frames "$video"
    echo "✓ Cleaned up frames for ${video}"
  done
}

# Run workers in parallel
pids=()
for ((w=0; w<WORKERS; w++)); do
  worker "$w" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do
  wait "$pid" || true
done

echo ""
echo "All videos processed."
