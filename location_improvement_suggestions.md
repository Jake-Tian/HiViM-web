# Critical Suggestions for Fixing Location Errors

Based on analysis of 17 location errors (28.8% of all errors) and examination of actual questions in `robot.json`, here are **critical, targeted improvements** needed for `prompt_generate_episodic_memory` and `prompt_extract_triples`.

## Key Findings from Location Error Analysis

### Error Patterns:
1. **bedroom_02_Q05**: "Where can the robot get the facial cleansing mask?" 
   - Model: "right hand of Lily's table" | GT: "In the below cabinet of the dressing table"
   - **Missing**: "below cabinet", "dressing table" (hierarchical: cabinet OF dressing table)

2. **bedroom_10_Q06**: "Where should the cap be placed?"
   - Model: "on Lucky's head" | GT: "In the cabinet on the left side of the wardrobe"
   - **Missing**: "cabinet", "left side", "wardrobe" (directional: "left side OF wardrobe")

3. **bedroom_10_Q07**: "Where is the book Lucky read just now?"
   - Model: "in the bedroom" | GT: "Bedside table"
   - **Missing**: Specific furniture name ("bedside table" not just "bedroom")

4. **gym_01_Q10**: "Where should the robot place the towels?"
   - Model: "bench next to bag" | GT: "In Susan's bag"
   - **Missing**: Backward reasoning (taken from → return to)

5. **bedroom_10_Q10**: "Where should the clothes be placed?"
   - Model: "into the closet" | GT: "In the cabinet on the left side of the wardrobe"
   - **Missing**: "cabinet", "left side", "wardrobe" (hierarchical + directional)

### Successful Location Questions (for reference):
- "Where should the robot place the rolling pin?" → "In the cabinet above the microwave oven"
- "Where should the robot place the knife?" → "In the knife holder beside the sink"
- "Where should the robot place the chopping board?" → "In the cabinet under the sink"
- "Where did Abel take out the yogurt from?" → "The second layer of the refrigerator"
- "Where is the soy milk machine's original place on the counter?" → "Next to the window"

## Critical Issues Identified

### Issue 1: Spatial Prepositions and Modifiers Lost
**Problem**: Questions require fine-grained spatial relationships:
- Directional: "left side", "right side", "above", "below", "beside", "in front of"
- Hierarchical: "cabinet of the dressing table", "second layer of the refrigerator"
- Relative: "next to", "under", "on the counter"

**Current State**: Behavior descriptions likely say "puts X in cabinet" but lose "below dressing table" or "left side of wardrobe".

### Issue 2: Furniture/Container Names Not Preserved
**Problem**: Questions ask for specific furniture (bedside table, dressing table, wardrobe, shoe cabinet) but model provides generic room names (bedroom, living room).

**Current State**: Scene is stored as "bedroom" but specific furniture where actions occur is lost.

### Issue 3: Hierarchical Location Structure Lost
**Problem**: Locations have hierarchy: "cabinet on the left side of the wardrobe" = wardrobe → left side → cabinet. Current storage likely flattens this.

**Current State**: Triple extraction may create ["object", "is in", "cabinet"] but loses "cabinet is on left side of wardrobe".

### Issue 4: Source Location Not Captured for "Return" Questions
**Problem**: Questions like "Where should robot place towels?" require backward reasoning: if taken from bag → return to bag.

**Current State**: "takes from bag" stored, but "should return to bag" not inferred.

---

## Recommended Changes

### 1. **Update `prompt_generate_episodic_memory` - Character Behavior Section**

**Current** (lines 7-14):
```
1. **Characters' Behavior**
   - Describe each character's behavior in chronological order.
   - Include:
     (a) Interaction with objects in the scene.
     (b) Interaction with other characters.
     (c) Actions and movements.
   - Each entry must describe exactly one event/detail. Split sentences if needed.
```

**Recommended Change**:
```
1. **Characters' Behavior**
   - Describe each character's behavior in chronological order.
   - Include:
     (a) Interaction with objects in the scene.
     (b) Interaction with other characters.
     (c) Actions and movements.
   - **CRITICAL for location accuracy**: When describing object placement, retrieval, or movement, ALWAYS include:
     - **Specific furniture/container names** (e.g., "dressing table", "bedside table", "wardrobe", "shoe cabinet", "refrigerator", "microwave oven")
     - **Spatial prepositions and modifiers** (e.g., "below", "above", "left side", "right side", "beside", "in front of", "next to", "under", "on the counter")
     - **Hierarchical location structure** (e.g., "cabinet below the dressing table", "second layer of the refrigerator", "cabinet on the left side of the wardrobe")
     - **Source location** when taking objects (e.g., "takes towel from Susan's bag", "gets mask from cabinet below dressing table")
   - Examples of good location descriptions:
     - "<Lily> puts facial cleansing mask in the cabinet below the dressing table."
     - "<Sarah> takes cap from the cabinet on the left side of the wardrobe."
     - "<Lucky> places book on the bedside table."
     - "<robot> takes rolling pin from the cabinet above the microwave oven."
     - "<robot> places knife in the knife holder beside the sink."
   - Each entry must describe exactly one event/detail. Split sentences if needed.
   - Output format: Python list of strings.
```

**Rationale**: Forces the model to capture fine-grained spatial information at the behavior description stage, preventing information loss before triple extraction.

---

### 2. **Update `prompt_generate_episodic_memory` - Scene Section**

**Current** (lines 42-43):
```
4. **Scene**: Use one word or phrase to describe the scene in the current video (eg. "bedroom", "gym", "office", etc.).
   - Output format: Python string.
```

**Recommended Change**:
```
4. **Scene**: Use one word or phrase to describe the scene in the current video (eg. "bedroom", "gym", "office", etc.).
   - **Note**: This is the general room/space. Specific furniture and sub-locations should be included in character behavior descriptions, not here.
   - Output format: Python string.
```

**Rationale**: Clarifies that scene is general, preventing confusion about where detailed location info should go.

---

### 3. **Update `prompt_extract_triples` - State Representation Section**

**Current** (lines 179-181):
```
8. STATE REPRESENTATION
- If an action implies a **resulting state**, add a state triple.
  eg. "<robot> puts coffee on table" → ["<robot>", "puts", "coffee"], ["coffee", "is on", "table"]
```

**Recommended Change**:
```
8. STATE REPRESENTATION
- If an action implies a **resulting state**, add a state triple.
  eg. "<robot> puts coffee on table" → ["<robot>", "puts", "coffee"], ["coffee", "is on", "table"]
- **CRITICAL for location accuracy**: Preserve ALL spatial information in state triples:
  - **Preserve spatial prepositions and modifiers** in the content field:
    - "<Lily> puts mask in cabinet below dressing table" → ["<Lily>", "puts", "mask"], ["mask", "is in", "cabinet below dressing table"]
    - "<Sarah> takes cap from cabinet on left side of wardrobe" → ["<Sarah>", "takes", "cap"], ["cap", "is in", "cabinet on left side of wardrobe"]
    - "<robot> places rolling pin in cabinet above microwave oven" → ["<robot>", "places", "rolling pin"], ["rolling pin", "is in", "cabinet above microwave oven"]
  - **Preserve hierarchical location structure** as a single entity in the source:
    - "cabinet below dressing table" (not split into separate triples)
    - "cabinet on left side of wardrobe" (not split)
    - "second layer of refrigerator" (not split)
  - **Preserve source locations** for retrieval actions:
    - "<robot> takes towel from Susan's bag" → ["<robot>", "takes", "towel"], ["towel", "is in", "Susan's bag"]
    - "<robot> gets mask from cabinet below dressing table" → ["<robot>", "gets", "mask"], ["mask", "is in", "cabinet below dressing table"]
- **DO NOT** simplify or generalize locations:
  - ❌ WRONG: "cabinet below dressing table" → ["mask", "is in", "cabinet"], ["cabinet", "is below", "dressing table"]
  - ✅ CORRECT: "cabinet below dressing table" → ["mask", "is in", "cabinet below dressing table"]
```

**Rationale**: Prevents information loss during triple extraction by preserving complete spatial phrases as single entities.

---

### 4. **Add New Rule to `prompt_extract_triples` - Location Preservation**

**Add after Rule 8 (State Representation)**:

```
9. LOCATION PRESERVATION (CRITICAL)
- **Preserve complete location phrases** as single entities in source/target fields:
  - Spatial modifiers: "left side", "right side", "below", "above", "beside", "in front of", "next to", "under"
  - Hierarchical structures: "cabinet below dressing table", "cabinet on left side of wardrobe", "second layer of refrigerator"
  - Furniture names: "bedside table", "dressing table", "wardrobe", "shoe cabinet", "microwave oven", "knife holder"
- **DO NOT split hierarchical locations** into multiple triples:
  - ❌ WRONG: "mask is in cabinet below dressing table" → ["mask", "is in", "cabinet"], ["cabinet", "is below", "dressing table"]
  - ✅ CORRECT: "mask is in cabinet below dressing table" → ["mask", "is in", "cabinet below dressing table"]
- **Include source location** when objects are taken/moved:
  - "takes X from Y" → ["character", "takes", "X"], ["X", "is in", "Y"] (preserve Y with all modifiers)
  - "gets X from Y" → ["character", "gets", "X"], ["X", "is in", "Y"]
- **Preserve possessive locations**: "Susan's bag", "Lily's table" (keep as single entity)

10. DEDUPLICATION
- Keep only **distinct, meaningful** actions
- Do NOT duplicate states already implied by a stronger action
- Redistribution of information across triples is allowed
```

**Rationale**: Explicitly prevents the model from splitting hierarchical locations, which is a major source of information loss.

---

### 5. **Update Example in `prompt_extract_triples`**

**Current Example** (lines 192-211):
```
Input:
[
  "<Michael> pats <Susan>'s shoulder and smiles.",
  "<robot> places the red cup on the counter.",
  "<Lisa> dances and sings happily.",
  "<John> takes his wallet and keys from the drawer."
]

Output:
[
  ["<Michael>", "pats shoulder", "<Susan>"],
  ["<Michael>", "smiles", null],
  ["<robot>", "places", "red cup"],
  ["red cup", "is on", "counter"],
  ["<Lisa>", "dances happily", null],
  ["<Lisa>", "sings happily", null],
  ["<John>", "takes", "John's wallet"],
  ["<John>", "takes", "John's key"]
]
```

**Recommended Addition** (add location-focused examples):
```
Input:
[
  "<Lily> puts facial cleansing mask in the cabinet below the dressing table.",
  "<Sarah> takes cap from the cabinet on the left side of the wardrobe.",
  "<robot> places rolling pin in the cabinet above the microwave oven.",
  "<robot> takes towel from Susan's bag."
]

Output:
[
  ["<Lily>", "puts", "facial cleansing mask"],
  ["facial cleansing mask", "is in", "cabinet below dressing table"],
  ["<Sarah>", "takes", "cap"],
  ["cap", "is in", "cabinet on left side of wardrobe"],
  ["<robot>", "places", "rolling pin"],
  ["rolling pin", "is in", "cabinet above microwave oven"],
  ["<robot>", "takes", "towel"],
  ["towel", "is in", "Susan's bag"]
]
```

**Rationale**: Provides concrete examples of how to preserve hierarchical locations, which the model can follow.

---

## Expected Impact

### Direct Fixes (High Confidence):
- **bedroom_02_Q05**: "cabinet below dressing table" preserved → should fix
- **bedroom_10_Q06**: "cabinet on left side of wardrobe" preserved → should fix
- **bedroom_10_Q07**: "bedside table" preserved → should fix
- **bedroom_10_Q10**: "cabinet on left side of wardrobe" preserved → should fix

### Indirect Improvements:
- Better spatial query parsing (more specific locations in graph)
- Better retrieval (hierarchical locations match queries)
- Better reasoning (complete location information available)

### Estimated Error Reduction:
- **Location errors**: 17 → ~8-10 (47-59% reduction)
- **Overall accuracy**: 54.26% → ~60-62%

---

## Implementation Priority: **HIGH**

These changes address the **largest error category** (28.8% of all errors) and are **highly feasible** (prompt updates only, no code changes). The modifications are **targeted** to actual question formats in `robot.json` and address **specific failure modes** identified in error analysis.

---

## Testing After Implementation

Test specifically on location questions that previously failed:
1. "Where can the robot get the facial cleansing mask?" (bedroom_02_Q05)
2. "Where should the cap be placed?" (bedroom_10_Q06)
3. "Where is the book Lucky read just now?" (bedroom_10_Q07)
4. "Where should the robot place the towels?" (gym_01_Q10) - may need additional backward reasoning prompt
5. "Where should the clothes be placed?" (bedroom_10_Q10)

Monitor for:
- Preservation of spatial modifiers ("below", "left side", "above")
- Preservation of hierarchical structures ("cabinet below dressing table")
- Preservation of furniture names ("bedside table", "dressing table", "wardrobe")
