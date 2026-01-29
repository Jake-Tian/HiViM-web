"""
Add subtitles to video and extract one frame per second with subtitles.
Saves frames to data/frames/{video_name}/{second}/ directory structure.
python -m preprocessing.add_subtitles_and_extract_frames
"""

import cv2
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import tempfile
import subprocess
import os
from whisper_subtitles import extract_subtitles_from_video


def check_video_codec(video_path: Path) -> str:
    """Check the video codec using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
            '-select_streams', 'v:0', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            if streams:
                codec_name = streams[0].get('codec_name', 'unknown')
                return codec_name.lower()
    except Exception:
        pass
    return 'unknown'


def convert_video_for_compatibility(video_path: Path) -> Path:
    """
    Convert AV1 or other incompatible videos to H.264 for better OpenCV compatibility.

    Returns the path to the converted video (or original if no conversion needed).
    """
    codec = check_video_codec(video_path)

    # Convert AV1 and other potentially problematic codecs
    if codec in ['av1', 'vp8', 'vp9']:
        print(f"Video codec is {codec}, converting to H.264 for better compatibility...")

        # Create temporary file for converted video
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()

        try:
            # Convert to H.264 using FFmpeg
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                '-y', temp_video.name
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Video converted successfully to {temp_video.name}")
                return Path(temp_video.name)
            else:
                print(f"✗ Video conversion failed: {result.stderr}")
                # Clean up failed conversion
                if os.path.exists(temp_video.name):
                    os.unlink(temp_video.name)

        except Exception as e:
            print(f"✗ Video conversion error: {e}")
            if os.path.exists(temp_video.name):
                os.unlink(temp_video.name)

    # Return original path if no conversion needed or conversion failed
    return video_path


def cleanup_temp_video(video_path: Path, original_path: Path):
    """Clean up temporary converted video files."""
    if video_path != original_path and video_path.exists():
        try:
            video_path.unlink()
            print(f"Cleaned up temporary video: {video_path}")
        except Exception:
            pass


def parse_srt_file(srt_path: Path) -> List[Dict[str, any]]:
    """
    Parse SRT subtitle file and return list of subtitle entries.
    
    Args:
        srt_path: Path to .srt file
        
    Returns:
        List of dicts with 'start', 'end', and 'text' keys
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match SRT entries
    # Format: number\nHH:MM:SS,mmm --> HH:MM:SS,mmm\ntext\n
    pattern = r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    subtitles = []
    for match in matches:
        # Extract timestamp components
        start_h, start_m, start_s, start_ms = map(int, match[1:5])
        end_h, end_m, end_s, end_ms = map(int, match[5:9])
        
        # Convert to seconds
        start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000.0
        end_time = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000.0
        
        # Extract text (remove speaker prefix if present, or keep it)
        text = match[9].strip()
        
        subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': text
        })
    
    return subtitles


def srt_time_to_seconds(time_str: str) -> float:
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
    parts = time_str.split(',')
    time_part = parts[0].split(':')
    ms = int(parts[1]) if len(parts) > 1 else 0
    
    hours = int(time_part[0])
    minutes = int(time_part[1])
    seconds = int(time_part[2])
    
    return hours * 3600 + minutes * 60 + seconds + ms / 1000.0


def get_subtitle_at_time(subtitles: List[Dict], time_seconds: float) -> str:
    """Get the active subtitle text at a given time."""
    for sub in subtitles:
        if sub['start'] <= time_seconds <= sub['end']:
            return sub['text']
    return None


def wrap_text(text: str, font, font_scale: float, thickness: int, max_width: int) -> List[str]:
    """
    Wrap text into multiple lines that fit within max_width.
    """
    words = text.split(' ')
    lines = []
    current_line = ''
    
    for word in words:
        test_line = current_line + (' ' if current_line else '') + word
        (line_width, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        
        if line_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text]


def draw_subtitle_on_frame(frame: np.ndarray, subtitle_text: str, 
                          font_size: int = 24, font_color: Tuple[int, int, int] = (255, 255, 255),
                          bg_color: Tuple[int, int, int] = (0, 0, 0),
                          position: str = 'bottom') -> np.ndarray:
    """
    Draw subtitle text on a frame.
    
    Args:
        frame: BGR image array
        subtitle_text: Text to display
        font_size: Font size
        font_color: BGR color tuple for text
        bg_color: BGR color tuple for background
        position: 'bottom' or 'center'
        
    Returns:
        Frame with subtitle drawn
    """
    if not subtitle_text:
        return frame
    
    height, width = frame.shape[:2]
    
    # Font settings
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = font_size / 30.0
    thickness = max(1, int(font_size / 20))
    line_type = cv2.LINE_AA
    
    # Wrap text
    max_text_width = int(width * 0.9)
    text_lines = wrap_text(subtitle_text, font, font_scale, thickness, max_text_width)
    
    # Calculate dimensions
    line_heights = []
    line_widths = []
    for line in text_lines:
        (line_width, line_height), baseline = cv2.getTextSize(line, font, font_scale, thickness)
        line_heights.append(line_height + baseline)
        line_widths.append(line_width)
    
    # Box dimensions
    padding = 10
    line_spacing = 5
    box_width = max(line_widths) + 2 * padding
    box_height = sum(line_heights) + (len(text_lines) - 1) * line_spacing + 2 * padding
    
    # Position
    if position == 'bottom':
        y_pos = height - box_height - 20
    else:  # center
        y_pos = (height - box_height) // 2
    
    x_pos = (width - box_width) // 2
    
    # Draw background
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (x_pos, y_pos),
        (x_pos + box_width, y_pos + box_height),
        bg_color,
        -1
    )
    alpha = 0.7
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    # Draw text
    text_x = x_pos + padding
    current_y = y_pos + padding + line_heights[0] if line_heights else y_pos + padding
    
    for i, line in enumerate(text_lines):
        line_width = line_widths[i]
        line_x = x_pos + (box_width - line_width) // 2
        
        cv2.putText(
            frame,
            line,
            (line_x, current_y),
            font,
            font_scale,
            font_color,
            thickness,
            line_type
        )
        
        if i < len(text_lines) - 1:
            current_y += line_heights[i] + line_spacing
    
    return frame


def process_video_with_subtitles(video_path: Path,
                                  output_frames_dir: Path,
                                  frames_per_second: int = 1,
                                  whisper_model: str = "small.en",
                                  use_whisper: bool = True,
                                  srt_path: Path = None):
    """
    Process video: extract one frame per second and add subtitles.

    Args:
        video_path: Path to input video
        output_frames_dir: Directory to save frames (e.g., data/frames/bedroom_01)
        frames_per_second: Number of frames to extract per second (default: 1)
        whisper_model: Whisper model to use if use_whisper=True (default: "small.en")
        use_whisper: Whether to use Whisper for subtitle extraction (default: True)
        srt_path: Path to SRT subtitle file (only used if use_whisper=False)
    """
    # Extract subtitles
    if use_whisper:
        print("Extracting subtitles using Whisper...")
        subtitles = extract_subtitles_from_video(video_path, whisper_model)
    else:
        if srt_path is None:
            raise ValueError("srt_path must be provided when use_whisper=False")
        print(f"Parsing subtitle file: {srt_path}")
        subtitles = parse_srt_file(srt_path)
        print(f"Found {len(subtitles)} subtitle entries")

    # Convert video if needed for compatibility
    original_video_path = video_path
    video_path = convert_video_for_compatibility(video_path)

    try:
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        print(f"Video opened successfully: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    except Exception as e:
        # Clean up any temp file if video opening failed
        cleanup_temp_video(video_path, original_video_path)
        raise
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0
    
    print(f"Video: {width}x{height}, {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration")
    
    # Create output directory
    output_frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract frames - one per second, grouped into folders of 30 frames each
    # Track which seconds we've already extracted
    extracted_seconds = set()
    frames_saved = 0
    frames_per_folder = 30
    
    print("\nExtracting frames with subtitles...")
    print(f"Grouping frames into folders of {frames_per_folder} frames each")
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps if fps > 0 else 0.0
        current_second = int(current_time)
        
        # Extract one frame per second (only once per second)
        if current_second not in extracted_seconds and current_second >= 0:
            # Get subtitle for this time
            subtitle_text = get_subtitle_at_time(subtitles, current_time)
            
            # Draw subtitle on frame
            frame_with_subtitle = draw_subtitle_on_frame(
                frame.copy(),
                subtitle_text,
                font_size=28,
                font_color=(255, 255, 255),
                bg_color=(0, 0, 0),
                position='bottom'
            )
            
            # Calculate folder number (1-indexed): every 30 frames go into a new folder
            folder_num = (frames_saved // frames_per_folder) + 1
            # Calculate frame number within folder (1-indexed)
            frame_num_in_folder = (frames_saved % frames_per_folder) + 1
            
            # Create directory for this folder (e.g., data/frames/bedroom_01/1/)
            folder_dir = output_frames_dir / str(folder_num)
            folder_dir.mkdir(parents=True, exist_ok=True)
            
            # Save frame (numbered within folder: 1.jpg, 2.jpg, ..., 30.jpg)
            frame_filename = folder_dir / f"{frame_num_in_folder}.jpg"
            cv2.imwrite(str(frame_filename), frame_with_subtitle)
            frames_saved += 1
            extracted_seconds.add(current_second)
            
            if frames_saved % 10 == 0:
                print(f"  Saved {frames_saved} frames (up to {current_second}s, folder {folder_num})")
        
        frame_count += 1
    
    cap.release()

    # Clean up temporary video file if it was converted
    cleanup_temp_video(video_path, original_video_path)

    print(f"\n✓ Extracted {frames_saved} frames to {output_frames_dir}")
    return frames_saved


def main():
    """Process videos and extract frames with subtitles using Whisper.

    Usage:
        python add_subtitles_and_extract_frames.py [video_name1] [video_name2] ... [--model MODEL] [--use-srt]

    Options:
        --model MODEL: Whisper model to use (default: tiny.en)
        --use-srt: Use SRT files instead of Whisper (requires matching .srt files)

    If video names are provided, processes only those videos.
    If no video names are provided, processes all videos in data/videos.

    Examples:
        python add_subtitles_and_extract_frames.py bedroom_01  # Process single video with Whisper
        python add_subtitles_and_extract_frames.py bedroom_01 --model small.en  # Use different model
        python add_subtitles_and_extract_frames.py bedroom_01 --use-srt  # Use SRT file
        python add_subtitles_and_extract_frames.py              # Process all videos
    """
    import sys

    # Parse command line arguments
    args = sys.argv[1:]
    use_whisper = True
    whisper_model = "small.en"

    # Check for flags
    if '--use-srt' in args:
        use_whisper = False
        args.remove('--use-srt')

    if '--model' in args:
        try:
            model_idx = args.index('--model')
            whisper_model = args[model_idx + 1]
            args = args[:model_idx] + args[model_idx + 2:]
        except (IndexError, ValueError):
            print("Error: --model flag requires a model name")
            return

    # Paths
    videos_dir = Path("data/videos")
    subtitles_dir = Path("data/subtitles")
    frames_base_dir = Path("data/frames")
    
    # Get video names from command line arguments (if provided)
    if args:
        # Process specified videos
        video_names = [arg.replace('.mp4', '') for arg in args]
        videos_to_process = []

        for video_name in video_names:
            video_path = videos_dir / f"{video_name}.mp4"
            srt_path = subtitles_dir / f"{video_name}.srt" if not use_whisper else None

            if not video_path.exists():
                print(f"✗ Video file not found: {video_path}")
                continue

            if not use_whisper and not srt_path.exists():
                print(f"✗ Subtitle file not found: {srt_path}")
                continue

            videos_to_process.append((video_name, video_path, srt_path))

        if not videos_to_process:
            print("No valid videos to process.")
            return

        # Process each video
        for video_name, video_path, srt_path in videos_to_process:
            print(f"\n{'='*60}")
            print(f"Processing: {video_name}")
            print(f"{'='*60}")
            print(f"Video: {video_path}")
            if use_whisper:
                print(f"Subtitles: Generated using Whisper ({whisper_model})")
            else:
                print(f"Subtitles: {srt_path}")
            print(f"Output: {frames_base_dir / video_name}")
            print(f"{'='*60}\n")

            try:
                frames_saved = process_video_with_subtitles(
                    video_path=video_path,
                    output_frames_dir=frames_base_dir / video_name,
                    frames_per_second=1,
                    whisper_model=whisper_model,
                    use_whisper=use_whisper,
                    srt_path=srt_path
                )
                print(f"\n✓ Successfully processed {video_name}: {frames_saved} frames saved")
            except Exception as e:
                print(f"\n✗ Error processing {video_name}: {e}")
                import traceback
                traceback.print_exc()
    else:
        # Process all videos
        video_files = list(videos_dir.glob("*.mp4"))
        if not video_files:
            print("No video files found in data/videos/")
            return

        # Find videos to process based on mode
        videos_to_process = []
        for video_file in video_files:
            video_name = video_file.stem
            srt_path = subtitles_dir / f"{video_name}.srt" if not use_whisper else None

            if use_whisper:
                # Always include video for Whisper processing
                videos_to_process.append((video_name, video_file, srt_path))
            else:
                # Only include if SRT file exists
                if srt_path.exists():
                    videos_to_process.append((video_name, video_file, srt_path))
                else:
                    print(f"⚠ Skipping {video_name}: No matching subtitle file found")

        if not videos_to_process:
            if use_whisper:
                print("No videos found in data/videos/")
            else:
                print("No videos with matching subtitle files found.")
            return

        print(f"\n{'='*60}")
        if use_whisper:
            print(f"Found {len(videos_to_process)} video(s) for Whisper processing")
        else:
            print(f"Found {len(videos_to_process)} video(s) with matching subtitles")
        print(f"{'='*60}\n")
        
        # Process each video
        successful = 0
        failed = 0
        
        for i, (video_name, video_path, srt_path) in enumerate(videos_to_process, 1):
            output_frames_dir = frames_base_dir / video_name

            print(f"\n{'='*60}")
            print(f"[{i}/{len(videos_to_process)}] Processing: {video_name}")
            print(f"{'='*60}")
            print(f"Video: {video_path}")
            if use_whisper:
                print(f"Subtitles: Generated using Whisper ({whisper_model})")
            else:
                print(f"Subtitles: {srt_path}")
            print(f"Output: {output_frames_dir}")
            print(f"{'='*60}\n")

            try:
                frames_saved = process_video_with_subtitles(
                    video_path=video_path,
                    output_frames_dir=output_frames_dir,
                    frames_per_second=1,
                    whisper_model=whisper_model,
                    use_whisper=use_whisper,
                    srt_path=srt_path
                )
                print(f"\n✓ Successfully processed {video_name}: {frames_saved} frames saved")
                successful += 1
            except Exception as e:
                print(f"\n✗ Error processing {video_name}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Processing Summary")
        print(f"{'='*60}")
        print(f"Total videos: {len(videos_to_process)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()

