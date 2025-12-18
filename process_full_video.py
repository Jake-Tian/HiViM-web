import glob
import json
import pickle
from pathlib import Path
from classes.hetero_graph import HeteroGraph
from utils.llm import generate_text_response
from utils.mllm_pictures import generate_messages, get_response
from utils.prompts import prompt_generate_episodic_memory, prompt_extract_triples
from utils.general import strip_code_fences

gym_frames_dir = Path("data/frames/gym_01")
image_folders = sorted(
    [str(folder) for folder in gym_frames_dir.iterdir() if folder.is_dir()],
    key=lambda x: int(Path(x).name)
)

character_appearance = "{}"
previous_conversation = False
episodic_memory = dict()
graph = HeteroGraph()

for folder in image_folders:
    print("--------------------------------")
    print("Processing folder: ", folder)
    clip_id = int(folder.split("/")[-1])
    response_dict = dict()
    # Collect images in the current folder
    current_images = sorted(
        glob.glob(f"{folder}/*.jpg"),
        key=lambda p: int(Path(p).stem) if Path(p).stem.isdigit() else p,
    )

    #--------------------------------
    # Episodic Memory
    #--------------------------------
    prompt = "Character appearance from previous videos: \n" + character_appearance + "\n" + prompt_generate_episodic_memory
    messages = generate_messages(current_images, prompt)
    response = get_response(messages)
    print(response)
    response = strip_code_fences(response)
    response_dict = json.loads(response)


    # 1. Process the character's behavior
    behaviors = response_dict["characters_behavior"]
    if behaviors[0].startswith("Equivalance:"):
        equivalence = behaviors[0].split(":")[1].split(",")
        behaviors = behaviors[1:]
        graph.rename_character(equivalence[0], equivalence[1])

    # 2. Process the character appearance
    character_appearance = response_dict["character_appearance"]
    for character in character_appearance:
        if character not in graph.characters:
            graph.add_character(character)

    # 3. Process the conversation
    conversation = response_dict["conversation"]

    if len(conversation) > 0:
        graph.update_conversation(clip_id, conversation, previous_conversation=previous_conversation)
        previous_conversation = True  # Set to True for next iteration
    else:
        previous_conversation = False  # No conversation in this clip, reset for next iteration

    scene = response_dict["scene"]

    #--------------------------------
    # Semantic Memory
    #--------------------------------
    behavior_prompt = prompt_extract_triples + "\n" + "\n".join(behaviors)
    triples_response = generate_text_response(behavior_prompt)

    triples_response = strip_code_fences(triples_response)
    triples = json.loads(triples_response)
    graph.insert_triples(triples, clip_id, scene)
    print(f"Inserted {len(triples)} triples into graph for clip {clip_id}")

    character_appearance = json.dumps(character_appearance)

    # Store episodic memory for this clip
    episodic_memory[clip_id] = {
        "folder": folder,
        "characters_behavior": behaviors,
        "conversation": conversation,
        "character_appearance": character_appearance,
        "scene": scene,
        "triples": triples
    }

# save the graph to a file
with open("data/semantic_memory/gym_01.pkl", "wb") as f:
    pickle.dump(graph, f)

# save the episodic memory to a JSON file
with open("data/episodic_memory/gym_01.json", "w") as f:
    json.dump(episodic_memory, f, indent=2)
print(f"\n✓ Saved episodic memory for {len(episodic_memory)} clips to gym_01.json")

