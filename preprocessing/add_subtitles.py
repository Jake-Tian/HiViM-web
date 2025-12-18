from local_voice_diarization import diarize_video_base64
import cv2
import base64
import numpy as np
from pathlib import Path


def wrap_text(text, font, font_scale, thickness, max_width):
    """
    Wrap text into multiple lines that fit within max_width.
    
    Args:
        text: Text to wrap
        font: OpenCV font
        font_scale: Font scale
        thickness: Text thickness
        max_width: Maximum width in pixels
    
    Returns:
        List of text lines
    """
    words = text.split(' ')
    lines = []
    current_line = ''
    
    for word in words:
        # Test if adding this word would exceed max_width
        test_line = current_line + (' ' if current_line else '') + word
        (line_width, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        
        if line_width <= max_width:
            current_line = test_line
        else:
            # Current line is full, start a new line
            if current_line:
                lines.append(current_line)
            current_line = word
    
    # Add the last line
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text]


def add_subtitles_to_video(video_path, diarization_results, output_path, 
                           font_size=24, font_color='white', 
                           bg_color='black', position='bottom',
                           include_speaker=True):
    """
    Add subtitles to video based on diarization results using OpenCV.
    
    Args:
        video_path: Path to input video
        diarization_results: List of dicts with start_time, end_time, speaker, asr
        output_path: Path to save output video
        font_size: Size of subtitle text
        font_color: Color of text ('white', 'black', 'yellow', etc.)
        bg_color: Background color of subtitle box ('black', 'transparent', etc.)
        position: 'bottom' or 'center'
        include_speaker: If True, include speaker label (e.g., "SPEAKER_00: text").
                        If False, only show the transcribed text. Default: True
    """
    # Open input video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video properties: {width}x{height}, {fps:.2f} FPS, {total_frames} frames")
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise ValueError(f"Could not create output video: {output_path}")
    
    # Convert color names to BGR tuples
    color_map = {
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'yellow': (0, 255, 255),
        'red': (0, 0, 255),
        'green': (0, 255, 0),
        'blue': (255, 0, 0),
    }
    text_color_bgr = color_map.get(font_color.lower(), (255, 255, 255))
    bg_color_bgr = color_map.get(bg_color.lower(), (0, 0, 0))
    
    # Font settings
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = font_size / 30.0  # Scale font size appropriately
    thickness = max(1, int(font_size / 20))  # Thickness based on font size
    line_type = cv2.LINE_AA
    
    # Process video frame by frame
    frame_count = 0
    current_time = 0.0
    
    print("\nProcessing video and adding subtitles...")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps if fps > 0 else 0.0
        
        # Find active subtitle for current time
        active_subtitle = None
        for result in diarization_results:
            start_time = mmss_to_seconds(result['start_time'])
            end_time = mmss_to_seconds(result['end_time'])
            
            if start_time <= current_time <= end_time:
                if include_speaker:
                    active_subtitle = f"{result['speaker']}: {result['asr']}"
                else:
                    active_subtitle = result['asr']
                break
        
        # Draw subtitle if active
        if active_subtitle:
            # Wrap text into multiple lines if needed
            # Use 90% of video width as max width for text
            max_text_width = int(width * 0.9)
            text_lines = wrap_text(active_subtitle, font, font_scale, thickness, max_text_width)
            
            # Calculate dimensions for all lines
            line_heights = []
            line_widths = []
            for line in text_lines:
                (line_width, line_height), baseline = cv2.getTextSize(line, font, font_scale, thickness)
                line_heights.append(line_height + baseline)
                line_widths.append(line_width)
            
            # Total box dimensions
            padding = 10
            line_spacing = 5  # Space between lines
            box_width = max(line_widths) + 2 * padding
            box_height = sum(line_heights) + (len(text_lines) - 1) * line_spacing + 2 * padding
            
            # Calculate position
            if position == 'bottom':
                y_pos = height - box_height - 20  # 20px from bottom
            else:  # center
                y_pos = (height - box_height) // 2
            
            x_pos = (width - box_width) // 2  # Centered horizontally
            
            # Draw background rectangle (semi-transparent if not black)
            if bg_color.lower() != 'transparent':
                overlay = frame.copy()
                cv2.rectangle(
                    overlay,
                    (x_pos, y_pos),
                    (x_pos + box_width, y_pos + box_height),
                    bg_color_bgr,
                    -1  # Filled rectangle
                )
                # Blend with original frame for transparency effect
                if bg_color.lower() == 'black':
                    alpha = 0.7  # 70% opacity
                else:
                    alpha = 0.5
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            # Draw each line of text
            text_x = x_pos + padding
            current_y = y_pos + padding + line_heights[0] if line_heights else y_pos + padding
            
            for i, line in enumerate(text_lines):
                # Center each line horizontally within the box
                line_width = line_widths[i]
                line_x = x_pos + (box_width - line_width) // 2
                
                cv2.putText(
                    frame,
                    line,
                    (line_x, current_y),
                    font,
                    font_scale,
                    text_color_bgr,
                    thickness,
                    line_type
                )
                
                # Move to next line
                if i < len(text_lines) - 1:
                    current_y += line_heights[i] + line_spacing
        
        # Write frame
        out.write(frame)
        
        frame_count += 1
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {frame_count}/{total_frames} frames ({progress:.1f}%)")
    
    # Cleanup
    cap.release()
    out.release()
    
    print(f"\n✓ Video with subtitles saved to: {output_path}")


def mmss_to_seconds(time_str):
    """Convert MM:SS format to seconds."""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        # Handle HH:MM:SS format
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        # Assume it's already in seconds
        try:
            return float(time_str)
        except:
            return 0.0


# Example usage
if __name__ == "__main__":
    # 1. Process video to get diarization results
    video_path = "../data/videos/gym_01.mp4"
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    
    base64_video = base64.b64encode(video_bytes)
    results = diarize_video_base64(base64_video)
    
    print(f"Found {len(results)} dialogue segments")
    
    # 2. Add subtitles to video
    output_path = "../data/videos/gym_01_subtitled.mp4"
    
    add_subtitles_to_video(
        video_path=video_path,
        diarization_results=results,
        output_path=output_path,
        font_size=28,
        font_color='white',
        bg_color='black',
        position='bottom', 
        include_speaker=False
    )
