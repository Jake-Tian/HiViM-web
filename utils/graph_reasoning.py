"""
Graph-based reasoning utilities.

This module provides functions for reasoning about questions using only
the knowledge graph, without watching video clips.
"""

from utils.llm import generate_text_response
from utils.prompts import prompt_semantic_answer_only, prompt_parse_query
from utils.search import search_with_parse


def reason_from_graph(question, graph):
    """
    Reason about a question using only the graph knowledge, without watching videos.
    
    This function searches the graph and directly answers the question based on
    the extracted knowledge, without the option to watch video clips.
    
    Args:
        question: The question to answer
        graph: HeteroGraph instance
    
    Returns:
        dict with keys:
            - 'question': The original question
            - 'parse_query_output': Output from prompt_parse_query
            - 'graph_search_results': Formatted search results from the graph
            - 'answer': The final answer based on graph knowledge
    """
    result = {
        'question': question,
        'parse_query_output': None,
        'graph_search_results': None,
        'answer': None
    }
    
    print("Question:", question)
    
    #--------------------------------
    # Part 1: Search the graph
    #--------------------------------
    print("\n[Step 1] Searching the graph...")
    try:
        # Parse query using LLM
        parse_query_response = generate_text_response(prompt_parse_query + "\n" + question)
        result['parse_query_output'] = parse_query_response
        print("Parse Query Output:")
        print(parse_query_response)
        
        # Search the graph with parsed query
        graph_search_results = search_with_parse(question, graph, parse_query_response)
        result['graph_search_results'] = graph_search_results
        print("\nGraph Search Results:")
        print(graph_search_results)
        
    except Exception as e:
        raise Exception(f"Error searching graph: {e}")
    
    #--------------------------------
    # Part 2: Answer directly from graph knowledge
    #--------------------------------
    print("\n[Step 2] Answering from graph knowledge...")
    try:
        # Combine prompt, question, and search results
        prompt = prompt_semantic_answer_only + "\n\nExtracted knowledge:\n" + graph_search_results + "\n\nQuestion: " + question
        
        # Get answer from LLM
        answer = generate_text_response(prompt)
        result['answer'] = answer.strip()
        
        print("Answer:")
        print(result['answer'])
        
    except Exception as e:
        raise Exception(f"Error generating answer: {e}")
    
    return result


if __name__ == "__main__":
    # Example usage
    import pickle
    from pathlib import Path
    
    graph_path = Path("data/semantic_memory/gym_01.pkl")
    if graph_path.exists():
        with open(graph_path, "rb") as f:
            graph = pickle.load(f)
        
        question = "Which takeout should be taken to Anna?"
        
        try:
            result = reason_from_graph(question, graph)
            print("\nFinal Answer:", result['answer'])
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Graph file not found: {graph_path}")
