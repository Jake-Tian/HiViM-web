"""Generate subtitles using Whisper and save to SRT file."""

import whisper
import tempfile
import subprocess
import os
import time
from pathlib import Path


def extract_audio_from_video(video_path, output_audio_path=None):
    """Extract audio from video file using ffmpeg."""
    if output_audio_path is None:
        output_audio_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    conda_prefix = os.environ.get('CONDA_PREFIX', '')
    if conda_prefix:
        conda_ffmpeg = os.path.join(conda_prefix, 'bin', 'ffmpeg')
        ffmpeg_cmd = conda_ffmpeg if os.path.exists(conda_ffmpeg) else 'ffmpeg'
    else:
        ffmpeg_cmd = 'ffmpeg'
    
    cmd = [
        ffmpeg_cmd, '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-f', 'wav', '-y',
        output_audio_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        stderr_lower = result.stderr.lower() if result.stderr else ''
        if 'no audio streams' in stderr_lower or 'stream map' in stderr_lower:
            raise ValueError("Video has no audio stream. Cannot generate subtitles.")
        raise ValueError(f"FFmpeg failed to extract audio: {result.stderr}")
    
    if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) == 0:
        raise ValueError("Failed to extract audio: output file is empty or missing")
    
    return output_audio_path


def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_whisper(segments, output_path):
    """Generate SRT file from Whisper segments."""
    with open(output_path, 'w', encoding='utf-8') as f:
        idx = 1
        for segment in segments:
            text = segment.get('text', '').strip()
            if not text:
                continue
            
            f.write(f"{idx}\n")
            f.write(f"{seconds_to_srt_time(segment['start'])} --> {seconds_to_srt_time(segment['end'])}\n")
            f.write(f"{text}\n\n")
            idx += 1
    
    print(f"✓ SRT file saved to: {output_path}")


def extract_subtitles_from_video(video_path, model_name="tiny.en"):
    """
    Extract subtitles directly from video using Whisper without saving to file.

    Args:
        video_path: Path to input video (string or Path object)
        model_name: Whisper model to use (default: "tiny.en")

    Returns:
        List of subtitle segments with 'start', 'end', and 'text' keys
    """
    video_path = Path(video_path)
    # If path doesn't exist, try relative to script directory
    if not video_path.exists():
        script_dir = Path(__file__).parent.parent  # Go up from preprocessing/ to project root
        alt_path = script_dir / video_path
        if alt_path.exists():
            video_path = alt_path
        else:
            raise FileNotFoundError(f"Video file not found: {video_path} (also tried: {alt_path})")

    print(f"Loading Whisper model: {model_name}...")
    model = whisper.load_model(model_name)

    print("Extracting audio from video...")
    audio_path = None
    try:
        audio_path = extract_audio_from_video(str(video_path))

        print("Transcribing audio...")
        result = model.transcribe(audio_path, language="en", fp16=False)

        # Convert Whisper segments to subtitle format
        subtitles = []
        for segment in result["segments"]:
            text = segment.get('text', '').strip()
            if text:  # Only add non-empty segments
                subtitles.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': text
                })

        print(f"Extracted {len(subtitles)} subtitle segments")
        return subtitles

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass


def generate_subtitles_with_whisper(video_path, output_srt_path=None, model_name="small.en"):
    """Generate subtitles from video using Whisper."""
    video_path = Path(video_path)
    # If path doesn't exist, try relative to script directory
    if not video_path.exists():
        script_dir = Path(__file__).parent.parent  # Go up from preprocessing/ to project root
        alt_path = script_dir / video_path
        if alt_path.exists():
            video_path = alt_path
        else:
            raise FileNotFoundError(f"Video file not found: {video_path} (also tried: {alt_path})")

    if output_srt_path is None:
        # Save to data/subtitles/web directory
        subtitles_dir = Path("data/subtitles/web")
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        # Use video filename (without path) for subtitle filename
        video_name = video_path.stem
        output_srt_path = subtitles_dir / f"{video_name}.srt"
    else:
        output_srt_path = Path(output_srt_path)
        # Ensure parent directory exists
        output_srt_path.parent.mkdir(parents=True, exist_ok=True)

    # Get subtitles and save to SRT
    subtitles = extract_subtitles_from_video(video_path, model_name)
    print("Generating SRT file...")
    generate_srt_from_whisper(subtitles, str(output_srt_path))

    return str(output_srt_path)


if __name__ == "__main__":
    video_path = "data/videos/web/Efk3K4epEzg.mp4"
    output_srt_path = "data/subtitles/web/small.srt"
    model_name = "small.en"
    try:
        start_time = time.time()
        output_path = generate_subtitles_with_whisper(video_path, output_srt_path, model_name)
        end_time = time.time()
        print(f"Time taken: {end_time - start_time} seconds")
        print(f"\n✓ Successfully generated subtitles: {output_path}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
