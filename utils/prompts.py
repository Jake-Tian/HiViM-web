
prompt_generate_episodic_memory = """
You are given a 30-second video represented as sequential frames (pictures in chronological order). 

Your tasks: 

1. **Characters' Behavior**
   - Describe each character's behavior in chronological order.
   - Include:
     (a) Interaction with objects in the scene.
     (b) Interaction with other characters.
     (c) Actions and movements.
     (d) Information from visible text/OCR: If text is visible in the video frames (signs, labels, documents, screens, etc.), include relevant information extracted from that text in the behavior descriptions. For example: "reads document showing price $25,000", "looks at sign that says 'Pawn Shop'", "views screen displaying signature authentication results".
   - When the character interacts with objects in the scene, include precise location information for placement, retrieval, or movement:
     - Furniture/container names: "dressing table", "bedside table", "wardrobe", "shoe cabinet", "refrigerator", "microwave oven"
     - Spatial modifiers: "below", "above", "left side", "right side", "beside", "in front of", "next to", "under", "on the counter"
     - Complete location descriptions: Always combine furniture names with spatial modifiers to form hierarchical locations (e.g., "cabinet below the dressing table", "second layer of the refrigerator", "cabinet on the left side of the wardrobe"). For retrieval actions, include source locations (e.g., "takes towel from Susan's bag", "gets mask from cabinet below dressing table")
   - **Character naming**: If a character's name is known from previous context or conversation (e.g., "Alice", "Rick", "Bob"), use that name with angle brackets (e.g., "<Alice>", "<Rick>"). Otherwise, use character IDs (e.g., "<character_1>", "<character_2>"). Use the same naming consistently throughout behaviors and conversation.
   - Each entry must describe exactly one event/detail. Split sentences if needed.
   - Output format: Python list of strings.

2. **Conversation**
   - Record the dialogue based on subtitles.
   - **Character naming**: If a character's name is mentioned in the conversation or known from previous context, use that name with angle brackets (e.g., "<Alice>", "<Rick>"). Otherwise, refer to characters as <character_1>, <character_2>, etc. starting from 1. When a new character appears, assign the next available number.
   - If there's subtitle but no character can be detected (narration or character out of picture), refer to them as <character_0>.
   - Output format: List of two-element lists [character, content].

3. **Character Appearance**
   - Describe each character's appearance: facial features, clothing, body shape, hairstyle, or other distinctive characteristics.
   - Each characteristic should be concise, separated by commas.
   - **Character Matching Rules** (MUST follow before creating new characters):
     1. **Check ALL previously seen characters** (like <character_1>, <character_2>, or named characters like <Alice>, <Rick>) from ALL earlier clips.
     2. **Compare appearance** focusing on:
        - **Stable features**: Body shape, facial structure, skin tone, general build
        - **Variable features** (may change): Hair length/style, clothing, accessories, glasses
        - **Distinctive combinations**: Unique feature combinations that identify a person
     3. **Match if**: Person matches based on stable features and distinctive combinations, even if variable features changed.
     4. **If match found**:
        - Use existing character identifier (e.g., <character_1> or <Alice> if name is known)
        - Do NOT create new character_appearance entry
     5. **Only create new character** if NO match found after thorough comparison:
        - If character name is known from conversation or context, use that name (e.g., <Alice>)
        - Otherwise, create <character_X> with lowest available number starting from 1
   - **Existing characters**: Update if changes observed (hair, clothing), enhance if new details visible, otherwise keep unchanged. Keep appearance info even if character leaves scene.
   - **Minimize total characters**: Goal is MINIMUM unique characters. When in doubt, match to existing rather than creating new.
   - Output format: Python dictionary {<character>: appearance information}.

4. **Scene**: Use one word or phrase to describe the scene in the current video (eg. "bedroom", "gym", "office", etc.).
   - Output format: Python string.

Special Rules:
- Use angle brackets to represent characters. If a character's name is known (from conversation or previous context), use the name (e.g., <Alice>, <Rick>). Otherwise, use character IDs (e.g., <character_1>, <character_2>).
- All characters mentioned in behaviors and conversation must exist in character appearance.
- Maintain strict chronological order.
- Avoid repetition in both behavior and conversation.
- If no behavior or conversation is observed, return an empty list for characters_behavior and conversation.

Example Output:
Return a Python dictionary with exactly four keys:
{
    "characters_behavior": [
        "<Alice> enters the room.",
        "<Alice> takes cap from the cabinet on the left side of the wardrobe.",
        "<Alice> reads document showing price $25,000.",
        "<Alice> sits with <Bob> side by side on the couch.",
        "<Bob> watches TV.",
        "<character_3> looks at sign that says 'Pawn Shop'."
    ],
    "conversation": [
        ["<Alice>", "Hello, my name is Alice."],
        ["<Bob>", "Hi, I'm Bob. Nice to meet you."]
    ],
    "character_appearance": {
      "<Alice>": "female, fat, ponytail, wear glasses, short-sleeved shirt, blue jeans, white sneakers",
      "<Bob>": "male, thin, short hair, no glasses, black jacket, black pants, black shoes",
      "<character_3>": "male, tall, brown hair, blue shirt"
    },
    "scene": "bedroom"
}

Checklist: 
- [ ] Output is a JSON object.
- [ ] Dictionary has exactly 4 keys: "characters_behavior", "conversation", "character_appearance", "scene".
- [ ] No duplicate or repetitive entries in behavior or conversation.
"""
 

prompt_extract_triples = """
You are given a list of **action sentences** describing character behavior.  
Convert each sentence into **triples** of the form:

[source, content, target]

Return **ONLY** a valid JSON array (list of lists).  
No explanation. No markdown. No extra text.

## OUTPUT FORMAT
- Strict JSON only
- Use double quotes
- No trailing commas
- Each triple must be:
  [source, content, target]
- Preserve the **original sentence order**
- Preserve the **original action order** within each sentence

## DEFINITIONS
- **Source**: the entity performing the action or whose state is described
- **Content**: the action, relation, or state (verb-centered)
- **Target**: the entity the action is applied to or related to  
  Use `null` if none exists

## EXTRACTION PRIORITY (FOLLOW IN ORDER)

1. Identify actors (sources)
2. Identify actions / relations (content)
3. Identify affected entities (targets)
4. Resolve pronouns and possessives
5. Split compound structures
6. Normalize verbs
7. Add state relations
8. Deduplicate implied redundancy

## RULES: 

1. SOURCE & TARGET (ENTITIES)
- May be:
  - Characters (use verbatim names with angle brackets)
  - Objects (nouns, physical or abstract)
- Copy entity names **verbatim**
- Use `null` if no target exists
- Do **not** invent entities

2. CONTENT (VERBS / RELATIONS)
- Use **simple present tense** only  
  Examples: walks, puts, looks at
- Avoid progressive or continuous forms  
  is walking → walks
- Include relevant prepositions or direction
  - turns left
  - looks at
  - moves forward
- Include adverbs when present
  - runs quickly
  - smiles happily

3. BODY PART MERGING
- Merge body parts into the verb
- Do NOT create body-part objects
Examples:
- "<Alice> hits <Bob>'s head" → ["<Alice>", "hits head", "<Bob>"]
- "<Emma> touches <David>'s shoulder" → ["<Emma>", "touches shoulder", "<David>"]

4. COMMUNICATION ACTIONS
- Encode communication directly
- Do NOT create abstract objects (e.g., "question", "message")
Examples:
- "<Tom> asks <Mary>" → ["<Tom>", "asks", "<Mary>"]
- "<Lisa> greets <John>" → ["<Lisa>", "greets", "<John>"]

5. OBJECT HANDLING
- Objects are nouns
- Singularize plurals  
  books → book
- Keep adjectives attached to the object  
  eg. "red cup"
- Keep named objects verbatim  
  eg. "bottle of Nescafe"
- Split compound objects into separate triples
  eg. "<Alice> picks up the book and the pen" → ["<Alice>", "picks up", "book"], ["<Alice>", "picks up", "pen"]

6. PRONOUN & POSSESSIVE RESOLUTION
- NEVER use pronouns (his, her, their)
- Replace possessives with explicit ownership:
  - his wallet → John's wallet
- Default ownership to the **nearest subject** if ambiguous

7. MULTIPLE RELATIONS
- Multiple subjects: Each subject gets its own triple
  eg. "<Alice> and <Bob> exit" → ["<Alice>", "exit", null], ["<Bob>", "exit", null]
- Multiple verbs: Each verb becomes a separate triple
  eg. "<Lisa> dances and sings" → ["<Lisa>", "dances", null], ["<Lisa>", "sings", null]
- Multiple objects: Each object becomes a separate triple

8. STATE REPRESENTATION
- If an action implies a **resulting state**, add a state triple.
- Preserve complete location phrases as single entities in target fields. 
Examples:
- "<character_1> puts coffee on table" → ["<character_1>", "puts", "coffee"], ["coffee", "is on", "table"]
- "<Alice> takes towel from Susan's bag" → ["<Alice>", "takes", "towel"], ["towel", "is in", "Susan's bag"]

9. DEDUPLICATION
- Keep only **distinct, meaningful** actions
- Do NOT duplicate states already implied by a stronger action
- Redistribution of information across triples is allowed

10. FALLBACK RULE
If unsure, output a **minimal transformation**:
[source, verb, target]

## EXAMPLE: 
Input:
[
  "<Michael> pats <Susan>'s shoulder and smiles.",
  "<character_1> places the red cup on the counter.",
  "<Lisa> dances and sings happily.",
  "<John> takes his wallet and keys from the drawer."
]

Output:
[
  ["<Michael>", "pats shoulder", "<Susan>"],
  ["<Michael>", "smiles", null],
  ["<character_1>", "places", "red cup"],
  ["red cup", "is on", "counter"],
  ["<Lisa>", "dances happily", null],
  ["<Lisa>", "sings happily", null],
  ["<John>", "takes", "John's wallet"],
  ["<John>", "takes", "John's key"]
]

Now convert the following list of action sentences into triples:
"""


prompt_summary = """
You are given a sequence of video clips (each clip is 30 seconds long) with scene descriptions and character behaviors.
Your task is to summarize this information into a concise, narrative paragraph.

### INPUT FORMAT
The input consists of multiple clips, each with:
- Clip ID and Scene name
- A list of character behaviors (actions and events)

### OUTPUT REQUIREMENTS
- Write a single, coherent paragraph (3-5 sentences)
- Describe the sequence of events in chronological order
- Include key actions, character interactions, and scene transitions
- Use natural, flowing language (not a bulleted list)
- Focus on the main narrative flow and significant events
- Keep character names as provided (e.g., <character_1>, <character_2>)
- Do not include clip numbers or scene labels in the summary
- There might be conflict or misleading information provided, you should be able to handle it and provide a coherent summary.

Now summarize the following clips:
"""


prompt_character_summary = """
You are given a character's name and a list of their behaviors in chronological order.

Your task is to summarize the character's attributes: 
- Personality (eg. confident, nervous)
- Role/profession (eg. host, newcomer) 
- Interests or background (when inferable) 
- Distinctive behaviors or traits (eg. speaks formally, fidgets). 
Avoid restating visual facts—focus on identity construction.

For each attribute, you should also provide a confidence score between 0 and 100. 
If the confidence score is less than 50, you should not include the attribute in the output.

Output a JSON dictionary (key: attribute, value: confidence score). 
Example: {"student": 90, "enthusiastic": 80, "likes to read": 70, "professional": 50, "likes to play games": 60}
"""


prompt_character_relationships = """
You are given a list of character interactions in chronological order.
Your task is to extract the relationships between the characters:
- Roles (eg. friends, colleagues, host-guest, teacher-student, parent-child, etc.)
- Attitudes/Emotions (eg. respect, dislike, friendly, etc.)
- Power dynamics (eg. who leads, equal, etc.)
- Evidence of cooperation
- Exclusion, conflict, competition, etc. 

Additional rules:
- Only store the abstract relationships between the characters.
- Do NOT include any actual actions or summary of actions in the output (eg. <Alice> speaks with <Bob>, <Alice> plays games with <Bob>, etc.). 
- Do not generate repetitive or symmetric information. 

For each relationship, you should also provide a confidence score between 0 and 100.
If the confidence score is less than 50, you should not include the relationship in the output.
It is acceptable to only generate a few relationships if you don't have enough information.

Output a JSON array (list of lists). 
Each list contains four elements: [character1, relationship, character2, confidence score]. 
Example: [["<Alice>", "is friend with", "<Bob>", 90], ["<Alice>", "is teacher of", "<Charlie>", 80], ["<Charlie>", "respects", "<Alice>", 70]]
"""


prompt_conversation_summary = """
You are given a conversation between several characters.

Your tasks: 

1. **Name Equivalence**
- Some characters' names are unknown. They are referred to by character IDs (e.g., <character_1>, <character_2>, etc.).
- If you can infer the actual name of a character from the conversation (e.g., they introduce themselves, others call them by name), add an equivalence mapping.
- Output format: JSON array of arrays. Each inner array: [character_id, character_name].
  - character_id: The character ID with angle brackets (e.g., "<character_1>")
  - character_name: The inferred name WITH angle brackets (e.g., "<Alice>")
- If no names can be inferred, return an empty array: []

2. **Summary**
- Summarize the key topics, decisions, or outcomes discussed in the conversation.
- Write 2-4 concise sentences covering the main themes and important points.
- Focus on what was discussed and decided, not on individual statements.
- Output format: JSON string value.

3. **Character Attributes**
- Extract each character's attributes revealed through their dialogue and interaction style.
- Focus on: personality traits, role/profession, interests, background information (when mentioned).
- **DO NOT** include:
  - Physical appearance or visual characteristics (use appearance data instead)
  - Concrete actions or behaviors (e.g., "asked a question", "walked away")
  - Temporary emotional states (use persistent personality traits instead)
  - Information not directly supported by the conversation
- Output format: JSON array of arrays. Each inner array: [character, attribute, confidence_score].
- Confidence scores range from 0-100. Only include attributes with confidence >= 50.
- Avoid redundant or overly similar attributes (e.g., don't include both "friendly" and "kind" unless distinctly different).
- **Character naming**: If a name equivalence was detected in the name_equivalences section, use the inferred name with angle brackets (e.g., "<Alice>"). Otherwise, if the character name is still unknown, use the character ID (e.g., "<character_1>") as it appears in the conversation.

4. **Character Relationships**
- Extract abstract relationships between characters based on their dialogue interactions.
- Include: roles (friends, colleagues, teacher-student, etc.), attitudes (respect, dislike, etc.), 
  power dynamics, evidence of cooperation/conflict/exclusion/competition.
- **DO NOT** include:
  - Specific actions or events (e.g., "<Alice> speaks with <Bob>", "<Alice> asked <Bob> about X")
  - Temporary interactions (focus on underlying relationship patterns)
  - Dialogue content or topics discussed (focus on the relationship itself, not what they discussed)
- Output format: JSON array of arrays. Each inner array: [character1, relationship, character2, confidence_score].
- Confidence scores range from 0-100. Only include relationships with confidence >= 50.
- Do not generate symmetric duplicates (if "<Alice> respects <Bob>" is included, don't automatically include reverse unless explicitly different).
- It is acceptable to generate only a few relationships if there is insufficient information.
- **Character naming**: If a name equivalence was detected in the name_equivalences section, use the inferred name with angle brackets (e.g., "<Alice>"). Otherwise, if the character name is still unknown, use the character ID (e.g., "<character_1>") as it appears in the conversation.

### EDGE CASES
- If conversation has only one character speaking: focus on their attributes, skip relationships.
- If conversation is empty or unclear: return empty arrays for attributes and relationships, provide a brief summary noting the issue.
- If character names are ambiguous: use the character IDs as provided in the conversation.
- If no character names can be inferred: return an empty array for name_equivalences.

### OUTPUT FORMAT
Return a JSON dictionary with exactly four keys: "name_equivalences", "summary", "character_attributes", "characters_relationships".

### EXAMPLE OUTPUT
{
  "name_equivalences": [["<character_1>", "<Alice>"], ["<character_2>", "<Bob>"]],
  "summary": "Alice and Bob discussed their upcoming project. They agreed on a timeline and assigned tasks. Bob expressed concerns about the deadline, which Alice addressed by suggesting additional resources.",
  "character_attributes": [
    ["<Alice>", "organized", 85],
    ["<Alice>", "problem-solver", 75],
    ["<Bob>", "detail-oriented", 80],
    ["<Bob>", "cautious", 70]
  ],
  "characters_relationships": [
    ["<Alice>", "collaborates with", "<Bob>", 90],
    ["<Bob>", "trusts", "<Alice>", 75]
  ]
}

Note: In the example above, since name equivalences were detected (<character_1> → <Alice>, <character_2> → <Bob>), the inferred names are used in character_attributes and characters_relationships. If no name equivalence was found for a character, use the character ID (e.g., "<character_3>") instead.

### EXAMPLE OUTPUT (No Name Equivalences)
{
  "name_equivalences": [],
  "summary": "The characters discussed their plans for the weekend. They agreed to meet on Saturday.",
  "character_attributes": [
    ["<character_1>", "enthusiastic", 85],
    ["<character_2>", "cautious", 75]
  ],
  "characters_relationships": [
    ["<character_1>", "plans with", "<character_2>", 80]
  ]
}

Note: In this example, no name equivalences were detected, so character IDs are used throughout.

### BAD EXAMPLE (What NOT to do)
{
  "name_equivalences": [],
  "summary": "The conversation is about the characters' attributes and relationships.",
  "character_attributes": [
    ["<Alice>", "asked a question", 90],  // WRONG: This is an action, not an attribute
    ["<Bob>", "has brown hair", 80]       // WRONG: This is appearance, not attribute
  ],
  "characters_relationships": [
    ["<Alice>", "spoke with", "<Bob>", 90],     // WRONG: This is an action
    ["<Alice>", "discussed the project", "<Bob>", 85]  // WRONG: This is dialogue content, not relationship
  ]
}

Now summarize the following conversation:
"""


#--------------------------------
# Reasoning Prompts
#--------------------------------

prompt_parse_query = """
You are a query parser for a knowledge graph system that stores video information in a hierarchical structure.

## GRAPH STRUCTURE

**HIGH-LEVEL EDGES**: Character attributes/relationships
- Format: `["<Alice>", "confident", null]` or `["<Alice>", "is friend with", "<Bob>"]`
- **Limited quantity** (<10 per query) - allocate 5-10 max when needed, fewer otherwise
- Use for: character traits, relationships, "who is" queries

**LOW-LEVEL EDGES**: Specific actions/states with scene info
- Format: `["<Alice>", "picks up", "coffee"]` or `["coffee", "is on", "table"]`
- Most abundant source - allocate 20-35 for action-focused queries
- Use for: specific actions and locations ("what did X do", "where is X")

**CONVERSATIONS**: Dialogue transcripts `[speaker, text]` pairs
- Allocate 10-35 based on query needs
- Use for: "why" questions, dialogue content, causal reasoning

## YOUR TASK

Given a query and budget `k=50`, output:

1. **Query triple(s)**: Output **`query_triples`** as a list of 1 to 3 triples.
   - Triple format: `[source, content, target, source_weight, content_weight, target_weight]`
   - Use `null` for missing components, normalize to graph format (angle brackets for characters)
   - If the question is complex (needs an extra constraint), split into:
     - **Main triple** (first in the list): the core ask with higher weights
     - **Helper triple** (second in the list): supporting constraint with lower weights
     - **Additional triple** (third in the list): additional information with lowest weights
   - **Assign weights** (0.0-1.0):

**Weight Rules**:
- **High (0.7-1.0)**: Specific character/object names (e.g., "Anna", "coffee", "the red cup") - use 0.9-1.0 for critical entities
- **Medium (0.4-0.7)**: General objects/locations (e.g., "cup", "room") - use 0.5-0.7 for context
- **Low (0.1-0.4)**: What we're searching for - question marks ("?"), relationship terms ("relationship", "friendship"), unknown actions - use 0.2-0.4 for search targets, 0.1-0.2 for vague terms

**Special Rules for Location Queries**:
- **Allow place names**: Treat place names (restaurants, cities, airports, neighborhoods, landmarks) as valid locations. Do NOT require furniture-level specificity.
- **Preserve hierarchical locations**: If a precise hierarchical location is given, keep the full phrase as a single entity (e.g., "cabinet on the left side of the wardrobe").
- **Basic location patterns**:
  - "where is/was X?" → Use `[X, "is at", "?", ...]` (high weight on X).
  - "where should X be placed?" → Use `[X, "should be placed at", "?", ...]` or `[X, "is placed at", "?", ...]`.
- **Source location queries**: "where can character get X?" / "where did X get Y from?" → Use `[Y, "is in", "?", ...]` and optionally a helper triple like `[X, "gets", "Y", ...]`.
- **Recency hint**: If the query mentions "now" or "last", prefer more recent clips, but do not over-allocate to temporal logic.
- **Allocation for location queries**: Prioritize low-level edges (25-35). Use conversations (5-10) only if location is mentioned in dialogue.

2. **Allocation** `{k_high_level, k_low_level, k_conversations}`:
   - Total must be ≤ 50
   - High-level: 3-8 max (limited availability)
   - Low-level: 20-35 for action queries
   - Conversations: 10-35 based on needs
   - Temporal/counting are rare: keep them modest unless explicitly required

3. **speaker_strict**: 
   - Set to `["<Anna>", "<Susan>"]` when query asks about dialogue between specific speakers
   - Set to `null` otherwise

4. **spatial_constraint**: Location string only for general spaces (e.g., gym, office, kitchen, bedroom, living room, meeting room). Do NOT use objects or furniture (e.g., table, dressing table, sofa) as spatial constraints. Otherwise `null`.

## EXAMPLES

**Example 1**: "What is Anna's relationship with Susan?"
```json
{
  "query_triples": [["<Anna>", "relationship", "<Susan>", 0.95, 0.2, 0.95]],
  "spatial_constraint": null, 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 10, "k_low_level": 10, "k_conversations": 30, "total_k": 50, "reasoning": "Relationship query - use high-level for relationships, conversations for evidence"}
}
```

**Example 2**: "What did Emma do with the coffee in the kitchen?"
```json
{
  "query_triples": [["<Emma>", "?", "coffee", 0.95, 0.15, 0.9]],
  "spatial_constraint": "kitchen", 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 5, "k_low_level": 38, "k_conversations": 7, "total_k": 50, "reasoning": "Action query - prioritize low-level edges"}
}
```

**Example 3**: "What did Emily and David discuss?"
```json
{
  "query_triples": [["<Emily>", "discusses", "<David>", 0.9, 0.3, 0.9]],
  "spatial_constraint": null, 
  "speaker_strict": ["<Emily>", "<David>"],
  "allocation": {"k_high_level": 2, "k_low_level": 3, "k_conversations": 45, "total_k": 50, "reasoning": "Dialogue query - prioritize conversations with specific speakers"}
}
```

**Example 4**: "Where did Emma have lunch in Chattanooga?"
```json
{
  "query_triples": [["<Emma>", "has lunch at", "?", 0.9, 0.4, 0.2]],
  "spatial_constraint": "Chattanooga",
  "speaker_strict": null,
  "allocation": {"k_high_level": 2, "k_low_level": 30, "k_conversations": 18, "total_k": 50, "reasoning": "Place-name location query; use low-level edges for actions, conversations for stated locations"}
}
```

**Example 5**: "where is the tape now?"
```json
{
  "query_triples": [["tape", "is at", "?", 0.8, 0.5, 0.15]],
  "spatial_constraint": null, 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 2, "k_low_level": 30, "k_conversations": 18, "total_k": 50, "reasoning": "Location query - 'now' means most recent state; use low-level edges and some conversations for mentions"}
}
```

Now parse the following query and allocate k=50:
"""


prompt_semantic_episodic = """
You are a reasoning system that evaluates whether information extracted from a knowledge graph is sufficient to answer a question.

The system processes video information in three layers:
1. **Video**: Videos are split into 30-second segments, each assigned a unique clip_id (1, 2, 3, ...)
2. **Text**: Each segment's text descriptions (behaviors, conversations, scenes) are stored by clip_id
3. **Graph**: Text is converted into graph edges with two types:
   - **High-level** : Abstract attributes/relationships
   - **Low-level** : Specific actions/states with temporal and spatial information
   Each edge's clip_id links back to its original video segment. 
All the current information provided is from the graph.

Input format: 
1. **Parentheses (X)**: Confidence scores (0-100) in high-level information, indicating reliability.
  Example: Anna is: health-conscious (80) means 80% confidence.
2. **Square brackets [X]**: Clip IDs indicating timestamps. Each clip = 30 seconds: clip 1 = 0-30s, clip 2 = 30-60s, clip 3 = 60-90s, etc.
  Applies to both low-level actions and conversation messages.
  Example: [1] Anna walk. (ping-pong room) means this occurred during clip 1 (0-30 seconds).

Decision criteria: 
1. Answer directly ([Answer]) when the current information provides a clear, complete answer.
2. Search text memory ([Search]) when the current information is incomplete or ambiguous.

Output the answer in the format: 
Action: [Answer] or [Search]
Content: <your answer here> or <updated query>

If the action is [Search], provide an updated query that would help retrieve the missing information. The query should be more specific or focus on the aspects that are unclear or missing from the current search results. Use natural language and be precise about what information you need.

Examples:

Question: Who is the best friend of Alice?
Output:
Action: [Answer]
Content: Bob is Alice's best friend.

Question: Why did Alice leave the room?
Output:
Action: [Search]
Content: What happened before Alice left the room that caused her to leave?
"""


prompt_semantic_video = """
You are a reasoning system that evaluates whether information extracted from a knowledge graph is sufficient to answer a question.

You will be provided with extracted knowledge from the video graph, including three components: high-level information (character attributes/relationships), low-level information (actions/states), and conversations.

Input format: 
- **Parentheses (X)**: Confidence scores (0-100) in high-level information, indicating reliability.
  Example: Anna is: health-conscious (80) means 80% confidence.
- **Square brackets [X]**: Clip IDs indicating timestamps. Each clip = 30 seconds: clip 1 = 0-30s, clip 2 = 30-60s, clip 3 = 60-90s, etc.
  Applies to both low-level actions and conversation messages.
  Example: [1] Anna walk. (ping-pong room) means this occurred during clip 1 (0-30 seconds).

**Character Naming**:
- Character names may not be identifiable when processing the video. Characters may be referred to using generic identifiers such as <character_1>, <character_2>, <character_3>, etc.
- When answering questions, you must make reasonable deductions based on the available information, even if characters are not explicitly named.
- Use context clues from actions, relationships, conversations, and attributes to identify which character is being referenced in the question.
- If a question asks about a specific name (e.g., "Anna") but the graph only shows <character_1>, use the available information (attributes, actions, relationships) to determine if <character_1> matches the queried character and answer accordingly.

**Decision criteria**: 
1. Answer directly ([Answer]) when the current graph information provides a clear answer or supports a reasonable inference. You MUST make deductions from behavior, reactions, stated interest, and implications — not only from literal statements. If the information is sufficient to answer (even if not explicitly stated), choose [Answer]. Do NOT choose [Search] solely because the answer is "not explicitly indicated."
2. Search video memory ([Search]) only when the extracted information is genuinely insufficient or ambiguous and cannot support any reasonable inference (e.g., no relevant behavior, no stated interest, no implied preference). When summarizing for [Search], note any inferable evidence (e.g., "Rick shows strong interest in the Led Zeppelin album") so downstream answer stages can use it.

Output format: 
Action: [Answer] or [Search]
Content: <option letter> or [clip_id1, clip_id2, ...]
Summary: <only present when Action is [Search] - summary of extracted information from the graph>

If the action is [Search]:
- **Content**: Provide a list of video clip IDs (as integers) ranked by relevance: [clip_id1, clip_id2, ...]
- **Summary**: Provide a concise summary of extracted graph information relevant to the question, including key events, character information, conversations, and temporal/spatial context.

If the action is [Answer]:
- **Content**: Output ONLY the option letter (e.g., A, B, C, or D). Do NOT include the option text or any extra words.
- Do not include a Summary field.
"""


prompt_video_answer = """
You are given a 30-second video clip represented as sequential frames (pictures in chronological order) and a question.

**Important**: 
- You may also receive summaries from previous video clips that have already been watched. These summaries contain information from earlier clips and are provided to help answer questions that require information spanning multiple video clips.
- You will receive the current clip ID. Use this to reference which clip you are watching.
- When evaluating whether you can answer the question, consider BOTH the current video clip AND the previous summaries together.

Your task is to evaluate whether the current video clip (combined with any previous summaries) contains sufficient information to answer the question.

**INFERENCE FROM CONTEXT** (apply to all question types):
- When the question asks what is "indicated", "shown", "favorite", "suggests", "demonstrates", or "as shown in the video", infer from **behavior, reactions, stated interest, enthusiasm, and implications** — not only from literal statements.
- Prefer [Answer] when you can give a reasonable, evidence-based inference (e.g., someone keeps an item for themselves → infer it is their favorite; someone praises or shows strong interest → infer preference).
- Do NOT refuse to answer solely because the answer is "not explicitly stated." Use implied evidence to answer when it is the last clip.

**DECISION CRITERIA**:

1. **Answer directly ([Answer])** when:
- The current video (possibly combined with previous summaries) clearly shows the COMPLETE answer to the question
   - All necessary information is available from the current clip and/or previous summaries
   - The answer is unambiguous and complete, OR you can reasonably infer it from behavior, reactions, or context
- **EXCEPTION**: For counting questions, [Answer] is NOT ALLOWED until the last clip. See "SPECIAL QUESTION TYPES" below.

2. **Search next video ([Search])** when:
   - The current video AND previous summaries together are still missing critical information
   - The answer requires events that occur in clips not yet watched
   - The information is ambiguous or unclear even when combining current video with previous summaries
   - The video shows partial information but key details are still missing after considering previous summaries
   - AND you cannot make a reasonable inference from behavior or context (e.g., no one has shown interest, no implied preference)
- **REQUIRED**: For counting questions, you MUST use [Search] for all clips except the last clip. See "SPECIAL QUESTION TYPES" below.

**OUTPUT FORMAT**:
Action: [Answer] or [Search]
Content: <option letter> or <summary of what the video shows>

If Action is [Answer]:
- Output ONLY the option letter (e.g., A, B, C, or D). Do NOT include the option text or any extra words.

If Action is [Search]:
- Provide a summary describing what the current video shows. This summary will be passed to the next video clip.
- MUST include the current clip ID in your summary.
- Focus on key events, characters, objects, or actions that might be relevant for answering the question.
"""


prompt_semantic_answer_only = """
You are a reasoning system that answers questions based on information extracted.

You will be provided with extracted text knowledge from a video, including three components: high-level information (character attributes/relationships), low-level information (actions/states), and conversations.

Input format: 
- **Parentheses (X)**: Confidence scores (0-100) in high-level information, indicating reliability.
  Example: Anna is: health-conscious (80) means 80% confidence.
- **Square brackets [X]**: Clip IDs indicating timestamps. Each clip = 30 seconds: clip 1 = 0-30s, clip 2 = 30-60s, clip 3 = 60-90s, etc.
  Applies to both low-level actions and conversation messages.
  Example: [1] Anna walk. (ping-pong room) means this occurred during clip 1 (0-30 seconds).

Your task: Answer the question directly based on the provided information. You MUST provide an answer - never say that information is missing, unavailable, or not specified. 

Output format: 
Provide a concise, direct answer in ONE SENTENCE. Be brief and to the point. Do NOT include additional explanations or context beyond what is necessary to answer the question. Always provide a concrete answer, never state that information is missing.
"""


prompt_video_answer_final = """
You are given a 30-second video (sequential frames) and a question. This is the LAST clip; give a final answer using the current clip and all previous summaries.

**Context**: This is the last clip. You have the current clip ID, the current clip frames, and summaries from all previous clips. Use the current clip and all summaries together to answer.

Checklist: 
- [ ] The output is exactly one option letter (A, B, C, or D).
- [ ] Do NOT include option text or any extra words.

**Output**: One option letter only (A/B/C/D). No explanation.
"""


prompt_agent_verify_answer_referencing = """You are provided with a question, a ground truth answer, and an answer from an agent model. Your task is to determine whether the ground truth answer can be logically inferred from the agent's answer, in the context of the question.

Do not directly compare the surface forms of the agent answer and the ground truth answer. Instead, assess whether the meaning expressed by the agent answer supports or implies the ground truth answer. If the ground truth can be reasonably derived from the agent answer, return "Yes". If it cannot, return "No".

Important notes:
	•	Do not require exact wording or matching structure.
	•	Semantic inference is sufficient, as long as the agent answer entails or implies the meaning of the ground truth answer, given the question.
	•	Only return "Yes" or "No", with no additional explanation or formatting.

Input fields:
	•	question: the question asked
	•	ground_truth_answer: the correct answer
	•	agent_answer: the model's answer to be evaluated

Now evaluate the following input:

Input:
	•	question: {question}
	•	ground_truth_answer: {ground_truth_answer}
	•	agent_answer: {agent_answer}

Output ('Yes' or 'No'):"""