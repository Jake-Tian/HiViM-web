#!/usr/bin/env bash
set -euo pipefail

# Run full pipeline sequentially per video to conserve storage:
# 1) Download MP4
# 2) Add subtitles + extract frames
# 3) Build graph memory
# 4) Answer questions and update results.json
# 5) Cleanup MP4 and frames

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

cleanup_video() {
  local video_name="$1"
  rm -f "data/videos/${video_name}.mp4"
  rm -rf "data/frames/${video_name}"
}

if [[ "$#" -gt 0 ]]; then
  VIDEOS=("$@")
else
  if [[ ! -f "video_list.txt" ]]; then
    echo "video_list.txt not found. Pass video names as arguments."
    exit 1
  fi
  mapfile -t VIDEOS < "video_list.txt"
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
  if ! python3 preprocessing/download_hf_videos.py "$video"; then
    echo "✗ Download failed for ${video}"
    cleanup_video "$video"
    continue
  fi

  # Step 2: Add subtitles + extract frames
  if [[ ! -f "data/subtitles/robot/${video}.srt" ]]; then
    echo "✗ Subtitle file missing for ${video}: data/subtitles/robot/${video}.srt"
    cleanup_video "$video"
    continue
  fi

  if ! python3 preprocessing/add_subtitles_and_extract_frames.py "$video"; then
    echo "✗ Frame extraction failed for ${video}"
    cleanup_video "$video"
    continue
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

  # Step 4: Answer questions and update results.json
  if python3 - <<PY
import json
import pickle
from pathlib import Path

from reason import reason
from reason_full import evaluate_answer

video_name = "${video}"

questions_path = Path("data/questions/robot.json")
results_path = Path("data/results/results.json")
graph_path = Path("data/semantic_memory") / f"{video_name}.pkl"

if not graph_path.exists():
    raise SystemExit(f"Graph file not found: {graph_path}")

with open(graph_path, "rb") as f:
    graph = pickle.load(f)

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

for qa in video_questions:
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

        existing_results[question_id] = reason_result
    except Exception as e:
        existing_results[question_id] = {
            "error": str(e),
            "video_name": video_name,
            "question": question,
            "ground_truth_answer": ground_truth,
            "reasoning": reasoning,
            "timestamp": timestamp,
            "type": qa_type,
            "before_clip": before_clip,
            "evaluator_correct": False,
        }

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
  cleanup_video "$video"
  echo "✓ Cleaned up video and frames for ${video}"
done

echo ""
echo "All videos processed."
