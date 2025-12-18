"""
High-level information extraction methods for HeteroGraph.
Similar to GraphRAG but adapted for video understanding.
"""

from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import json


def extract_character_profile(graph, character_name: str) -> Dict:
    """
    Extract comprehensive profile of a character from their actions and interactions.
    
    Returns:
        {
            "actions": {action: count},  # What they do
            "objects_interacted": {object: count},  # What objects they interact with
            "frequent_actions": [(action, count)],  # Top actions
            "possessions": [objects with @character],  # Objects owned
            "temporal_patterns": {clip_id: [actions]},  # How behavior changes over time
            "interaction_partners": {character: interaction_count}  # Who they interact with
        }
    """
    profile = {
        "actions": Counter(),
        "objects_interacted": Counter(),
        "possessions": set(),
        "temporal_patterns": defaultdict(list),
        "interaction_partners": Counter(),
    }
    
    # Get all edges where this character is the source
    if character_name in graph.adjacency_list:
        for edge_id in graph.adjacency_list[character_name]:
            edge = graph.edges[edge_id]
            action = edge.content
            target = edge.target
            
            profile["actions"][action] += 1
            profile["temporal_patterns"][edge.clip_id].append((action, target))
            
            # Check if target is an object
            if not (target.startswith("<") and target.endswith(">")):
                profile["objects_interacted"][target] += 1
                
                # Check if it's a possession (has @character in name)
                if f"@{character_name}" in target:
                    profile["possessions"].add(target)
            
            # Check if target is another character
            elif target != character_name:
                profile["interaction_partners"][target] += 1
    
    # Also check edges where character is target (passive interactions)
    for edge_id, edge in graph.edges.items():
        if edge.target == character_name and edge.source.startswith("<") and edge.source.endswith(">"):
            if edge.source != character_name:
                profile["interaction_partners"][edge.source] += 1
    
    return {
        "actions": dict(profile["actions"]),
        "objects_interacted": dict(profile["objects_interacted"]),
        "frequent_actions": profile["actions"].most_common(10),
        "possessions": list(profile["possessions"]),
        "temporal_patterns": dict(profile["temporal_patterns"]),
        "interaction_partners": dict(profile["interaction_partners"]),
    }


def extract_character_relationships(graph) -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Extract relationships between characters.
    
    Returns:
        {
            "character_1": [
                ("character_2", "interaction_type", count),
                ...
            ]
        }
    """
    relationships = defaultdict(lambda: defaultdict(int))
    
    # Direct character-to-character edges
    for edge_id, edge in graph.edges.items():
        src = edge.source
        tgt = edge.target
        
        # Both are characters
        if (src.startswith("<") and src.endswith(">") and 
            tgt.startswith("<") and tgt.endswith(">")):
            if src != tgt:
                relationships[src][(tgt, edge.content)] += 1
    
    # Indirect relationships through shared objects/actions
    # (e.g., both interact with same object)
    shared_objects = defaultdict(set)
    for edge_id, edge in graph.edges.items():
        src = edge.source
        tgt = edge.target
        
        if src.startswith("<") and src.endswith(">"):
            if not (tgt.startswith("<") and tgt.endswith(">")):
                # Character interacting with object
                shared_objects[tgt].add(src)
    
    # Find characters who share objects
    for obj, characters in shared_objects.items():
        char_list = list(characters)
        for i, char1 in enumerate(char_list):
            for char2 in char_list[i+1:]:
                relationships[char1][(char2, f"shares_{obj}")] += 1
                relationships[char2][(char1, f"shares_{obj}")] += 1
    
    # Convert to list format
    result = {}
    for char, rels in relationships.items():
        result[char] = [(other, rel_type, count) 
                        for (other, rel_type), count in rels.items()]
    
    return result


def extract_video_plot(graph) -> Dict:
    """
    Extract high-level plot understanding from temporal edge sequences.
    
    Returns:
        {
            "key_events": [(clip_id, event_description)],
            "scene_transitions": [(from_clip, to_clip, change_description)],
            "plot_summary": str,
            "timeline": {clip_id: [events]}
        }
    """
    # Group edges by clip_id
    clip_events = defaultdict(list)
    for edge_id, edge in graph.edges.items():
        clip_events[edge.clip_id].append(edge)
    
    # Extract key events (high-frequency actions or character appearances)
    key_events = []
    action_frequency = Counter()
    character_appearances = defaultdict(set)
    
    for clip_id, edges in sorted(clip_events.items()):
        clip_actions = []
        for edge in edges:
            action_frequency[edge.content] += 1
            if edge.source.startswith("<") and edge.source.endswith(">"):
                character_appearances[clip_id].add(edge.source)
            clip_actions.append(f"{edge.source} {edge.content} {edge.target}")
        
        key_events.append((clip_id, clip_actions))
    
    # Detect scene transitions (changes in character/object presence)
    scene_transitions = []
    prev_characters = set()
    prev_objects = set()
    
    for clip_id in sorted(clip_events.keys()):
        current_characters = character_appearances[clip_id]
        current_objects = set()
        for edge in clip_events[clip_id]:
            if not (edge.target.startswith("<") and edge.target.endswith(">")):
                current_objects.add(edge.target)
        
        if prev_characters or prev_objects:
            new_chars = current_characters - prev_characters
            new_objects = current_objects - prev_objects
            if new_chars or new_objects:
                scene_transitions.append((
                    clip_id - 1, clip_id,
                    f"New characters: {new_chars}, New objects: {new_objects}"
                ))
        
        prev_characters = current_characters
        prev_objects = current_objects
    
    return {
        "key_events": key_events,
        "scene_transitions": scene_transitions,
        "most_common_actions": action_frequency.most_common(10),
        "timeline": {clip_id: [f"{e.source} {e.content} {e.target}" 
                               for e in edges] 
                    for clip_id, edges in clip_events.items()},
    }


def extract_object_usage_patterns(graph) -> Dict:
    """
    Extract how objects are used across the video.
    
    Returns:
        {
            "object_name": {
                "users": [characters who interact with it],
                "actions": [actions performed on it],
                "frequency": count,
                "contexts": [clip_ids where it appears]
            }
        }
    """
    object_patterns = defaultdict(lambda: {
        "users": set(),
        "actions": Counter(),
        "contexts": set(),
    })
    
    for edge_id, edge in graph.edges.items():
        target = edge.target
        source = edge.source
        
        # If target is an object (not a character)
        if not (target.startswith("<") and target.endswith(">")):
            obj_key = target.split("@")[0].split("#")[0]  # Base object name
            
            if source.startswith("<") and source.endswith(">"):
                object_patterns[obj_key]["users"].add(source)
            object_patterns[obj_key]["actions"][edge.content] += 1
            object_patterns[obj_key]["contexts"].add(edge.clip_id)
    
    # Convert to final format
    result = {}
    for obj, data in object_patterns.items():
        result[obj] = {
            "users": list(data["users"]),
            "actions": dict(data["actions"]),
            "most_common_action": data["actions"].most_common(1)[0] if data["actions"] else None,
            "frequency": sum(data["actions"].values()),
            "contexts": sorted(list(data["contexts"])),
        }
    
    return result


def extract_behavioral_patterns(graph, include_conversations=True) -> Dict:
    """
    Extract behavioral patterns combining edges and conversations.
    
    Args:
        include_conversations: Whether to incorporate conversation data
    
    Returns:
        {
            "character_behaviors": {character: behavior_summary},
            "conversation_context": {clip_id: conversation_summary},
            "behavior_dialogue_alignment": {character: [(action, dialogue_context)]}
        }
    """
    behaviors = {}
    
    # Extract behavior from edges
    for char_name in graph.characters.keys():
        profile = extract_character_profile(graph, char_name)
        behaviors[char_name] = {
            "primary_actions": profile["frequent_actions"][:5],
            "key_objects": list(profile["objects_interacted"].keys())[:5],
            "possessions": profile["possessions"],
        }
    
    # Incorporate conversations if available
    conversation_context = {}
    behavior_dialogue = defaultdict(list)
    
    if include_conversations:
        for conv_id, conversation in graph.conversations.items():
            for clip_id in conversation.clips:
                conversation_context[clip_id] = {
                    "speakers": list(conversation.speakers),
                    "message_count": len(conversation.messages),
                }
                
                # Align conversations with behaviors by clip_id
                for char in conversation.speakers:
                    # Find behaviors in same clip
                    char_edges = [e for e in graph.edges.values() 
                                 if e.source == char and e.clip_id == clip_id]
                    if char_edges:
                        behavior_dialogue[char].append({
                            "clip_id": clip_id,
                            "actions": [e.content for e in char_edges],
                            "dialogue": [msg[1] for msg in conversation.messages 
                                        if msg[0] == char],
                        })
    
    return {
        "character_behaviors": behaviors,
        "conversation_context": conversation_context,
        "behavior_dialogue_alignment": dict(behavior_dialogue),
    }


def generate_character_summary(graph, character_name: str) -> str:
    """
    Generate a natural language summary of a character.
    """
    profile = extract_character_profile(graph, character_name)
    relationships = extract_character_relationships(graph)
    
    summary_parts = [f"Character: {character_name}\n"]
    
    # Actions
    if profile["frequent_actions"]:
        top_actions = ", ".join([f"{action} ({count}x)" 
                                 for action, count in profile["frequent_actions"][:5]])
        summary_parts.append(f"Primary actions: {top_actions}")
    
    # Possessions
    if profile["possessions"]:
        summary_parts.append(f"Possessions: {', '.join(profile['possessions'][:5])}")
    
    # Relationships
    if character_name in relationships and relationships[character_name]:
        rels = relationships[character_name][:3]
        rel_str = ", ".join([f"{other} ({rel_type})" for other, rel_type, _ in rels])
        summary_parts.append(f"Key relationships: {rel_str}")
    
    return "\n".join(summary_parts)


def generate_plot_summary(graph) -> str:
    """
    Generate a high-level plot summary from the graph.
    """
    plot_data = extract_video_plot(graph)
    
    summary_parts = ["Video Plot Summary:\n"]
    
    # Timeline
    summary_parts.append("Timeline:")
    for clip_id in sorted(plot_data["timeline"].keys()):
        events = plot_data["timeline"][clip_id][:3]  # Top 3 events per clip
        summary_parts.append(f"  Clip {clip_id}: {'; '.join(events)}")
    
    # Key transitions
    if plot_data["scene_transitions"]:
        summary_parts.append("\nScene Transitions:")
        for from_clip, to_clip, change in plot_data["scene_transitions"][:5]:
            summary_parts.append(f"  Clip {from_clip} -> {to_clip}: {change}")
    
    return "\n".join(summary_parts)


def align_behavior_conversation(graph, clip_id: int = None) -> Dict:
    """
    Align behavior (edges) with conversations for a specific clip or all clips.
    
    Args:
        clip_id: Specific clip to analyze, or None for all clips
    
    Returns:
        {
            clip_id: {
                "behaviors": [list of actions],
                "conversation": [list of messages],
                "aligned_events": [(character, action, dialogue_context)]
            }
        }
    """
    result = defaultdict(lambda: {
        "behaviors": [],
        "conversation": [],
        "aligned_events": [],
    })
    
    # Get behaviors by clip
    behaviors_by_clip = defaultdict(list)
    for edge_id, edge in graph.edges.items():
        if clip_id is None or edge.clip_id == clip_id:
            behaviors_by_clip[edge.clip_id].append(edge)
    
    # Get conversations by clip
    conversations_by_clip = defaultdict(list)
    for conv_id, conversation in graph.conversations.items():
        for cid in conversation.clips:
            if clip_id is None or cid == clip_id:
                conversations_by_clip[cid].extend(conversation.messages)
    
    # Align by clip_id
    all_clips = set(behaviors_by_clip.keys()) | set(conversations_by_clip.keys())
    
    for cid in all_clips:
        behaviors = behaviors_by_clip[cid]
        messages = conversations_by_clip[cid]
        
        result[cid]["behaviors"] = [
            f"{e.source} {e.content} {e.target}" for e in behaviors
        ]
        result[cid]["conversation"] = messages
        
        # Align: find behaviors and dialogue for same character in same clip
        char_behaviors = defaultdict(list)
        char_dialogue = defaultdict(list)
        
        for edge in behaviors:
            if edge.source.startswith("<") and edge.source.endswith(">"):
                char_behaviors[edge.source].append(edge.content)
        
        for msg in messages:
            if isinstance(msg, list) and len(msg) >= 1:
                char_dialogue[msg[0]].append(msg[1] if len(msg) > 1 else "")
        
        # Create aligned events
        for char in set(char_behaviors.keys()) | set(char_dialogue.keys()):
            behaviors_list = char_behaviors.get(char, [])
            dialogue_list = char_dialogue.get(char, [])
            
            # Pair behaviors with dialogue context
            for behavior in behaviors_list:
                dialogue_context = dialogue_list[0] if dialogue_list else None
                result[cid]["aligned_events"].append((char, behavior, dialogue_context))
    
    return dict(result) if clip_id is None else result.get(clip_id, {})


def combine_behavior_dialogue(graph, character_name: str) -> Dict:
    """
    Combine behavior and dialogue for a complete character understanding.
    
    Returns:
        {
            "behavior_summary": {...},
            "dialogue_summary": {...},
            "aligned_contexts": [...],
            "complete_profile": str
        }
    """
    # Behavior profile
    behavior_profile = extract_character_profile(graph, character_name)
    
    # Dialogue summary
    dialogue_summary = {
        "total_messages": 0,
        "clips_with_dialogue": set(),
        "message_examples": [],
    }
    
    for conv_id, conversation in graph.conversations.items():
        char_messages = [msg for msg in conversation.messages 
                        if isinstance(msg, list) and len(msg) >= 1 and msg[0] == character_name]
        if char_messages:
            dialogue_summary["total_messages"] += len(char_messages)
            dialogue_summary["clips_with_dialogue"].update(conversation.clips)
            dialogue_summary["message_examples"].extend([msg[1] for msg in char_messages[:3]])
    
    dialogue_summary["clips_with_dialogue"] = sorted(list(dialogue_summary["clips_with_dialogue"]))
    
    # Aligned contexts
    aligned = align_behavior_conversation(graph)
    aligned_contexts = []
    for clip_id, data in aligned.items():
        char_events = [e for e in data["aligned_events"] if e[0] == character_name]
        if char_events:
            aligned_contexts.append({
                "clip_id": clip_id,
                "events": char_events,
            })
    
    # Generate complete profile
    profile_parts = [f"Complete Profile: {character_name}\n"]
    profile_parts.append(f"Actions: {', '.join([a[0] for a in behavior_profile['frequent_actions'][:5]])}")
    profile_parts.append(f"Dialogue: {dialogue_summary['total_messages']} messages across {len(dialogue_summary['clips_with_dialogue'])} clips")
    if dialogue_summary["message_examples"]:
        profile_parts.append(f"Sample dialogue: {dialogue_summary['message_examples'][0]}")
    
    return {
        "behavior_summary": behavior_profile,
        "dialogue_summary": dialogue_summary,
        "aligned_contexts": aligned_contexts,
        "complete_profile": "\n".join(profile_parts),
    }

