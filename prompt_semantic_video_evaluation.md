# Critical Evaluation: prompt_semantic_video

## Major Issues

### 1. **Ambiguous Decision Criteria** (CRITICAL)
**Problem**: The decision criteria are vague and contradictory:
- Line 544: "Answer directly ([Answer]) when the current graph information provides a clear answer... You should make reasonable deductions and inferences"
- Line 545: "Search video memory ([Search]) only when the extracted information is fundamentally insufficient"

**Issue**: What constitutes "reasonable deductions"? When is information "fundamentally insufficient"? The model has no clear threshold, leading to:
- Over-confidence: Answering with generic information when specific details are needed
- Under-confidence: Searching when graph information is actually sufficient

**Evidence from errors**: 100% of errors occurred in graph-only mode, suggesting the model is choosing [Answer] too frequently when it should choose [Search].

**Fix**: Add explicit decision tree:
```
Choose [Answer] ONLY if:
1. The graph provides EXACT information matching the question (not generic approximations)
2. For location questions: specific furniture/container is mentioned (not just room)
3. For counting questions: explicit counts or all occurrences clearly enumerated
4. For temporal questions: clear sequence with clip IDs showing order
5. NO inference or deduction required beyond simple lookup

Choose [Search] if:
1. Information is generic (e.g., "bedroom" instead of "bedside table")
2. Counts are incomplete or require aggregation
3. Temporal sequence is unclear or missing events
4. Any reasonable doubt exists about completeness
```

### 2. **Missing Explicit Verification Step** (CRITICAL)
**Problem**: The prompt doesn't require the model to verify completeness before choosing [Answer].

**Evidence**: Many errors show partial information extraction (e.g., "Strawberry cake and tea" missing "cookies").

**Fix**: Add mandatory verification step before [Answer]:
```
Before choosing [Answer]:
1. List ALL relevant information from the graph
2. Verify this information directly answers the question
3. Check if any information is missing or ambiguous
4. For multi-part questions, verify ALL parts are answered
```

### 3. **Insufficient Guidance on Clip Selection** (HIGH)
**Problem**: The clip selection guidance is too vague:
- "ranked by relevance" - what does relevance mean?
- "clips before and after if necessary" - when is it necessary?
- No guidance on prioritizing clips when limit is 5

**Evidence**: Counting errors suggest clips between events aren't always included.

**Fix**: Add explicit clip selection rules:
```
Clip Selection Priority (max 5 clips):
1. Primary clips: All clips where the key event/object appears
2. Temporal context: Clips immediately before/after key events (for sequence questions)
3. Gap filling: Clips between two mentioned events (for counting)
4. Rank by: Temporal proximity to key events, then relevance
5. If >5 clips needed, prioritize clips with most relevant information
```

### 4. **Weak Counting Instructions** (HIGH)
**Problem**: Counting instructions don't emphasize systematic enumeration.

**Evidence**: 35 counting errors, many with vague answers like "at least two" instead of exact counts.

**Fix**: Strengthen counting section:
```
For Counting Questions:
- NEVER answer with vague ranges ("at least X", "more than X")
- ALWAYS enumerate explicitly: "In clip X: 1 occurrence, in clip Y: 2 occurrences, total: 3"
- If ANY doubt exists about completeness, choose [Search]
- When [Search], include ALL clips where event occurs PLUS clips between them
- Summary MUST list each occurrence with clip ID and count
```

### 5. **Temporal Sequence Ambiguity** (HIGH)
**Problem**: The distinction between "should" (instructions) and "what happened" (actual sequence) is mentioned but not emphasized enough.

**Evidence**: 68 temporal sequence errors, many confusing instruction order with actual sequence.

**Fix**: Make distinction more prominent:
```
Temporal Sequence Questions - CRITICAL DISTINCTION:
- "Should X be done first?" = INSTRUCTION question → Look for instructions, not actual sequence
- "What happened before/after X?" = ACTUAL sequence question → Look for actual events in order
- "What did X do first?" = ACTUAL sequence question → Look for first action chronologically
- When in doubt about instruction vs. actual, choose [Search] and include clips showing both
```

### 6. **Location Question Handling Too Restrictive** (MEDIUM)
**Problem**: The rule "Generic room names alone are INSUFFICIENT" might be too strict for some questions.

**Evidence**: Some questions might legitimately be answerable with room-level information if that's what's asked.

**Fix**: Clarify when generic is acceptable:
```
Spatial/Location Questions:
- Generic room names are INSUFFICIENT if question asks for specific placement (e.g., "where is the book?" → needs furniture)
- Generic room names ARE sufficient if question asks for general location (e.g., "which room is X in?" → room name is fine)
- When question includes "now", "last time", or "placed", require specific location
- When question includes "which place", "where", check if context requires specificity
```

### 7. **Missing Multi-Part Question Handling** (MEDIUM)
**Problem**: No guidance for questions requiring multiple pieces of information.

**Evidence**: 161 Multi-Detail Reasoning errors (64.1% of all errors).

**Fix**: Add section:
```
Multi-Part Questions:
- Break down question into components
- Verify graph has information for EACH component
- If ANY component is missing or ambiguous, choose [Search]
- When [Answer], ensure ALL parts are addressed in the response
- Example: "What did X have for tea?" requires: all items, not just some
```

### 8. **Summary Quality Not Enforced** (MEDIUM)
**Problem**: Summary instructions are descriptive but don't enforce quality standards.

**Evidence**: Summaries might not provide enough context for video watching.

**Fix**: Add quality requirements:
```
Summary Requirements (when [Search]):
- MUST include: What information is available, what is missing, why video is needed
- MUST include: Relevant clip IDs mentioned in summary
- MUST include: Key events/objects with their clip IDs
- MUST exclude: Irrelevant character attributes, relationships, conversations
- Format: "The graph shows [available info]. However, [missing info] requires video inspection. In clip X, [event]. In clip Y, [event]."
```

### 9. **No Explicit Error Prevention** (MEDIUM)
**Problem**: Prompt doesn't warn against common error patterns.

**Evidence**: Error analysis shows specific patterns (vague counts, generic locations, partial information).

**Fix**: Add "Common Pitfalls" section:
```
Common Pitfalls to Avoid:
1. DO NOT answer with vague counts ("at least X") - require exact numbers
2. DO NOT answer location questions with generic rooms if specific placement is needed
3. DO NOT answer multi-part questions partially - verify all parts answered
4. DO NOT confuse instruction order with actual sequence
5. DO NOT choose [Answer] if any reasonable doubt exists - prefer [Search]
```

### 10. **Example Quality Issues** (LOW-MEDIUM)
**Problems**:
- Examples don't show edge cases (e.g., when to choose [Search] for seemingly complete information)
- Missing example of multi-part question requiring [Search]
- Missing example showing when generic location is acceptable

**Fix**: Add more diverse examples:
- Example where graph seems complete but [Search] is correct (e.g., generic location)
- Example of multi-part question requiring [Search]
- Example showing systematic counting enumeration

## Recommended Priority Fixes

### Immediate (High Impact):
1. Add explicit decision tree for [Answer] vs [Search]
2. Add mandatory verification step before [Answer]
3. Strengthen counting instructions with explicit enumeration requirement
4. Add explicit clip selection priority rules

### Short-term (Medium Impact):
5. Clarify temporal sequence distinction (instructions vs. actual)
6. Add multi-part question handling
7. Add "Common Pitfalls" section
8. Improve example diversity

### Long-term (Lower Impact):
9. Refine location question rules
10. Enhance summary quality requirements

## Structural Improvements

### Suggested Prompt Structure:
1. **Clear Decision Tree** (replace vague criteria)
2. **Verification Checklist** (mandatory before [Answer])
3. **Special Question Types** (current, but enhanced)
4. **Clip Selection Rules** (explicit priority system)
5. **Common Pitfalls** (error prevention)
6. **Examples** (more diverse, including edge cases)
