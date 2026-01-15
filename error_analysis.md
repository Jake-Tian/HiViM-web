# Error Analysis: Model Performance on Incorrect Answers

## Summary
Out of the questions analyzed, **5 questions were answered incorrectly**. This analysis examines the root causes and patterns in these failures.

---

## Detailed Error Analysis

### 1. **gym_01_Q07**: Counting Error - Place Changes
**Question**: "How many times do Susan and Anna change places during the table tennis game?"

**Model Answer**: "Susan and Anna change places once during the table tennis game in this clip."

**Ground Truth**: "Twice"

**Retrieval Results**: 
- Retrieved relevant clips [18, 12, 13, 25, 27]
- Found conversations about playing table tennis
- Retrieved interactions between Anna and Susan

**Root Cause**: 
- **Memory Storage**: ✅ Information was stored correctly (conversations mention place changes)
- **Retrieval**: ✅ Relevant clips were retrieved
- **Reasoning**: ❌ **FAILURE** - The model failed to count the number of place changes correctly. The reasoning mentions two separate instances but the model only counted one.

**Question Type**: Multi-Detail Reasoning, Cross-Modal Reasoning

---

### 2. **gym_01_Q10**: Inference/Reasoning Error - Object Location
**Question**: "Where should the robot place the towels?"

**Model Answer**: "The robot should place the towels on the bench next to the bag."

**Ground Truth**: "In Susan's bag"

**Retrieval Results**:
- Retrieved clip 39: "Susan asked Tom to take two towels from her bag"
- Retrieved general robot actions and towel-related information
- Missing: Explicit information about where to place towels back

**Root Cause**:
- **Memory Storage**: ✅ Information about taking towels from bag was stored
- **Retrieval**: ⚠️ **PARTIAL** - Retrieved the action of taking towels but missed the implicit need to return them
- **Reasoning**: ❌ **FAILURE** - The model failed to infer that if towels were taken from a bag, they should be placed back in the bag. This requires backward reasoning from the action.

**Question Type**: General Knowledge Extraction

---

### 3. **living_room_04_Q05**: Temporal Sequence Error
**Question**: "Should the balloons be put up first?"

**Model Answer**: "Yes, the balloons should be put up first according to Betty's instructions."

**Ground Truth**: "No, Betty and Linda write some message and draw some pictures on the balloons first."

**Retrieval Results**:
- Retrieved information about balloons being put up
- Retrieved Betty's instruction: "the red and the pink go first"
- Retrieved conversations about drawing on balloons (Conversation 3: "we can write some message on the balloons and draw some interesting pictures on them")
- Retrieved information about sticking balloons on the wall

**Root Cause**:
- **Memory Storage**: ✅ Information about drawing on balloons was stored in conversations
- **Retrieval**: ⚠️ **PARTIAL** - Retrieved both pieces of information but didn't prioritize temporal sequence
- **Reasoning**: ❌ **FAILURE** - The model failed to understand the temporal sequence: drawing on balloons happens BEFORE putting them up. It focused on Betty's instruction about color order but missed the step sequence.

**Question Type**: Cross-Modal Reasoning, General Knowledge Extraction

---

### 4. **living_room_04_Q06**: Specific Context Missing
**Question**: "What does the robot need to offer?"

**Model Answer**: "The robot needs to help hang the string of lights on the wall."

**Ground Truth**: "Remove the double-sided tape on the balloon and hand it to Betty."

**Retrieval Results**:
- Retrieved general robot actions (holding items, helping with decorations)
- Retrieved clips [6, 8, 12, 19, 30, 31, 54, 5, 9, 3]
- Retrieved conversations about decorations and tasks
- **Missing**: Specific information about double-sided tape on balloons

**Root Cause**:
- **Memory Storage**: ❌ **FAILURE** - The specific action of removing double-sided tape from balloons was likely not stored as a low-level edge or was stored with insufficient detail
- **Retrieval**: ❌ **FAILURE** - The query didn't retrieve the specific context about tape on balloons. The model retrieved general robot assistance but missed the specific task.
- **Reasoning**: N/A (information not available)

**Question Type**: Multi-Detail Reasoning

---

### 5. **living_room_04_Q08**: Counting Error - Cake Pieces
**Question**: "How many pieces of cake were cut?"

**Model Answer**: "A total of three pieces of cake were cut."

**Ground Truth**: "Four pieces"

**Retrieval Results**:
- Retrieved clips [64, 72, 75, 79] related to cake cutting
- Retrieved information about Linda cutting cake
- Retrieved information about Cindy, Daisy, and Betty eating cake
- **Missing**: Explicit count of pieces or information about Daisy cutting an additional piece

**Root Cause**:
- **Memory Storage**: ⚠️ **PARTIAL** - Information about cake cutting was stored, but the specific count or Daisy's additional cut may not have been explicitly stored
- **Retrieval**: ⚠️ **PARTIAL** - Retrieved relevant clips but may have missed the detail about Daisy cutting one more piece for Cindy
- **Reasoning**: ❌ **FAILURE** - The model failed to count correctly: Linda cut 3 pieces (for herself, Cindy, Betty) + Daisy cut 1 more piece for Cindy = 4 total

**Question Type**: Multi-Detail Reasoning

---

## Pattern Analysis

### Question Types Most Difficult for the Model:

1. **Multi-Detail Reasoning** (4 out of 5 errors)
   - Counting tasks (2 errors)
   - Complex multi-step tasks (2 errors)

2. **General Knowledge Extraction** (2 out of 5 errors)
   - Implicit reasoning about object locations
   - Temporal sequence understanding

3. **Cross-Modal Reasoning** (1 out of 5 errors)
   - Understanding sequence of actions

### Root Cause Categories:

1. **Counting Errors** (2 errors - Q07, Q08)
   - **Issue**: Model fails to accurately count occurrences or quantities
   - **Examples**: Place changes, cake pieces
   - **Severity**: High - Fundamental reasoning failure

2. **Temporal Sequence Errors** (1 error - Q05)
   - **Issue**: Model fails to understand the order of events
   - **Example**: Drawing on balloons before putting them up
   - **Severity**: High - Affects understanding of process flows

3. **Inference/Backward Reasoning Errors** (1 error - Q10)
   - **Issue**: Model fails to infer implicit information from explicit actions
   - **Example**: If towels were taken from bag, they should be returned to bag
   - **Severity**: Medium-High - Requires common sense reasoning

4. **Missing Specific Context** (1 error - Q06)
   - **Issue**: Specific details not stored or not retrieved
   - **Example**: Double-sided tape removal task
   - **Severity**: Medium - Could be storage or retrieval issue

### Storage vs. Retrieval vs. Reasoning Breakdown:

- **Storage Issues**: 1 error (Q06 - specific context missing)
- **Retrieval Issues**: 2 errors (Q10 - partial retrieval, Q06 - missing context)
- **Reasoning Issues**: 5 errors (all questions - counting, temporal, inference failures)

**Key Insight**: While storage and retrieval have some issues, the primary failure mode is **reasoning** - the model struggles to:
- Count accurately
- Understand temporal sequences
- Make implicit inferences
- Synthesize multiple pieces of information correctly

---

## Proposed Solutions

### 1. **Improve Counting Capabilities**

**Problem**: Model fails to count occurrences accurately (place changes, cake pieces)

**Solutions**:
- **Enhanced Prompting**: Add explicit instructions in the reasoning prompt to count occurrences step-by-step
- **Post-processing**: Add a counting verification step that explicitly lists all occurrences before finalizing the count
- **Graph Structure**: Consider storing counts as explicit high-level edges (e.g., "Susan and Anna change places: 2 times")
- **Iterative Counting**: In the reasoning process, explicitly enumerate each occurrence before providing the final count

**Implementation**:
- Update `prompt_semantic_video` and `prompt_video_answer` to include: "When counting occurrences, explicitly list each instance before providing the final count"
- Add a counting verification step in the reasoning pipeline

---

### 2. **Enhance Temporal Sequence Understanding**

**Problem**: Model fails to understand the order of events (drawing before putting up balloons)

**Solutions**:
- **Temporal Edge Storage**: Store temporal relationships explicitly (e.g., "drawing on balloons" happens BEFORE "putting up balloons")
- **Sequence Prompting**: In prompts, explicitly ask the model to identify the sequence of events
- **Graph Enhancement**: Add temporal edges or clip_id ordering information to help understand sequences
- **Multi-step Reasoning**: Break down questions about sequences into explicit step-by-step analysis

**Implementation**:
- Modify `insert_triples` to store temporal relationships when actions are sequential
- Update prompts to include: "Identify the sequence of events. What happens first, second, etc.?"
- Consider adding a `temporal_order` field to edges or creating separate temporal relationship edges

---

### 3. **Improve Implicit Reasoning**

**Problem**: Model fails to make backward inferences (if towels taken from bag, return to bag)

**Solutions**:
- **Common Sense Prompting**: Add instructions to consider implicit consequences of actions
- **Bidirectional Reasoning**: When retrieving actions, also retrieve related reverse actions or consequences
- **Graph Expansion**: Store implicit relationships (e.g., "if X is taken from Y, then X should be returned to Y")
- **Reasoning Chain**: Explicitly prompt the model to reason backward: "If item was taken from location, where should it be returned?"

**Implementation**:
- Update reasoning prompts to include: "Consider implicit consequences: if an object was taken from a location, where should it be returned?"
- Add a reasoning step that checks for reverse actions or implicit relationships
- Consider storing common-sense rules as high-level knowledge edges

---

### 4. **Improve Specific Context Retrieval**

**Problem**: Model misses specific details (double-sided tape removal)

**Solutions**:
- **More Granular Storage**: Store more detailed low-level edges (e.g., "Linda applies double-sided tape to balloon", "tape needs to be removed")
- **Better Query Parsing**: Improve query parsing to capture specific object-verb combinations
- **Multi-hop Retrieval**: When a specific detail is missing, perform multi-hop retrieval (e.g., find balloons → find tape on balloons → find removal task)
- **Context Expansion**: When retrieving information, also retrieve related context (e.g., when retrieving "balloon", also retrieve "tape on balloon")

**Implementation**:
- Review the episodic memory extraction prompt to ensure it captures fine-grained details
- Improve the search function to perform multi-hop retrieval when initial results are insufficient
- Add a context expansion step in retrieval that finds related objects/actions

---

### 5. **Enhance Multi-Detail Synthesis**

**Problem**: Model struggles to synthesize multiple pieces of information correctly

**Solutions**:
- **Structured Reasoning**: Break down complex questions into sub-questions and answer each before synthesizing
- **Verification Step**: Add a verification step that checks if all retrieved information has been considered
- **Weighted Synthesis**: When multiple pieces of information are relevant, explicitly weight and combine them
- **Explicit Enumeration**: Before finalizing an answer, explicitly list all relevant pieces of information found

**Implementation**:
- Update reasoning prompts to include: "Before answering, list all relevant information found. Then synthesize to provide the final answer"
- Add a synthesis verification step in the reasoning pipeline
- Consider adding a structured reasoning format that separates information gathering from synthesis

---

## Priority Recommendations

### High Priority (Address First):
1. **Fix Counting Errors** - Most common error type (2/5)
   - Add explicit counting instructions to prompts
   - Add counting verification step

2. **Improve Temporal Sequence Understanding** - Affects process understanding
   - Add temporal relationship storage
   - Enhance sequence reasoning in prompts

### Medium Priority:
3. **Enhance Implicit Reasoning** - Improves common sense understanding
   - Add backward reasoning instructions
   - Store implicit relationships

4. **Improve Specific Context Retrieval** - Reduces missing information
   - Enhance granularity of stored information
   - Add multi-hop retrieval

### Lower Priority:
5. **Enhance Multi-Detail Synthesis** - Improves complex reasoning
   - Add structured reasoning format
   - Add synthesis verification

---

## Testing Recommendations

After implementing solutions, test specifically on:
- Counting questions (place changes, quantities)
- Temporal sequence questions (order of events)
- Implicit reasoning questions (object locations, consequences)
- Multi-detail questions (synthesizing multiple pieces of information)

Monitor for improvements in these specific question types.
