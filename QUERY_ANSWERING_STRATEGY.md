# Query Answering Strategy for HiViM

## Overview
This document outlines a hierarchical strategy for answering queries about processed video content using both semantic memory (graph/pickle) and episodic memory (JSON), with fallback to re-watching videos when necessary.

---

## System Architecture

### Data Structures

1. **Semantic Memory (Graph/Pickle)**
   - **Location**: `data/semantic_memory/{video_name}.pkl`
   - **Structure**: `HeteroGraph` object containing:
     - `characters`: Dictionary of character nodes (e.g., `"<robot>"`, `"<Alice>"`)
     - `objects`: Dictionary of object nodes (keyed by `(name, owner, attribute)` tuple)
     - `edges`: Dictionary of edge objects
     - `conversations`: Dictionary of conversation objects
     - `adjacency_list_out` / `adjacency_list_in`: Fast lookup structures

2. **Episodic Memory (JSON)**
   - **Location**: `data/episodic_memory/{video_name}.json`
   - **Structure**: Dictionary keyed by `clip_id`, each containing:
     - `folder`: Path to frame folder
     - `characters_behavior`: List of behavior descriptions
     - `conversation`: List of `[speaker, text]` pairs
     - `character_appearance`: JSON string of character appearances
     - `scene`: Scene description
     - `triples`: List of extracted triples `[source, content, target]`

3. **Edge Information Hierarchy**
   - **High-level edges** (`clip_id=0`, `scene=None`):
     - Character attributes: `source=<character>`, `content=attribute_name`, `target=None`, `confidence=score`
     - Character relationships: `source=<character1>`, `content=relationship`, `target=<character2>`, `confidence=score`
   - **Low-level edges** (`clip_id>0`, `scene=description`):
     - Action triples: `source=<character>`, `content=action_verb`, `target=object_or_character`
     - State triples: `source=object`, `content=state`, `target=location_or_object`

---

## Query Answering Pipeline

### Phase 1: Query Parsing and Triple Extraction

**Goal**: Convert natural language query into structured triples for graph matching.

**Steps**:
1. **Parse query to identify**:
   - Entities (characters, objects)
   - Actions/relationships
   - Temporal/spatial constraints
   - Question type (who, what, when, where, why, how)

2. **Extract query triples**:
   - Use LLM with a prompt similar to `prompt_extract_triples` to convert query into triples
   - Example: "What did Alice do with the coffee?" → `[["<Alice>", "does", "coffee"]]`
   - Example: "Who is Alice's friend?" → `[["<Alice>", "friend", "?"]]`

3. **Normalize entities**:
   - Match query entities to graph entities (handle variations, synonyms)
   - Use character appearance matching if needed
   - Handle object variations (e.g., "cup" vs "mug", "coffee#red" vs "coffee")

**Output**: List of query triples `[(source, content, target), ...]` with confidence scores

---

### Phase 2: Graph-Based Similarity Search

**Goal**: Find relevant edges in the semantic memory graph that match or are similar to query triples.

#### 2.1 Edge Classification and Filtering

**Differentiate edge types**:
- **High-level edges** (`clip_id=0`): Use for character attributes, relationships, general questions
- **Low-level edges** (`clip_id>0`): Use for specific actions, temporal queries, detailed questions

**Filtering strategy**:
```python
# High-level filter
high_level_edges = [e for e in graph.edges.values() 
                    if e.clip_id == 0 and e.scene is None]

# Low-level filter  
low_level_edges = [e for e in graph.edges.values() 
                    if e.clip_id > 0 and e.scene is not None]
```

#### 2.2 Embedding-Based Similarity Matching (Inspired by Atom)

**Key Innovation**: Use embedding-based reasoning for semantic matching, with operator-level batching for efficiency.

**For each query triple `(q_source, q_content, q_target)`**:

1. **Exact matching** (fast path):
   - Find edges where `source == q_source`, `content == q_content`, `target == q_target`
   - Priority: High confidence edges first
   - Use hash-based lookup for O(1) exact matches

2. **Embedding-based semantic matching** (when exact match insufficient):
   - **Pre-compute embeddings**: Store embeddings for all edge contents, sources, and targets
   - **Query embedding**: Generate embedding for query triple components
   - **Batch similarity computation**: Use operator-level batching to compute similarities for multiple edges simultaneously
   - **Content similarity**: Cosine similarity between query content embedding and edge content embeddings
   - **Entity similarity**: Handle variations using entity embeddings (e.g., "Alice" vs "<Alice>", "coffee" vs "coffee#red")
   - **Graph traversal**: Follow paths from query entities to find related edges

**Triple Similarity Computation (Atom's Approach)**:

Atom uses a **component-wise embedding approach** where source, content (relation), and target are embedded separately, then combined with learned or fixed weights:

```python
def compute_triple_similarity(query_triple, doc_triple):
    """
    Compute similarity between query triple (q_s, q_c, q_t) and document triple (d_s, d_c, d_t).
    
    Atom's approach:
    1. Embed each component separately
    2. Compute component-wise similarities
    3. Combine with weighted sum
    """
    # Step 1: Get embeddings for each component
    q_s_emb = get_entity_embedding(query_triple.source)      # Query source embedding
    q_c_emb = get_relation_embedding(query_triple.content)    # Query content/relation embedding
    q_t_emb = get_entity_embedding(query_triple.target)      # Query target embedding
    
    d_s_emb = get_entity_embedding(doc_triple.source)       # Document source embedding
    d_c_emb = get_relation_embedding(doc_triple.content)    # Document content/relation embedding
    d_t_emb = get_entity_embedding(doc_triple.target)        # Document target embedding
    
    # Step 2: Compute component-wise cosine similarities
    sim_source = cosine_similarity(q_s_emb, d_s_emb)
    sim_content = cosine_similarity(q_c_emb, d_c_emb)
    sim_target = cosine_similarity(q_t_emb, d_t_emb)
    
    # Step 3: Weighted combination (Atom's weighting strategy)
    # Common weights (may be learned or fixed):
    # - Content/relation typically has higher weight (0.4-0.5) as it's most discriminative
    # - Source and target share remaining weight (0.25-0.3 each)
    w_source = 0.25   # Weight for source similarity
    w_content = 0.50  # Weight for content/relation similarity (highest - most important)
    w_target = 0.25   # Weight for target similarity
    
    triple_similarity = (
        w_source * sim_source +
        w_content * sim_content +
        w_target * sim_target
    )
    
    return triple_similarity
```

**Alternative Approaches** (Atom may use):

1. **Learned Attention Weights**:
   - Use attention mechanism to dynamically weight components based on query context
   - Weights adapt to different query types (e.g., relation-focused vs entity-focused)

2. **Triple-Level Embedding**:
   - Embed entire triple as single vector: `emb(triple) = f(emb(s), emb(c), emb(t))`
   - Use composition functions like concatenation, addition, or learned transformations
   - Then compute cosine similarity on combined embeddings

3. **Distance-Based Scoring**:
   - Use translation-based models: `score = ||emb(s) + emb(c) - emb(t)||`
   - Lower distance = higher similarity

**Weight Determination**:

- **Fixed weights**: Based on empirical analysis (content typically most important)
- **Learned weights**: Trained on query-document relevance pairs
- **Context-dependent**: Weights vary based on query type or graph structure
- **Adaptive**: Weights adjust based on which components match exactly vs semantically

3. **Operator-level batching strategy**:
   ```python
   # Batch multiple query triples or multiple edges for efficiency
   def batch_similarity_search(query_triples, candidate_edges, batch_size=32):
       # Group operations by type (exact match, embedding similarity, traversal)
       # Process in batches to leverage GPU/parallel computation
       # Return top-k matches per query triple
   ```

4. **Graph traversal strategies**:
   - **Direct neighbors**: Get all edges connected to query entities
   - **Multi-hop paths**: Traverse 2-3 hops to find indirect connections
   - **Subgraph extraction**: Extract subgraph around query entities (within N hops)
   - **Temporal paths**: Follow edges with similar `clip_id` values (temporal proximity)
   - **Batch traversal**: Process multiple query entities in parallel

5. **Enhanced scoring mechanism**:
   ```python
   edge_score = (
       exact_match_bonus * 1.0 +
       embedding_similarity * 0.7 +      # Increased weight for embedding-based matching
       confidence_score * 0.3 +
       temporal_relevance * 0.1 +
       graph_structure_score * 0.1       # Bonus for edges in dense subgraphs
   )
   ```

#### 2.3 Conversation-Based Search

**Key Innovation**: Leverage conversation information stored in the graph for answering queries about relationships, motivations, and causal events.

**For queries involving relationships, motivations, or "why" questions**:

1. **Conversation retrieval by entities**:
   - Find conversations where query entities are speakers or mentioned
   - Use `graph.conversations` dictionary to access conversation objects
   - Filter conversations by `clip_id` from matched edges

2. **Conversation embedding and similarity**:
   - Generate embeddings for conversation messages (full text or per-message)
   - Use embedding similarity to find conversations relevant to query
   - Batch conversation similarity computation for efficiency

3. **Conversation-to-edge linking**:
   - Link conversations to edges via `clip_id`
   - Use conversations to provide context for actions (edges)
   - Identify causal relationships: conversation → action

4. **Conversation search strategies**:
   ```python
   def search_conversations(query_entities, graph, clip_ids=None):
       relevant_conversations = []
       for conv_id, conv in graph.conversations.items():
           # Check if conversation involves query entities
           if query_entities & conv.speakers:  # Entity is a speaker
               if clip_ids is None or any(cid in clip_ids for cid in conv.clips):
                   relevant_conversations.append(conv)
       return relevant_conversations
   ```

5. **Conversation relevance scoring**:
   ```python
   conversation_score = (
       speaker_match * 0.4 +           # Query entity is a speaker
       content_similarity * 0.4 +       # Conversation content matches query
       temporal_proximity * 0.2         # Conversation near relevant clip_ids
   )
   ```

#### 2.4 Edge Information Utilization

**For each matched edge, extract**:
- **Edge metadata**: `clip_id`, `scene`, `confidence`
- **Connected nodes**: Source and target node information
- **Temporal context**: `clip_id` for chronological ordering
- **Spatial context**: `scene` for location information
- **Associated conversations**: Conversations from the same `clip_id` or adjacent clips

**Build evidence set**:
- Collect all matched edges with scores
- Collect relevant conversations with scores
- Group by `clip_id` to identify relevant time segments
- Group by `scene` to identify relevant locations
- Link conversations to edges for causal/contextual information
- Sort by relevance score

---

### Phase 3: Information Sufficiency Assessment

**Goal**: Determine if the graph information is sufficient to answer the query.

#### 3.1 Sufficiency Criteria

**Sufficient if**:
- Exact matches found for all query triples
- High confidence scores (e.g., `confidence >= 70`)
- Complete information (no missing entities/actions)
- Temporal/spatial constraints satisfied
- For "why" or relationship queries: Relevant conversations found that provide context

**Insufficient if**:
- No matches or only weak matches (low similarity scores)
- Missing entities (characters/objects not in graph)
- Ambiguous results (multiple conflicting edges)
- Temporal/spatial gaps (missing `clip_id` ranges)
- For "why" queries: No conversations found that explain motivations
- For relationship queries: No conversations found that provide interaction context

#### 3.2 Evidence Quality Scoring

```python
sufficiency_score = (
    match_coverage * 0.4 +      # % of query triples matched
    confidence_avg * 0.3 +      # Average confidence of matches
    completeness * 0.2 +         # Missing information ratio
    temporal_coherence * 0.1     # Temporal consistency
)
```

**Threshold**: If `sufficiency_score < 0.6`, proceed to Phase 4.

---

### Phase 4: Diving Deeper into Episodic Memory

**Goal**: Retrieve detailed information from episodic memory JSON files using `clip_id` from matched edges.

#### 4.1 Clip Identification

**From Phase 2, extract**:
- Set of relevant `clip_id`s from matched edges
- Prioritize `clip_id`s with highest edge scores
- Consider temporal ranges (e.g., `clip_id ± 2` for context)

#### 4.2 Episodic Memory Retrieval

**For each relevant `clip_id`**:

1. **Load episodic memory JSON**:
   ```python
   episodic_memory = json.load(open(f"data/episodic_memory/{video_name}.json"))
   clip_data = episodic_memory.get(clip_id)
   ```

2. **Extract detailed information**:
   - **`characters_behavior`**: Detailed behavior descriptions (more context than triples)
   - **`conversation`**: Full conversation transcripts `[speaker, text]` - **CRITICAL for context**
   - **`scene`**: Scene description
   - **`triples`**: All triples extracted from this clip
   - **`character_appearance`**: Character appearance details

3. **Conversation-focused retrieval**:
   - **For "why" queries**: Prioritize clips with conversations that explain motivations
   - **For relationship queries**: Extract conversations between query entities
   - **For causal queries**: Find conversations before/after actions (temporal context)
   - **Cross-clip conversations**: Check adjacent clips (`clip_id ± 1, 2`) for extended conversations

4. **Conversation analysis**:
   - **Speaker identification**: Identify which characters are speaking
   - **Topic extraction**: Use embeddings to identify conversation topics
   - **Sentiment/emotion**: Analyze conversation tone for relationship inference
   - **Action triggers**: Identify conversations that precede actions (causal links)

5. **Relevance filtering**:
   - Filter behaviors/conversations that mention query entities
   - Use keyword matching or semantic similarity (embedding-based)
   - Prioritize clips with multiple relevant mentions
   - For conversation-heavy queries: Prioritize clips with longer/more relevant conversations

#### 4.3 Conversation-Enhanced Information Synthesis

**Combine graph, episodic, and conversation information**:

1. **Graph-to-conversation linking**:
   - Use graph edges as "index" to episodic memory
   - Link edges to conversations via `clip_id`
   - Identify conversations that provide context for actions (edges)

2. **Information enrichment**:
   - Enrich graph triples with detailed behavior descriptions
   - **Add conversation context** for relationship queries (who said what to whom)
   - **Add conversation context** for "why" queries (motivations, reasons)
   - Use scene descriptions for spatial queries
   - Use conversations for temporal context (what was discussed before/after actions)

3. **Conversation-based reasoning**:
   - **Causal reasoning**: Conversations before actions explain motivations
   - **Relationship inference**: Conversations reveal relationship dynamics
   - **Contextual understanding**: Conversations provide background for actions
   - **Multi-turn analysis**: Analyze conversation flow across multiple clips

4. **Evidence combination**:
   ```python
   evidence = {
       'edges': matched_edges,
       'conversations': relevant_conversations,  # From graph and episodic memory
       'behaviors': behavior_descriptions,
       'temporal_context': clip_ids,
       'spatial_context': scenes
   }
   ```

**Re-assess sufficiency**:
- If episodic memory + conversations provide sufficient detail, generate answer
- If still insufficient, proceed to Phase 5

---

### Phase 5: Re-watching Videos

**Goal**: Select and re-process the most relevant video segments when graph and episodic memory are insufficient.

#### 5.1 Video Selection

**Criteria for selecting videos**:
1. **Relevance score**: Based on matched edges and episodic memory mentions
2. **Coverage**: Videos that cover multiple query aspects
3. **Temporal coverage**: Videos that span relevant time periods

**Selection algorithm**:
```python
video_scores = {}
for video_name in available_videos:
    score = (
        num_matched_edges[video_name] * 0.5 +
        num_episodic_mentions[video_name] * 0.3 +
        temporal_coverage[video_name] * 0.2
    )
    video_scores[video_name] = score

# Select top 1-2 videos
selected_videos = sorted(video_scores.items(), key=lambda x: x[1], reverse=True)[:2]
```

#### 5.2 Re-processing Strategy

**For each selected video**:

1. **Identify specific clips**:
   - Use `clip_id` from matched edges to identify relevant segments
   - Load frames from `data/frames/{video_name}/{clip_id}/`

2. **Re-run episodic memory generation**:
   - Use `process_full_video()` or a focused version for specific clips
   - Generate new episodic memory for the selected clips
   - Extract new triples and add to graph (temporarily or permanently)

3. **Re-query**:
   - Re-run Phase 2 (graph search) with updated graph
   - Re-run Phase 3 (sufficiency assessment)
   - If still insufficient, expand to adjacent clips

#### 5.3 Incremental Processing

**Optimization**: Only process clips that haven't been fully analyzed:
- Check if episodic memory for a clip exists and is complete
- If missing or incomplete, process only that clip
- Cache results to avoid redundant processing

---

## Answer Generation

### Final Answer Synthesis

**Once sufficient information is gathered**:

1. **Combine evidence from all phases**:
   - Graph edges (semantic memory)
   - Episodic memory details
   - Re-processed video information (if applicable)

2. **Generate structured answer**:
   - Use LLM to synthesize evidence into natural language
   - Include confidence scores
   - Cite sources (clip_id, video_name, edge confidence)

3. **Answer format**:
   ```
   Answer: [Natural language response]
   
   Confidence: [0-100]
   Sources: 
   - Graph edges: [edge IDs]
   - Episodic memory: [clip_ids]
   - Videos: [video_names]
   ```

---

## Implementation Considerations

### 1. Embedding-Based Similarity Search (Atom-Inspired)

**Architecture**:
- **Pre-computation phase**: Generate and cache embeddings for all graph entities and edge contents
  - Use sentence transformers (e.g., `all-MiniLM-L6-v2`) for edge content embeddings
  - Use entity embeddings for characters and objects (handle variations)
  - **Generate conversation embeddings**: Embed full conversations or per-message embeddings
  - Store embeddings in efficient format (e.g., numpy arrays, FAISS index)

- **Query-time phase**: 
  - Generate embedding for query triple components
  - **Generate query embedding for conversation search** (for "why", "what did they say" queries)
  - Use **operator-level batching** to compute similarities for multiple edges simultaneously
  - **Batch conversation similarity computation** for efficiency
  - Leverage GPU acceleration when available

- **Hybrid approach**:
  - **Fast path**: Exact string matching for high-confidence exact matches
  - **Slow path**: Embedding-based similarity for semantic matching
  - **Conversation path**: Embedding-based conversation search for contextual queries
  - **Fallback**: Keyword-based matching with synonyms

**Batching strategy**:
```python
# Batch multiple operations for efficiency
def batch_embedding_similarity(query_embeddings, edge_embeddings, batch_size=32):
    # Process in batches to maximize GPU utilization
    # Return top-k most similar edges per query

def batch_conversation_similarity(query_embedding, conversation_embeddings, batch_size=32):
    # Batch conversation similarity computation
    # Return top-k most relevant conversations
```

**Recommended**: 
- Pre-compute embeddings during graph construction (edges, entities, conversations)
- Use exact matching first (fast), then embedding-based matching (accurate)
- Batch operations when processing multiple queries or large candidate sets
- **Prioritize conversation search for "why", "what did they say", and relationship queries**

### 2. Graph Traversal Efficiency

**Optimizations**:
- Use adjacency lists (`adjacency_list_out`, `adjacency_list_in`) for O(1) neighbor lookup
- Limit traversal depth (e.g., max 3 hops)
- Cache frequently accessed subgraphs
- Use BFS for shortest path finding

### 3. Temporal Reasoning

**Handle temporal queries**:
- "What happened before/after X?": Filter edges by `clip_id` ranges
- "What happened first?": Sort edges by `clip_id`
- "What happened at the same time?": Group edges by `clip_id`

### 4. Multi-Video Queries

**For queries spanning multiple videos**:
- Load graphs from multiple pickle files
- Merge or query across graphs
- Aggregate episodic memory from multiple JSON files
- Prioritize videos with most relevant information

### 5. Caching and Performance (Atom-Inspired Optimizations)

**Multi-level caching**:
- **Level 1**: Loaded graphs (avoid re-loading pickle files)
- **Level 2**: Episodic memory JSONs
- **Level 3**: Pre-computed embeddings (entity, edge content, and **conversation embeddings**)
- **Level 4**: Similarity scores (cache for frequently queried patterns)
- **Level 5**: Traversal results (cache subgraph extractions)
- **Level 6**: Conversation-to-edge mappings (cache which conversations relate to which edges)

**Operator-level batching**:
- Batch multiple queries together when possible
- Batch embedding similarity computations
- **Batch conversation similarity computations**
- Batch graph traversal operations
- Use vectorized operations (numpy, PyTorch) for efficiency

**Lazy loading**: Only load graphs/episodic memory for videos that have relevant edges.

**Embedding index**:
- Use FAISS or similar library for fast approximate nearest neighbor search
- Build index during graph construction (edges, entities, **conversations**)
- Update index incrementally when graph is modified
- **Separate indices**: One for edges, one for conversations (different query patterns)

---

## Example Query Flow

### Query: "What is Alice's relationship with Bob?"

1. **Phase 1**: Parse to triple `[("<Alice>", "relationship", "<Bob>")]`

2. **Phase 2**: 
   - Search for high-level edges with `source="<Alice>"`, `content` containing "relationship", `target="<Bob>"`
   - Find relationship edge: `Edge(source="<Alice>", content="friend", target="<Bob>", clip_id=0, confidence=85)`
   - Also find indirect connections via `get_connected_edges("<Alice>", "<Bob>")`

3. **Phase 3**: 
   - Sufficiency score: 0.85 (high confidence, exact match)
   - **Sufficient** → Generate answer: "Alice and Bob are friends (confidence: 85%)"

### Query: "What did Alice do in the kitchen at 3pm?"

1. **Phase 1**: Parse to triples:
   - `[("<Alice>", "does", "?"), ("?", "location", "kitchen"), ("?", "time", "3pm")]`

2. **Phase 2**:
   - Search low-level edges with `source="<Alice>"`, `scene` containing "kitchen"
   - Find edges: `Edge(source="<Alice>", content="cooks", target="coffee", clip_id=15, scene="kitchen")`
   - Match `clip_id=15` to approximate time

3. **Phase 3**:
   - Sufficiency score: 0.6 (partial match, but missing exact time verification)
   - **Insufficient** → Proceed to Phase 4

4. **Phase 4**:
   - Load episodic memory for `clip_id=15`
   - Extract detailed behavior: "Alice is cooking coffee in the kitchen, checking the timer..."
   - Re-assess: **Sufficient** → Generate answer with details

### Query: "Why did Alice leave the room?"

1. **Phase 1**: Parse to triples:
   - `[("<Alice>", "leaves", "room"), ("?", "reason", "?")]`
   - Question type: "why" → requires conversation/contextual information

2. **Phase 2**:
   - Find edge: `Edge(source="<Alice>", content="exits", target="room", clip_id=20)`
   - No direct "reason" edge found
   - **Search conversations**: Find conversations at `clip_id=19, 20, 21` involving `<Alice>`
   - Search adjacent edges (`clip_id=19, 21`) for context
   - Find conversation in graph: `Conversation(id=5, clips=[19, 20], speakers=["<Bob>", "<Alice>"], messages=[...])`

3. **Phase 3**:
   - Sufficiency score: 0.4 (action found, but reason missing)
   - Conversation found but need full context → **Insufficient** → Proceed to Phase 4

4. **Phase 4**:
   - Load episodic memory for `clip_id=19, 20, 21`
   - Extract conversations and behaviors around `clip_id=20`
   - **Find conversation**: `["<Bob>", "Can you get the keys?"]` at `clip_id=19`
   - **Link conversation to action**: Conversation at `clip_id=19` → Action at `clip_id=20`
   - Re-assess: **Sufficient** → Generate answer: "Alice left the room because Bob asked her to get the keys."

### Query: "What did Alice and Bob discuss?"

1. **Phase 1**: Parse to triples:
   - `[("<Alice>", "discusses", "<Bob>")]`
   - Question type: "what" → requires conversation content

2. **Phase 2**:
   - **Primary search: Conversations** (not edges)
   - Find conversations where both `<Alice>` and `<Bob>` are speakers
   - Use `graph.conversations` to find relevant conversations
   - Extract conversation messages using embedding similarity

3. **Phase 3**:
   - Sufficiency score: 0.8 (conversations found with both speakers)
   - **Sufficient** → Generate answer from conversation messages

### Query: "How do Alice and Bob feel about each other?"

1. **Phase 1**: Parse to triples:
   - `[("<Alice>", "feels", "<Bob>"), ("<Bob>", "feels", "<Alice>")]`
   - Question type: "how" → requires relationship and conversation analysis

2. **Phase 2**:
   - Search high-level edges: Find relationship edges between `<Alice>` and `<Bob>`
   - **Search conversations**: Find all conversations between `<Alice>` and `<Bob>`
   - Analyze conversation tone, sentiment, and content
   - Use `get_connected_edges("<Alice>", "<Bob>")` to find interaction patterns

3. **Phase 3**:
   - Sufficiency score: 0.7 (relationships + conversations found)
   - **Sufficient** → Generate answer combining relationship edges and conversation analysis

---

## Atom-Inspired Enhancements

### Embedding Infrastructure

1. **Pre-computed embeddings**:
   - Generate embeddings for all edge contents during graph construction
   - Store entity embeddings for characters and objects
   - **Generate conversation embeddings** (full conversation or per-message)
   - Build FAISS index for fast similarity search (edges, entities, conversations)
   - Update embeddings incrementally when graph changes

2. **Operator-level batching**:
   - Batch multiple query triples for parallel processing
   - Batch embedding similarity computations
   - **Batch conversation similarity computations**
   - Batch graph traversal operations
   - Optimize for GPU acceleration when available

3. **Query serving optimization**:
   - Pre-warm caches with frequently accessed subgraphs
   - Use query patterns to optimize traversal strategies
   - Implement query result caching for common queries
   - **Cache conversation-to-edge mappings** for faster causal reasoning

### Additional Future Enhancements

1. **Learning from queries**: Track which phases are most effective for different query types
2. **Query optimization**: Pre-compute common query patterns
3. **Multi-modal reasoning**: Use frame images directly for visual queries
4. **Temporal reasoning**: Better handling of "before/after" and causal relationships
5. **Uncertainty quantification**: Provide confidence intervals for answers
6. **Distributed query processing**: Scale to multiple videos/graphs using distributed embeddings

---

## Summary

This strategy implements a **hierarchical retrieval system** enhanced with **Atom-inspired optimizations** and **conversation-aware reasoning**:
1. **Fast graph search** (semantic memory) for high-level queries
   - **Embedding-based reasoning** for semantic matching
   - **Operator-level batching** for efficient processing
   - **Conversation search** for contextual and causal queries
2. **Detailed episodic memory** for context and specifics
   - **Conversation extraction** for "why", relationship, and dialogue queries
   - **Conversation-to-action linking** for causal reasoning
3. **Re-processing videos** as a last resort for missing information

### Key Innovations from Atom Paper

1. **Embedding-based knowledge graph reasoning**: 
   - Pre-compute embeddings for all graph entities and edge contents
   - **Pre-compute conversation embeddings** for dialogue and contextual queries
   - Use semantic similarity instead of just exact matching
   - Handle entity variations and synonyms effectively

2. **Operator-level batching**:
   - Batch multiple operations (similarity computation, traversal) for efficiency
   - **Batch conversation similarity computations**
   - Leverage GPU acceleration when available
   - Optimize for query serving workloads

3. **Efficient query serving**:
   - Multi-level caching strategy (including conversation embeddings)
   - Lazy loading of graphs and episodic memory
   - Fast approximate nearest neighbor search (FAISS) for edges and conversations

### Conversation-Aware Enhancements

1. **Conversation search integration**:
   - Search conversations in graph (`graph.conversations`) and episodic memory
   - Use embeddings for conversation relevance matching
   - Link conversations to edges via `clip_id` for causal reasoning

2. **Query-specific conversation strategies**:
   - **"Why" queries**: Find conversations before actions that explain motivations
   - **Relationship queries**: Extract conversations between query entities
   - **"What did they say" queries**: Direct conversation content retrieval
   - **Causal queries**: Analyze conversation-action temporal relationships

3. **Conversation analysis**:
   - Speaker identification and relationship inference
   - Topic extraction using embeddings
   - Sentiment/emotion analysis for relationship understanding
   - Multi-turn conversation flow analysis

The key is to **progressively dive deeper** only when necessary, balancing answer quality with computational cost, while leveraging **embedding-based reasoning**, **batching**, and **conversation-aware search** for efficiency and accuracy.

