# Error Analysis: Model Performance on Incorrect Answers

## Executive Summary

Out of **515 total questions**, **251 questions (48.74%) were answered incorrectly**. This analysis examines the root causes, patterns, and failure modes across all incorrect answers to identify systematic issues and propose targeted solutions.

**Overall Accuracy**: 51.26% (264 correct / 515 total)

**Key Observation**: Unlike the previous analysis, **0% of incorrect answers involved video watching** (all answers were generated from graph knowledge only), suggesting that graph-only reasoning has significant limitations that need to be addressed.

---

## Error Distribution

### By Video
- **kitchen_22**: 12 errors (highest)
- **kitchen_15**: 12 errors
- **study_16**: 11 errors
- **living_room_14**: 9 errors
- **meeting_room_03**: 8 errors
- **living_room_12**: 8 errors
- **study_04**: 8 errors
- **kitchen_18**: 8 errors
- **study_09**: 8 errors
- **living_room_01**: 8 errors
- **kitchen_03**: 8 errors
- **living_room_17**: 7 errors
- **living_room_18**: 7 errors
- **bedroom_10**: 6 errors
- **office_02**: 6 errors
- **gym_04**: 6 errors
- **office_04**: 6 errors
- **living_room_10**: 6 errors
- **kitchen_06**: 6 errors
- **study_20**: 6 errors
- **living_room_11**: 6 errors
- **office_06**: 6 errors
- **living_room_06**: 6 errors
- **study_22**: 6 errors
- **kitchen_21**: 6 errors
- **living_room_04**: 5 errors
- **living_room_03**: 5 errors
- **bedroom_02**: 5 errors
- **study_11**: 5 errors
- **living_room_09**: 5 errors
- **living_room_02**: 5 errors
- **office_05**: 4 errors
- **living_room_07**: 4 errors
- **office_08**: 4 errors
- **study_07**: 4 errors
- **bedroom_09**: 4 errors
- **meeting_room_01**: 4 errors
- **gym_01**: 3 errors (lowest among videos with errors)
- **kitchen_08**: 3 errors
- **study_15**: 2 errors
- **study_02**: 2 errors
- **bedroom_11**: 1 error

### By Question Type
- **Multi-Detail Reasoning**: 161 errors (64.1% of all errors)
- **Cross-Modal Reasoning**: 108 errors (43.0% of all errors)
- **General Knowledge Extraction**: 91 errors (36.3% of all errors)
- **Human Understanding**: 61 errors (24.3% of all errors)
- **Multi-Hop Reasoning**: 12 errors (4.8% of all errors)

*Note: Questions can have multiple types, so totals exceed 251.*

---

## Error Category Analysis

### 1. **Temporal Sequence Errors** (68 errors, 27.1%)

**Pattern**: Model fails to understand the order of events, temporal relationships, or sequence of actions.

**Examples**:
- `living_room_04_Q05`: "Should the balloons be put up first?" → Model: "Yes, Betty instructed to put up the red and pink balloons first" | GT: "No, Betty and Linda write some message and draw some pictures on the balloons first"
- `study_15_Q09`: "What did Jennie have for afternoon tea?" → Model: "Strawberry cake and tea" | GT: "Strawberry cake and cookies" (temporal context confusion)
- `study_15_Q10`: "What snack should the robot bring to Lucy?" → Model: "Snacks are not recommended; instead, the robot should bring milk" | GT: "Milk candy" (missed specific item)

**Root Causes**:
- **Storage**: ⚠️ **PARTIAL** - Events stored but temporal relationships not explicitly encoded
- **Retrieval**: ⚠️ **PARTIAL** - Both events retrieved but sequence not prioritized or clip ordering not utilized
- **Reasoning**: ❌ **FAILURE** - Model doesn't analyze temporal order systematically, confuses "should" questions with "what happened" questions

**Severity**: High - Affects 27.1% of all errors (largest category)

---

### 2. **Location/Placement Errors** (67 errors, 26.7%)

**Pattern**: Model fails to identify correct spatial locations or placement instructions.

**Examples**:
- `living_room_04_Q07`: "where is the tape now?" → Model: "On the shelf near the door in the living room" | GT: "On the coffee table"
- `living_room_03_Q01`: "Which place is the last time that robot can get the towel?" → Model: "At the bathroom rack (bathroom hook)" | GT: "On the backrest of the black sofa"
- `living_room_03_Q06`: "Where does Betty's towel need to be placed back?" → Model: "Back into the original place" | GT: "In the bathroom"

**Root Causes**:
- **Storage**: ⚠️ **PARTIAL** - General locations stored but not specific sub-locations (e.g., "living room" vs "coffee table", "bathroom" vs "bathroom rack")
- **Retrieval**: ❌ **FAILURE** - Query parsing doesn't capture fine-grained spatial relationships, "last time" temporal-spatial queries not handled
- **Reasoning**: ❌ **FAILURE** - Model provides generic locations instead of specific placement instructions, doesn't track object movements over time

**Severity**: High - Affects 26.7% of all errors (second largest category)

---

### 3. **Counting Errors** (35 errors, 13.9%)

**Pattern**: Model fails to accurately count occurrences, quantities, or items.

**Examples**:
- `living_room_04_Q08`: "How many pieces of cake were cut in total?" → Model: "At least two pieces of cake were cut in total" | GT: "Four pieces"
- `meeting_room_03_Q04`: "How many times was the air-conditioning remote used?" → Model: "once" | GT: "Twice"
- `meeting_room_03_Q11`: "How many kinds of things were taken from the cabinet?" → Model: "Two kinds of things: a stapler and a document" | GT: "3"

**Root Causes**:
- **Storage**: ⚠️ **PARTIAL** - Actions stored but explicit counts not recorded, multiple actions of same type not aggregated
- **Retrieval**: ⚠️ **PARTIAL** - Relevant clips retrieved but model doesn't aggregate counts across clips or edge types
- **Reasoning**: ❌ **FAILURE** - Model fails to enumerate and count occurrences systematically, provides vague answers ("at least two") instead of exact counts

**Severity**: High - Fundamental reasoning failure affecting quantitative questions

---

### 4. **Other Errors** (67 errors, 26.7%)

**Pattern**: Various other error types including:
- Partial information errors (e.g., `study_15_Q09`: "What did Jennie have for afternoon tea?" → Model: "Strawberry cake and tea" | GT: "Strawberry cake and cookies")
- State/status errors (e.g., `study_20_Q01`: "Is the air conditioner turned on by the robot blowing cold air or warm air?" → Model: "Cold air" | GT: "Warm air")
- Item identification errors (e.g., `study_15_Q10`: "What snack should the robot bring to Lucy?" → Model: "milk" | GT: "Milk candy")
- Boolean/verification errors (e.g., `office_02_Q05`: "Did Emma, Faye and Tom all eat the food brought by Faye?" → Model: "No" | GT: "Yes")

**Root Causes**: Mixed - combination of storage, retrieval, and reasoning issues

**Severity**: Medium - Diverse error types requiring targeted fixes

---

### 5. **Inference/Reasoning Errors** (6 errors, 2.4%)

**Pattern**: Model fails to make implicit inferences or backward reasoning from actions.

**Examples**:
- `living_room_04_Q06`: "What help the robot need to offer?" → Model: "help decorate by securing and adjusting the garland" | GT: "Remove the double-sided tape on the balloon and hand it to Betty"
- `office_02_Q06`: "Which is the document that isn't needed anymore?" → Model: "The incorrect document that Emma asks the robot to put into the shredder" | GT: "The document that was signed early"
- `office_05_Q01`: "What coffee does Marry need?" → Model: "her coffee from Jenny's desk" | GT: "Cappuccino" (missed specific type)

**Root Causes**:
- **Storage**: ⚠️ **PARTIAL** - Forward actions stored but reverse implications not considered, specific task details not captured
- **Retrieval**: ⚠️ **PARTIAL** - General actions retrieved but specific context missing
- **Reasoning**: ❌ **FAILURE** - Model doesn't apply common-sense reasoning, provides generic answers instead of specific tasks

**Severity**: Medium - Requires common-sense and backward reasoning

---

### 6. **Specific Detail Missing** (8 errors, 3.2%)

**Pattern**: Model misses very specific details or tasks that require fine-grained information.

**Examples**:
- `kitchen_15_Q03`: "What is the purpose of soaking the turkey in the sink?" → Model: "N/A" | GT: "Thawing"
- Questions requiring very specific object properties or purposes

**Root Causes**:
- **Storage**: ❌ **FAILURE** - Fine-grained details not stored (e.g., "purpose of soaking" not captured)
- **Retrieval**: ❌ **FAILURE** - Query doesn't retrieve specific context
- **Reasoning**: N/A (information not available)

**Severity**: Medium - Could be addressed by improving storage granularity

---

## Detailed Error Breakdown by Root Cause

### Storage Issues (Information Not Stored)
- **Count**: ~80-100 errors (32-40%)
- **Primary Issues**:
  - Fine-grained details not captured (e.g., specific sub-locations, exact counts, object purposes)
  - Temporal relationships not explicitly stored
  - Object movement tracking incomplete (where objects are "now" vs where they were)
  - Implicit relationships not encoded

### Retrieval Issues (Information Not Retrieved)
- **Count**: ~100-120 errors (40-48%)
- **Primary Issues**:
  - Query parsing doesn't capture fine-grained spatial relationships
  - Temporal-spatial queries ("last time", "now") not handled
  - Multi-hop retrieval not performed for specific details
  - Context expansion missing (e.g., retrieving "balloon" but not "tape on balloon")
  - Temporal sequence not prioritized in retrieval
  - Counting queries don't aggregate across edges/clips

### Reasoning Issues (Information Available But Incorrectly Processed)
- **Count**: ~180-200 errors (72-80%)
- **Primary Issues**:
  - Counting failures (not enumerating systematically, providing vague ranges)
  - Temporal sequence not analyzed (confusing "should" with "what happened")
  - Implicit reasoning not applied (backward reasoning, common sense)
  - Generic answers instead of specific details
  - Incomplete synthesis of multiple information sources
  - Object tracking failures (not tracking where objects are "now")

**Key Insight**: While storage and retrieval have issues, **reasoning failures are the dominant problem**, affecting 72-80% of all errors. The model often has access to relevant information but fails to process it correctly, especially in graph-only mode without video watching.

---

## Video Watch Analysis

### Questions with Video Watches
- **Total**: 251 incorrect answers
- **With video watches**: 0 errors (0%)
- **Without video watches**: 251 errors (100%)

**Critical Observation**: **ALL incorrect answers occurred in graph-only reasoning mode** (no video watching). This suggests:
1. Graph-only reasoning has significant limitations
2. The model may need video watching for many questions that currently fail
3. Graph knowledge may be incomplete or insufficient for certain question types
4. The reasoning prompts for graph-only mode may need enhancement

**Comparison with Previous Analysis**:
- Previous: ~42-51% of errors had video watches
- Current: 0% of errors had video watches
- **Implication**: Graph-only reasoning is less effective than graph + video watching

---

## Pattern Analysis by Question Type

### Multi-Detail Reasoning (161 errors, 64.1%)
**Characteristics**:
- Requires synthesizing multiple pieces of information
- Often involves counting, listing, or combining details
- **Common Failures**:
  - Incomplete enumeration (missing items in lists)
  - Counting errors (vague ranges instead of exact counts)
  - Generic answers instead of specific details
  - Partial information extraction

**Example**: `study_15_Q09`: "What did Jennie have for afternoon tea?" → Model lists some items but misses others

### Cross-Modal Reasoning (108 errors, 43.0%)
**Characteristics**:
- Requires combining visual and textual information
- Often involves understanding actions, states, or relationships
- **Common Failures**:
  - Misinterpreting context (confusing temporal contexts)
  - Not connecting actions with their purposes
  - Missing implicit relationships
  - Graph-only mode lacks visual context

**Example**: `living_room_04_Q05`: "Should the balloons be put up first?" → Model confuses instruction order with actual sequence

### General Knowledge Extraction (91 errors, 36.3%)
**Characteristics**:
- Requires extracting factual information from memory
- Often involves locations, objects, or states
- **Common Failures**:
  - Generic locations instead of specific ones
  - Missing fine-grained details
  - Incorrect state identification
  - Object tracking failures ("where is X now?")

**Example**: `living_room_04_Q07`: "where is the tape now?" → Model provides wrong location

### Human Understanding (61 errors, 24.3%)
**Characteristics**:
- Requires understanding motivations, emotions, or character traits
- Often involves inferring from behavior or conversations
- **Common Failures**:
  - Partial understanding of motivations
  - Missing key emotional context
  - Over-generalization
  - Graph-only mode may miss visual cues

**Example**: Various questions where model provides partial or incorrect character understanding

---

## Proposed Solutions

### 1. **Improve Temporal Sequence Understanding** (High Priority)

**Problem**: Model fails to understand event order (68 errors, 27.1%)

**Solutions**:
- **Temporal Edge Storage**: Store explicit temporal relationships (e.g., "drawing on balloons" BEFORE "putting up balloons")
- **Sequence Prompting**: Update `prompt_semantic_answer_only` to explicitly ask: "What happens first? What happens second? Identify the sequence."
- **Clip Ordering**: Use `clip_id` ordering to infer temporal relationships in graph search
- **Temporal Reasoning Step**: Add explicit temporal analysis in reasoning pipeline
- **Distinguish Question Types**: Separate "should" questions (instructions) from "what happened" questions (actual sequence)

**Implementation Priority**: High (affects 27.1% of errors - largest category)

---

### 2. **Enhance Spatial/Location Understanding** (High Priority)

**Problem**: Model provides generic locations instead of specific placements (67 errors, 26.7%)

**Solutions**:
- **Granular Storage**: Store fine-grained spatial relationships (e.g., "in cabinet", "left side of wardrobe", "below dressing table", "on coffee table")
- **Query Parsing Enhancement**: Improve `prompt_parse_query` to capture spatial modifiers (e.g., "below", "left side", "inside", "now", "last time")
- **Multi-hop Spatial Retrieval**: When retrieving locations, also retrieve sub-locations and spatial relationships
- **Context Expansion**: When retrieving an object, also retrieve its container and spatial context
- **Object Tracking**: Track object movements over time to answer "where is X now?" questions

**Implementation Priority**: High (affects 26.7% of errors - second largest category)

---

### 3. **Improve Counting Capabilities** (High Priority)

**Problem**: Model fails to count occurrences accurately (35 errors, 13.9%)

**Solutions**:
- **Enhanced Prompting**: Add explicit instructions to enumerate each occurrence before counting
  - Update `prompt_semantic_answer_only`: "When counting, explicitly list each instance: 1) [instance 1], 2) [instance 2], etc. Then provide the exact total count."
- **Post-processing Verification**: Add a counting verification step that requires explicit enumeration
- **Graph Structure**: Consider storing counts as explicit high-level edges when possible
- **Aggregation Logic**: Ensure counting logic aggregates across all relevant edges and clips
- **Forbid Vague Answers**: Explicitly forbid answers like "at least X" or "more than X" - require exact counts

**Implementation Priority**: High (affects 13.9% of errors)

---

### 4. **Enhance Graph-Only Reasoning** (High Priority)

**Problem**: 100% of errors occurred in graph-only mode, suggesting limitations in graph knowledge or reasoning

**Solutions**:
- **Improve Graph Completeness**: Ensure all relevant information is stored in the graph
- **Enhance Reasoning Prompts**: Update `prompt_semantic_answer_only` to be more explicit about:
  - Enumerating all relevant information before answering
  - Verifying completeness of retrieved information
  - Making reasonable inferences when information is partial
- **Multi-hop Reasoning**: Implement explicit multi-hop reasoning steps in graph search
- **Context Expansion**: When initial search is insufficient, expand context and search again
- **Consider Video Watching**: For questions where graph knowledge is insufficient, trigger video watching

**Implementation Priority**: High (affects all 251 errors)

---

### 5. **Improve Fine-Grained Detail Storage** (Medium Priority)

**Problem**: Specific details not stored or retrieved (8 errors, 3.2%, but likely contributes to more)

**Solutions**:
- **Episodic Memory Enhancement**: Review `prompt_generate_episodic_memory` to ensure fine-grained actions are captured (e.g., "remove double-sided tape", "purpose of soaking turkey")
- **Multi-hop Retrieval**: When specific detail missing, perform multi-hop search
- **Context Expansion**: When retrieving objects, also retrieve associated actions, purposes, and modifications
- **Detail Verification**: Add a step to check if retrieved information contains required level of detail

**Implementation Priority**: Medium (affects 3.2% directly, but could prevent many more)

---

### 6. **Enhance Multi-Detail Synthesis** (Medium Priority)

**Problem**: Model struggles to synthesize multiple pieces of information (affects Multi-Detail Reasoning questions - 161 errors)

**Solutions**:
- **Structured Reasoning**: Break complex questions into sub-questions, answer each, then synthesize
- **Verification Step**: Before finalizing answer, verify all retrieved information has been considered
- **Explicit Enumeration**: Require model to list all relevant information before synthesizing
- **Weighted Synthesis**: When multiple sources relevant, explicitly weight and combine them
- **Completeness Check**: Add explicit check: "Have I considered all relevant information? Am I missing any items?"

**Implementation Priority**: Medium (affects 64.1% of errors - Multi-Detail Reasoning)

---

### 7. **Enhance Implicit Reasoning** (Medium Priority)

**Problem**: Model fails to make backward inferences (6 errors, 2.4%)

**Solutions**:
- **Common Sense Prompting**: Add instructions: "Consider implicit consequences: if an object was taken from location X, where should it be returned?"
- **Bidirectional Retrieval**: When retrieving actions, also retrieve reverse actions or consequences
- **Graph Expansion**: Store implicit relationships as high-level edges when possible
- **Reasoning Chain**: Explicitly prompt backward reasoning: "Trace back: where was this item originally? Where should it be returned?"

**Implementation Priority**: Medium (affects 2.4% of errors, but could prevent more)

---

## Priority Recommendations

### Immediate Actions (High Impact, High Feasibility)

1. **Fix Temporal Sequence Errors** (27.1% of errors)
   - Add temporal relationship storage
   - Enhance sequence reasoning in prompts
   - Distinguish instruction questions from sequence questions
   - **Expected Impact**: Fix 50-60 errors

2. **Enhance Spatial Understanding** (26.7% of errors)
   - Improve query parsing for spatial modifiers
   - Add multi-hop spatial retrieval
   - Implement object tracking for "now" queries
   - **Expected Impact**: Fix 50-60 errors

3. **Fix Counting Errors** (13.9% of errors)
   - Add explicit enumeration instructions to prompts
   - Add counting verification step
   - Forbid vague counting answers
   - **Expected Impact**: Fix 25-30 errors

4. **Enhance Graph-Only Reasoning** (affects all errors)
   - Improve reasoning prompts for completeness
   - Add multi-hop reasoning steps
   - Consider triggering video watching when graph knowledge insufficient
   - **Expected Impact**: Fix 30-50 errors

### Short-term Actions (Medium-High Impact)

5. **Enhance Multi-Detail Synthesis** (64.1% of errors)
   - Structured reasoning framework
   - Synthesis verification
   - **Expected Impact**: Fix 40-60 errors

6. **Improve Detail Storage** (3.2% direct, but prevents more)
   - Enhance episodic memory extraction
   - Add multi-hop retrieval
   - **Expected Impact**: Fix 10-20 errors (including prevention)

### Long-term Actions (Systematic Improvements)

7. **Enhance Implicit Reasoning** (2.4% of errors)
   - Add backward reasoning instructions
   - Store implicit relationships
   - **Expected Impact**: Fix 5-10 errors

---

## Testing Recommendations

After implementing solutions, test specifically on:

1. **Temporal Questions** (68 known errors)
   - Event sequences, "first/before/after" questions, "should" vs "what happened"
   - Verify temporal reasoning and sequence understanding

2. **Location Questions** (67 known errors)
   - Specific placements, sub-locations, spatial relationships, "where is X now?"
   - Verify fine-grained spatial understanding and object tracking

3. **Counting Questions** (35 known errors)
   - Place changes, quantities, item counts
   - Verify enumeration, aggregation, and exact counting

4. **Multi-Detail Questions** (161 known errors)
   - Lists, combinations, synthesis
   - Verify complete enumeration and synthesis

5. **Graph-Only Reasoning** (all 251 errors)
   - Test if enhanced reasoning improves graph-only performance
   - Consider when video watching should be triggered

**Success Metrics**:
- Overall accuracy improvement from 51.26% to >65%
- Reduction in temporal errors from 68 to <20
- Reduction in location errors from 67 to <20
- Reduction in counting errors from 35 to <10
- Improvement in graph-only reasoning effectiveness

---

## Conclusion

The analysis reveals several critical issues:

1. **Graph-only reasoning limitations**: 100% of errors occurred without video watching, suggesting that graph knowledge alone is insufficient for many questions. This is a fundamental limitation that needs addressing.

2. **Temporal understanding is the biggest challenge** (27.1% of errors) - the model struggles with event sequences, confusing instructions with actual sequences, and temporal relationships.

3. **Spatial understanding remains problematic** (26.7% of errors) - generic locations instead of specific placements, and object tracking failures.

4. **Counting failures** (13.9% of errors) - model provides vague ranges instead of exact counts, suggesting incomplete enumeration.

5. **Reasoning failures dominate** (72-80% of errors) - even when information is stored and retrieved, the model fails to process it correctly.

**Key Differences from Previous Analysis**:
- **Larger dataset**: 515 questions vs 129 (4x larger)
- **Lower accuracy**: 51.26% vs 54.26%
- **No video watching**: 0% vs ~42-51% (all graph-only)
- **Different error distribution**: Temporal errors are now largest (27.1% vs 11.9%), location errors similar (26.7% vs 28.8%)

Targeted improvements to prompts, reasoning pipelines, storage mechanisms, and consideration of when to trigger video watching should address these systematic failures and significantly improve overall accuracy.
