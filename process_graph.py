import time
import json
import pickle
from classes.hetero_graph import HeteroGraph

# load the graph from the file
with open("data/results/results.json", "r") as f:
    results = json.load(f)

# print as a dictionary
results = results["gym_01_Q10"]
print(results["graph_search_results"])
# print(results["semantic_video_output"])
# print(results["video_answer_outputs"])

