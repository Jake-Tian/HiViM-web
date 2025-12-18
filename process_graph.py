import pickle
from classes.hetero_graph import HeteroGraph

# load the graph from the file
with open("graph.pkl", "rb") as f:
    graph = pickle.load(f)

print(graph.characters)
print("--------------------------------")
print(graph.objects)
print("--------------------------------")
print(graph.conversations)
print("--------------------------------")
print(graph.edges)
