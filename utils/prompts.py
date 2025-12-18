
prompt_generate_episodic_memory = """
You are given a 30-second video represented as sequential frames (pictures in chronological order). 

Your tasks: 

1. **Characters' Behavior**
   - Describe each character's behavior in chronological order.
   - Include:
     (a) Interaction with objects in the scene.
     (b) Interaction with other characters.
     (c) Actions and movements.
   - Each entry must describe exactly one event/detail. Split sentences if needed.
   - Output format: Python list of strings.

2. **Conversation**
   - Record the dialogue based on subtitles.
   - Output format: List of two-element lists [character, content].

3. **Character Appearance**
   - Describe each character's appearance: facial features, clothing, body shape, hairstyle, or other distinctive characteristics.
   - Each characteristic should be concise, separated by commas.
   - **New characters**: Describe based on what you observe.
   - **Existing characters** (if previous appearance info provided): Update if changes observed, enhance if new details visible, otherwise keep unchanged.
   - If the character leaves the scene, keep their appearance information in the dictionary.
   - If two characters in the scene look similar, extract the most distinctive features to describe them.
   - Output format: Python dictionary {<character>: appearance information}.

4. **Scene**: Use one word or phrase to describe the scene in the current video (eg. "bedroom", "gym", "office", etc.).
   - Output format: Python string.

Special Rules:
- Use angle brackets to represent the characters eg. <Alice>, <Bob>, <robot>, <character_1>, etc.
- If you don't know the character's name, use <character_1>, <character_2>, etc.
- If an unknown character is later identified, add an equivalence line at the **start of characters_behavior**. Then remove its information from character_appearance: 
  Example: "Equivalance: <character_1>, <Alice>"
- Include the robot (<robot>) if present:
  - It wears black gloves and has no visible face (it holds the camera).
  - Describe its behavior and conversation.
  - Do NOT include robot in character appearance information, but include it in characters_behavior and conversation.
- Maintain strict chronological order.
- Avoid repetition in both behavior and conversation.
- If no behavior or conversation is observed, return an empty list for characters_behavior and conversation.

Example Output:
Return a Python dictionary with exactly four keys:
{
    "characters_behavior": [
        "<Alice> enters the room.", 
        "<Alice> sits with <Bob> side by side on the couch.", 
        "<Bob> watches TV.", 
        "<robot> puts the coffee on the table."
    ],
    "conversation": [
        ["<Alice>", "Hello, my name is Alice."], 
        ["<Bob>", "Hi, I'm Bob. Nice to meet you."]
    ], 
    "character_appearance": {
      "<Alice>": "female, fat, ponytail, wear glasses, short-sleeved shirt, blue jeans, white sneakers", 
      "<Bob>": "male, thin, short hair, no glasses, black jacket, black pants, black shoes"
    }, 
    "scene": "bedroom"
}

Checklist: 
- [ ] Output is a Python dictionary.
- [ ] Dictionary has exactly 4 keys: "characters_behavior", "conversation", "character_appearance", "scene".
- [ ] No duplicate or repetitive entries in behavior or conversation.
"""


prompt_extract_triples = """
You are given a list of action sentences describing character behavior.
Convert them into triples of the form:

[subject, predicate, object]

Return ONLY a valid JSON array (list of lists). No explanation.

### CORE RULES

1. SUBJECTS
- Subjects may be characters (with angle brackets) or objects/entities.
- Copy subjects verbatim (e.g., "<robot>", "coffee").

2. OBJECT IDENTIFICATION
- Objects are nouns representing entities (physical things, abstract concepts, or named objects).
- Format: simple noun (e.g., "table", "phone", "book") or noun#attribute (see rule 3 for attributes).
- Plurals → singularize (e.g., "books" → "book").
- Named objects → keep verbatim (e.g., "bottle of Nescafe").
- **Position/direction**: Do NOT use as object. Merge into predicate.
  Example: "<Lily> turns left" → ["<Lily>", "turns left", null], NOT ["<Lily>", "turns", "left"].
- **Missing objects**: Use `null` if no object can be extracted.
  Example: "<Frank> dances" → ["<Frank>", "dances", null].
- **Multiple objects**: Split compound objects into separate triples.

3. ATTRIBUTE (#) CONSTRAINTS
- Attributes MUST be identity-defining characteristics.
- ALLOWED: color, material, shape, size, brand/type.
- FORBIDDEN: locations, positions, or conditions.
- Temporary states/locations MUST be expressed as separate triples.

4. OWNERSHIP (@)
- Personal items (objects that belong to a specific character) → noun@<character>.
- Use ownership notation ONLY for items that are clearly personal possessions or belong to a specific character.
- Examples: "phone@<Alice>", "bag@<Bob>", "jacket@<Lily>"
- When to use ownership:
  * Personal devices: phone, wallet, keys, watch, glasses
  * Personal clothing/accessories: jacket, bag, hat (when clearly belonging to someone)
  * Personal items mentioned with possessive pronouns ("her phone", "his bag")
- When NOT to use ownership:
  * Shared/public objects: table, chair, mug, coffee bottle, door
  * Objects being passed between characters (use without ownership)
  * Objects in the environment

5. BODY PARTS
- Merge body parts into the predicate.
  Example: "<Alice> hits <Bob>'s head" → ["<Alice>", "hits head", "<Bob>"].
  Example: "<Emma> touches <David>'s shoulder" → ["<Emma>", "touches shoulder", "<David>"].

6. COMMUNICATION ACTIONS
- Do NOT create abstract conversation objects ("response", "message", "question").
- Use the character directly as the object, or encode the concept in the predicate.
  Example: ["<Alice>", "responds to", "<Bob>"] or ["<Alice>", "responds to question", "<Bob>"].
  Example: ["<Sarah>", "asks", "<Tom>"] or ["<Emma>", "greets", "<David>"].

7. PRONOUNS
- NEVER use pronouns ("her", "his", "their").
- Replace pronouns with the actual character or object name.

8. MULTIPLE RELATIONS
- If a sentence expresses multiple relations, split into multiple triples.

9. DEDUPLICATION
- Keep only distinct, meaningful actions.
- Prefer completed actions over partial or preparatory ones.
- Avoid redundant states implied by stronger actions.

10. STATE REPRESENTATION
- State triples are allowed with the object as subject.
  Example: "<robot> puts coffee on table" →
  ["<robot>", "puts", "coffee"], ["coffee", "is on", "table"].

11. ORDER & FALLBACK
- Preserve the original order of actions.
- If unsure, default to minimally transformed [subject, verb, object].

12. OUTPUT FORMAT
- Strict JSON only: double quotes, no trailing commas.

### EXAMPLE

Input:
[
  "<Lily> looks at her phone.",
  "<robot> offers the white mug with the drink to <Lily>.",
  "<Emma> picks up <David>'s bag from the table.",
  "<Sarah> gives the book to <Tom>.",
  "<Lily> turns left."
]

Output:
[
  ["<Lily>", "looks at", "phone@<Lily>"],
  ["<robot>", "offers", "mug#white"],
  ["<Lily>", "receives", "mug#white"],
  ["<Emma>", "picks up", "bag@<David>"],
  ["<Sarah>", "gives", "book"],
  ["<Tom>", "receives", "book"],
  ["<Lily>", "turns left", null]
]

Note: "phone@<Lily>" and "bag@<David>" use ownership because they are personal items. "mug#white" and "book" have no ownership because they are shared/public objects being passed between characters. Direction "left" is merged into the predicate "turns left" rather than being a separate object.

Now convert the following lines into triples:
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
- Keep character names as provided (e.g., <character_1>, <robot>)
- Do not include clip numbers or scene labels in the summary
- There might be conflict or misleading information provided, you should be able to handle it and provide a coherent summary.

Now summarize the following clips:
"""

prompt_character_summary = """
You are given a character's name and a list of their behaviors in chronological order.

Your task is to summarize the character's attributes: 
- Personality (e.g., confident, nervous)
- Role/profession (e.g., host, newcomer) 
- Interests or background (when inferable) 
- Distinctive behaviors or traits (e.g., speaks formally, fidgets). 
Avoid restating visual facts—focus on identity construction.

Output a JSON array of words or phrases that describe the character's attributes. 
Example: ["student", "enthusiastic", "likes to read"]
"""