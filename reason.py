import json
import pickle
from classes.hetero_graph import HeteroGraph
from utils.llm import generate_text_response
from utils.mllm_pictures import generate_messages, get_response
from utils.prompts import prompt_parse_query, prompt_semantic_answer
from utils.general import strip_code_fences, load_video_list, Tee


def reason(question, graph):

    strategy = generate_text_response(prompt_parse_query + "\n" + question)

    # transfer the strategy into dictionary
    strategy_dict = json.loads(strip_code_fences(strategy))
    print(strategy_dict)

    triple = strategy_dict["query_triple"]
    spatial_constraint = strategy_dict["spatial_constraint"]
    speaker_strict = strategy_dict["speaker_strict"]
    allocation = strategy_dict["allocation"]


    # search the graph for the relevant information
    high_level_edges = graph.search_high_level_edges(triple, allocation["k_high_level"])
    low_level_edges = graph.search_low_level_edges(triple, allocation["k_low_level"], spatial_constraint)
    conversation_edges = graph.search_conversation_edges(triple, allocation["k_conversations"], speaker_strict)

    print(high_level_edges)
    print(low_level_edges)
    print(conversation_edges)

    

if __name__ == "__main__":
    # load the graph from the file
    with open("data/semantic_memory/gym_01.pkl", "rb") as f:
        graph = pickle.load(f)

    reason("Which takeout should be taken to Anna?", graph)