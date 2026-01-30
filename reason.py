import json
import pickle
import time
import fcntl
from pathlib import Path
from utils.llm import generate_text_response, get_token_counter
from utils.prompts import prompt_semantic_video, prompt_parse_query
from utils.search import search_with_parse
from utils.reasoning import parse_semantic_response, extract_clip_ids, watch_video_clips


def evaluate_semantic_answer(question, graph_search_results):
    """
    For step 2: Evaluate semantic answer
    Evaluate whether the graph search results are sufficient to answer the question.
    
    Args:
        question: The question to answer
        graph_search_results: The formatted search results from the graph
    
    Returns:
        dict with keys: 'semantic_video_output', 'parsed_response' (with action, content, summary)
    """
    # Combine prompt, question, and search results
    prompt = prompt_semantic_video + "\n\nExtracted knowledge from graph:\n" + graph_search_results + "\n\nQuestion: " + question
    
    # Get semantic answer from LLM
    try:
        semantic_response, _ = generate_text_response(prompt)
    except Exception as e:
        raise Exception(f"Error generating semantic answer: {e}")
    
    # Parse the response
    try:
        parsed = parse_semantic_response(semantic_response)
    except Exception as e:
        raise Exception(f"Error parsing semantic response: {e}\nResponse: {semantic_response}")
    
    return {
        'semantic_video_output': semantic_response,
        'parsed_response': parsed
    }


def _update_token_usage(video_name, total_tokens):
    usage_path = Path("data/results/token_usage.json")
    lock_path = usage_path.with_suffix(usage_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        data = {"memorization": {}, "reasoning": {}}
        if usage_path.exists():
            try:
                with open(usage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        data.setdefault("reasoning", {})
        data["reasoning"][video_name] = total_tokens
        usage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        fcntl.flock(lock_file, fcntl.LOCK_UN)


def reason(question, graph, video_name):
    """
    Reason about a question using the graph and optionally watching video clips.
    
    Args:
        question: The question to answer
        graph: HeteroGraph instance
        video_name: Name of the video (e.g., "gym_01") used to locate frame directories
    
    Returns:
        dict with keys:
            - 'parse_query_output': Output from prompt_parse_query
            - 'graph_search_results': Formatted search results from the graph
            - 'semantic_video_output': Output from prompt_semantic_video
            - 'video_answer_outputs': List of outputs from prompt_video_answer for each clip watched
            - 'final_answer': The final answer to the question
    """
    start_time = time.time()
    result = {
        'question': question,
        'parse_query_output': None,
        'graph_search_results': None,
        'semantic_video_output': None,
        'video_answer_outputs': None,
        'final_answer': None
    }
    print("Question:", question)

    #--------------------------------
    # Part 1: Search the graph
    #--------------------------------
    print("\n[Step 1] Searching the graph...")
    try:
        # Parse query using LLM
        parse_query_response, _ = generate_text_response(prompt_parse_query + "\n" + question)
        result['parse_query_output'] = parse_query_response
        print("Parse Query Output:")
        print(parse_query_response)
        
        # Search the graph with parsed query
        graph_search_results = search_with_parse(question, graph, parse_query_response)
        result['graph_search_results'] = graph_search_results
        # print("\nGraph Search Results:")
        # print(graph_search_results)
        
    except Exception as e:
        raise Exception(f"Error searching graph: {e}")
    
    #--------------------------------
    # Part 2: Evaluate semantic answer
    #--------------------------------
    print("\n[Step 2] Evaluating semantic answer...")
    try:
        semantic_result = evaluate_semantic_answer(question, result['graph_search_results'])
        result['semantic_video_output'] = semantic_result['semantic_video_output']
        parsed = semantic_result['parsed_response']
        
        print(result['semantic_video_output'])
    except Exception as e:
        raise Exception(f"Error evaluating semantic answer: {e}")
    
    # If action is Answer, return immediately
    if parsed['action'].upper() == 'ANSWER':
        result['final_answer'] = parsed['content']
        result['video_answer_outputs'] = []
        print("FINAL ANSWER (from graph):")
        print(result['final_answer'])
        _update_token_usage(video_name, get_token_counter())
        elapsed = time.time() - start_time
        print(f"Reasoning time: {elapsed:.2f}s")
        return result
    
    # If action is Search, watch the video clips
    if parsed['action'].upper() != 'SEARCH':
        raise ValueError(f"Unknown action: {parsed['action']}")
    
    #--------------------------------
    # Part 3: Watch the video clips
    #--------------------------------
    # Extract clip IDs from content
    clip_ids = extract_clip_ids(parsed['content'])
    if not clip_ids:
        # Fallback: use the first clip in data/frames/{video_name} and answer with prompt_video_answer_final
        frames_dir = Path(f"data/frames/{video_name}")
        if not frames_dir.exists():
            raise ValueError(f"Could not extract clip IDs from content: {parsed['content']} and frames directory not found: {frames_dir}")
        subdirs = sorted(
            [d.name for d in frames_dir.iterdir() if d.is_dir()],
            key=lambda x: int(x) if str(x).isdigit() else x
        )
        if not subdirs:
            raise ValueError(f"Could not extract clip IDs from content: {parsed['content']} and no clip folders in {frames_dir}")
        # Prefer numeric folder names so clip_ids is consistently list of int
        numeric_subdirs = sorted([d for d in subdirs if str(d).isdigit()], key=lambda x: int(x))
        first_clip = int(numeric_subdirs[0]) if numeric_subdirs else subdirs[0]
        clip_ids = [first_clip]
        print(f"No clip IDs in content; using first clip from frames: {clip_ids} (will use final-answer prompt)")

    print(f"\n[Step 3] Watching video clips: {clip_ids}")
    
    # Watch video clips
    try:
        video_result = watch_video_clips(
            question, 
            clip_ids, 
            video_name, 
            initial_summary=parsed.get('summary'),
            print_progress=True
        )
        result['video_answer_outputs'] = video_result['video_answer_outputs']
        result['final_answer'] = video_result['final_answer']
        
        print("Video Answer Outputs:")
        if result['video_answer_outputs']:
            for i, clip_output in enumerate(result['video_answer_outputs'], 1):
                print(f"   Clip {clip_output['clip_id']}:")
                print(f"   {clip_output['video_answer_output']}")
        else:
            print("   No video clips were processed.")
    except Exception as e:
        raise Exception(f"Error watching video clips: {e}")
    
    print("Final Answer:")
    print(result['final_answer'])

    _update_token_usage(video_name, get_token_counter())
    elapsed = time.time() - start_time
    print(f"Reasoning time: {elapsed:.2f}s")

    return result


if __name__ == "__main__":
    # Example usage
    with open("data/semantic_memory/living_room_12.pkl", "rb") as f:
        graph = pickle.load(f)
    
    question = "How many things are left unfinished after the sofa is cleaned?"
    video_name = "living_room_12"
    
    try:
        result = reason(question, graph, video_name)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
