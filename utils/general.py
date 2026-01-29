"""
General utility helpers.
"""
import json
import re
import sys
from pathlib import Path


class Tee:
    """Write to both file and stdout."""
    def __init__(self, file):
        self.file = file
        self.stdout = sys.stdout
        
    def write(self, text):
        self.file.write(text)
        self.file.flush()
        self.stdout.write(text)
        self.stdout.flush()
        
    def flush(self):
        self.file.flush()
        self.stdout.flush()

def strip_code_fences(text: str) -> str:
    """
    Remove surrounding Markdown code fences (``` or ```json) from a string.
    Preserves inner content exactly.
    """
    if text is None:
        return ""

    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the first fence line
        lines = stripped.splitlines()
        if lines:
            # Remove the opening fence (could be ``` or ```json)
            lines = lines[1:]
        # If the last line is a closing fence, drop it
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _repair_json_string(s: str) -> str:
    """
    Apply common repairs to LLM JSON output: extract first {...} or [...] block,
    remove trailing commas before } or ].
    """
    s = s.strip()
    # Extract first complete object: find first { or [, then match balanced braces
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = s.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(s)):
            if s[i] == start_char:
                depth += 1
            elif s[i] == end_char:
                depth -= 1
                if depth == 0:
                    s = s[start : i + 1]
                    break
        else:
            continue
        break
    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def parse_json_with_repair(text: str, *, expect_dict: bool = True):
    """
    Parse JSON from LLM output, with optional repair for common mistakes.
    Returns (parsed, None) on success or (None, error) on failure.
    """
    if not text or not text.strip():
        return None, ValueError("Empty or whitespace-only JSON string")
    text = strip_code_fences(text)
    # Try direct parse first
    try:
        out = json.loads(text)
        if expect_dict and not isinstance(out, dict):
            return None, ValueError(f"Expected a JSON object, got {type(out).__name__}")
        return out, None
    except json.JSONDecodeError:
        pass
    # Try repaired string
    repaired = _repair_json_string(text)
    try:
        out = json.loads(repaired)
        if expect_dict and not isinstance(out, dict):
            return None, ValueError(f"Expected a JSON object, got {type(out).__name__}")
        return out, None
    except json.JSONDecodeError as e:
        return None, e


def update_character_appearance_keys(character_appearance_dict, character_id, character_name):
    """
    Update character appearance dictionary keys from character_id to character_name.
    
    Args:
        character_appearance_dict: Dictionary to update (modified in place)
        character_id: Old key (e.g., "<character_1>")
        character_name: New key (e.g., "<Alice>")
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not isinstance(character_appearance_dict, dict):
        return False
    
    if character_id in character_appearance_dict:
        # If character_name already exists, merge the appearance descriptions
        if character_name in character_appearance_dict:
            # Merge: combine descriptions, removing duplicates
            old_desc = character_appearance_dict[character_id]
            new_desc = character_appearance_dict[character_name]
            # Simple merge: use the longer/more detailed description
            if len(old_desc) > len(new_desc):
                character_appearance_dict[character_name] = old_desc
            # Remove the old key
            del character_appearance_dict[character_id]
        else:
            # Simple rename
            character_appearance_dict[character_name] = character_appearance_dict.pop(character_id)
        return True
    return False

