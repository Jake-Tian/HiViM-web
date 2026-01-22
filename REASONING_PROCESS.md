# Full Reasoning Process Documentation

## Overview

The reasoning system follows a **3-step pipeline** to answer questions about videos:

1. **Graph Search**: Parse question and search the knowledge graph
2. **Semantic Evaluation**: Determine if graph information is sufficient or if video watching is needed
3. **Video Watching** (if needed): Watch video clips sequentially until answer is found

---

## Step-by-Step Process

### **STEP 1: Graph Search** (`reason.py` lines 72-87)

**Goal**: Extract relevant information from the knowledge graph

**Process**:
1. **Parse Query** (`prompt_parse_query`):
   - Input: Natural language question (e.g., "Where is the book Lucky read just now?")
   - Output: JSON strategy with:
     - `query_triple(s)`: Structured triples like `[source, content, target]`
     - `spatial_constraint`: Location constraints (e.g., "bedroom", "now", "last time")
     - `speaker_strict`: Whether to match speakers exactly
     - `allocation`: How many results to retrieve (k_high_level, k_low_level, k_conversations)

2. **Search Graph** (`search_with_parse`):
   - Searches three types of information:
     - **High-level edges**: Character attributes and relationships
     - **Low-level edges**: Actions and events with clip IDs
     - **Conversations**: Dialogue with clip IDs
   - Uses embedding similarity to find most relevant results
   - Returns formatted natural language string with all search results

**Example Output**:
```
High-Level Information (Character Attributes and Relationships):
Anna is: health-conscious (80). Anna prefers water (85).

Low-Level Information (Actions and Events):
[8] Lucky reads book. (bedroom)
[9] Lucky places book. (bedroom)

Conversations:
(no relevant conversations)
```

---

### **STEP 2: Semantic Evaluation** (`reason.py` lines 92-108)

**Goal**: Decide if graph information is sufficient or if video watching is needed

**Process**:
1. **Evaluate Semantic Answer** (`evaluate_semantic_answer`):
   - Input: Question + Graph search results
   - Uses `prompt_semantic_video` to evaluate completeness
   - LLM analyzes the graph information and decides:
     - **[Answer]**: Graph has sufficient information → Return answer immediately
     - **[Search]**: Graph information is insufficient → Need to watch video clips

2. **Parse Response**:
   - Extracts `action` ([Answer] or [Search])
   - Extracts `content` (answer text OR list of clip IDs)
   - Extracts `summary` (if [Search], provides context about what's missing)

**Decision Logic** (`prompt_semantic_video`):
- **Choose [Answer]** if:
  - Graph provides EXACT information (not generic)
  - For location: Specific furniture/container mentioned (not just room)
  - For counting: Explicit counts or all occurrences enumerated
  - For temporal: Clear sequence with clip IDs
  - All parts of multi-part questions answered

- **Choose [Search]** if:
  - Information is generic or incomplete
  - Missing specific details (e.g., "bedroom" but need "bedside table")
  - Counts are vague or incomplete
  - Temporal sequence is unclear
  - Any reasonable doubt exists

**Example Output**:
```
Action: [Search]
Content: [8, 9, 7]
Summary: The graph shows Lucky reading a book at clip 8 and placing it at clip 9, both in the bedroom. However, the specific location within the bedroom (e.g., which furniture or surface) is not captured in the graph...
```

**Early Exit**: If action is [Answer], return immediately with `final_answer = parsed['content']`

---

### **STEP 3: Video Watching** (`reason.py` lines 114-144, `video_processing.py`)

**Goal**: Watch video clips sequentially to find the answer

**Process**:
1. **Extract Clip IDs** (`extract_clip_ids`):
   - Parses clip IDs from content (e.g., `[8, 9, 7]`)
   - Maximum 5 clips allowed

2. **Watch Clips Sequentially** (`watch_video_clips`):
   - Processes clips one by one in order
   - For each clip:
     - Loads frames from `data/frames/{video_name}/{clip_id}/`
     - Builds prompt with:
       - `prompt_video_answer` (for non-last clips) OR `prompt_video_answer_final` (for last clip)
       - Question
       - Current clip ID
       - Previous summaries (accumulated from earlier clips)
     - Sends frames + prompt to MLLM (multimodal LLM)
     - Gets response

3. **Process Each Clip Response**:
   - **For non-last clips**:
     - Parse response: `Action: [Answer]` or `[Search]`
     - If [Answer]: Return immediately with answer
     - If [Search]: Add summary to `previous_summaries` and continue
   - **For last clip**:
     - Response is direct answer (no Action/Content format)
     - Return answer

4. **Accumulate Summaries**:
   - Each [Search] response adds: `"Clip {clip_id}: {summary}"`
   - Summaries passed to next clip for context
   - For counting questions: Summaries include explicit counts per clip

**Example Flow**:
```
Clip 8:
  Input: Question + Graph summary + No previous summaries
  Output: Action: [Search], Content: "In clip 8, Lucky reads the book in the bedroom, but specific location unclear."
  
Clip 9:
  Input: Question + Graph summary + "Clip 8: In clip 8, Lucky reads the book..."
  Output: Action: [Answer], Content: "The book is on the bedside table."
  
→ Return answer immediately
```

**Special Handling**:
- **Counting questions**: Must watch ALL clips before answering (even if answer found early, continue to verify complete count)
- **Location questions**: Continue until specific location visible (not just generic room)
- **Temporal questions**: Continue until complete sequence clear

---

## Complete Flow Diagram

```
Question: "Where is the book Lucky read just now?"
    │
    ▼
┌─────────────────────────────────────┐
│ STEP 1: Parse Query                 │
│ - Extract query_triples              │
│ - Extract spatial_constraint         │
│ - Determine allocation               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ STEP 1: Search Graph                │
│ - Search high-level edges           │
│ - Search low-level edges            │
│ - Search conversations              │
│ → Returns formatted results         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ STEP 2: Semantic Evaluation        │
│ - Analyze graph completeness       │
│ - Decision: [Answer] or [Search]   │
└─────────────────────────────────────┘
    │
    ├─→ [Answer] → Return answer immediately
    │
    └─→ [Search] → Extract clip IDs [8, 9, 7]
            │
            ▼
    ┌─────────────────────────────────────┐
    │ STEP 3: Watch Video Clips           │
    │                                     │
    │ Clip 8:                             │
    │   - Load frames                     │
    │   - Send to MLLM                   │
    │   - Response: [Search]              │
    │   - Add summary to context          │
    │                                     │
    │ Clip 9:                             │
    │   - Load frames                     │
    │   - Send to MLLM (with Clip 8 summary)│
    │   - Response: [Answer]              │
    │   - Return answer                   │
    └─────────────────────────────────────┘
            │
            ▼
    Final Answer: "The book is on the bedside table."
```

---

## Key Components

### **Prompts Used**:
1. `prompt_parse_query`: Converts natural language question → structured search strategy
2. `prompt_semantic_video`: Evaluates if graph information is sufficient
3. `prompt_video_answer`: Processes each video clip (non-last clips)
4. `prompt_video_answer_final`: Processes final video clip

### **Data Structures**:
- **HeteroGraph**: Knowledge graph storing characters, objects, edges, conversations
- **Search Results**: Formatted string with high-level, low-level, and conversation info
- **Clip Summaries**: Accumulated context passed between clips

### **Special Question Types**:
1. **Spatial/Location**: Requires specific furniture/container, not just room name
2. **Temporal Sequence**: Distinguishes instructions vs. actual sequence
3. **Counting**: Must watch all clips, enumerate occurrences per clip

---

## Error Handling

- **Graph search fails**: Raises exception, question marked as error
- **Semantic evaluation fails**: Raises exception, question marked as error
- **Clip folder missing**: Skips clip, continues with next
- **No images in clip**: Skips clip, continues with next
- **All clips watched, no answer**: Returns fallback message with latest information

---

## Performance Considerations

- **Early exit**: If graph has sufficient info, return immediately (no video watching)
- **Parallel processing**: In `run_video_pipeline.sh`, 2 questions processed in parallel
- **Clip limit**: Maximum 5 clips per question to control cost
- **Summary accumulation**: Only relevant information passed between clips
