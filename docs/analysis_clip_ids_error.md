# Analysis: "Could not extract clip IDs from content: []"

## Summary

The error **"Could not extract clip IDs from content: []"** occurs in `reason.py` when:

1. The semantic step returns **Action: [Search]** (so the system should watch video clips).
2. **Content** is parsed from the LLM response and passed to `extract_clip_ids(parsed['content'])`.
3. `extract_clip_ids()` returns an **empty list** (no clip IDs found in the content string).
4. The code raises: `ValueError("Could not extract clip IDs from content: {parsed['content']}")`.

So the **displayed "[]"** in the message is the value of `parsed['content']` (e.g. the literal string `"[]"` or a sentence with no digits). The pipeline then stops and the result is stored with only `error`, `question`, `video_name`, etc.—no `parse_query_output`, `graph_search_results`, or `semantic_video_output`—so we cannot see the exact LLM output for those failed runs.

---

## Affected Questions (from `data/results/results.json`)

| Result key           | Video         | Question |
|----------------------|---------------|----------|
| Rvl4FRGjMtQ_Q2       | Rvl4FRGjMtQ   | Where is the author originally from? |
| Rvl4FRGjMtQ_Q1       | Rvl4FRGjMtQ   | After writing down the cost of buying a car on the blackboard, what specific indicator did the author check next? |
| oc-b4T7H-gM_Q2       | oc-b4T7H-gM   | Who are the target customers of this coffee shop? |
| oc-b4T7H-gM_Q4       | oc-b4T7H-gM   | Is Jessica a lively person? |
| oc-b4T7H-gM_Q5       | oc-b4T7H-gM   | Why does Jessica slice the potatoes into thin chips? |
| PnvZZwlN2yk_Q1       | PnvZZwlN2yk   | What is the approximate age range of J.F. Harris? |
| PnvZZwlN2yk_Q2       | PnvZZwlN2yk   | Who expressed a different opinion from the others during the first-round vote to identify the non-millionaire? |

**Total: 7 questions across 3 videos.**

---

## Root Causes

### 1. Empty episodic memory (Rvl4FRGjMtQ, PnvZZwlN2yk)

- **Rvl4FRGjMtQ**: `data/episodic_memory/Rvl4FRGjMtQ.json` is **`{}`** (empty object).
- **PnvZZwlN2yk**: `data/episodic_memory/PnvZZwlN2yk.json` is **`{}`** (empty object).

So for these two videos there are **no clips** in episodic memory. That implies either:

- `process_full_video` was never run for them, or
- It was run but `data/frames/{video_name}/` had no subdirectories (no clip folders), or
- It failed before writing any clip data.

The graph is then built from empty or nearly empty episodic data. When the LLM is given "Extracted knowledge from graph" and chooses **[Search]**, it has **no clip IDs in the input** (nothing like `[1]`, `[2]`, … in the text). It then often outputs **Content: []** or a prose sentence with no numbers, so `extract_clip_ids()` returns `[]` and the error is raised.

### 2. Only one clip in episodic memory (oc-b4T7H-gM)

- **oc-b4T7H-gM**: `data/episodic_memory/oc-b4T7H-gM.json` has **only one key: `"52"`**.

So the graph only has edges with **clip_id 52**. For Q2, Q4, Q5 the LLM still returns **Action: [Search]** with **Content** that yields no clip IDs. Possible reasons:

- Graph search returns mostly high-level attributes (no `[52]` in the text), so the model does not “see” any clip ID and outputs something like `Content: []` or “no relevant clips.”
- The model decides the graph is insufficient and outputs a prose Content with **no digits** (e.g. “The graph does not contain sufficient information to identify relevant clips.”). Then `extract_clip_ids()` finds no numbers and returns `[]`.

So even when clip IDs exist in the graph, **format non-compliance or “no relevant clips” phrasing** leads to empty `content` and thus empty clip list.

### 3. Parser behavior

- **`extract_clip_ids(content)`** in `utils/reasoning/response_parser.py`:
  - First tries: `re.search(r'\[([\d,\s]+)\]', content)` (bracket list like `[1, 2, 3]`).
  - Fallback: `re.findall(r'\d+', content)` (any digits in the string).
- If `content` is the literal string **`"[]"`**, the first regex matches but the inner group is empty, and the code builds a list from an empty split → **`[]`**.
- If `content` is prose with **no digits**, the fallback also returns **`[]`**.

So both “Content: []” and “Content: no numbers” lead to an empty list and then to the ValueError in `reason.py`.

---

## Flow Recap

1. **Graph search** returns a string that may or may not include clip IDs (e.g. `[52]` in low-level lines).
2. **Semantic step** (`prompt_semantic_video`) gets that string and outputs **Action** and **Content**.
3. When **Action = [Search]**, the pipeline expects **Content** to contain clip IDs (e.g. `[1, 2, 3]` or at least some digits).
4. **`parse_semantic_response`** extracts `content` (e.g. `"[]"` or a sentence).
5. **`extract_clip_ids(content)`** returns `[]` when:
   - Content is `"[]"`, or
   - Content has no digits.
6. **`reason.py`** does `if not clip_ids: raise ValueError(...)`, so the run fails and only the error is stored in `results.json`.

---

## Recommended Fixes (no code changes in this doc)

### 1. Fix empty episodic memory (Rvl4FRGjMtQ, PnvZZwlN2yk)

- Ensure **frames exist** for these videos:  
  `data/frames/Rvl4FRGjMtQ/`, `data/frames/PnvZZwlN2yk/` with subdirs named by clip ID (e.g. `1`, `2`, …).
- Run **`process_full_video`** for each so that:
  - Episodic memory is populated (`data/episodic_memory/{video_name}.json` has clip keys).
  - The graph is built from that episodic memory.
- If frames are missing, fix the pipeline that downloads/extracts frames for these videos so that memorization can run.

### 2. Prompt: require non-empty clip list when Action is [Search]

In **`prompt_semantic_video`** (in `utils/prompts.py`):

- State explicitly: when **Action is [Search]**, **Content MUST be a non-empty list of clip IDs** in bracket notation, e.g. `[1, 2, 3]`.
- Add: “Use clip IDs that appear in the extracted graph (e.g. the numbers in brackets like [X] in the low-level information). If no clip IDs appear in the graph, use [1] as default so that at least one clip can be watched.”

This reduces the chance the LLM outputs `Content: []` or prose with no numbers.

### 3. Code fallback when clip_ids is empty

In **`reason.py`**, when **action is Search** and **`extract_clip_ids(parsed['content'])`** returns **[]**:

- **Do not raise** immediately.
- **Fallback**: get a list of available clip IDs for that video, e.g. by:
  - Reading `data/episodic_memory/{video_name}.json` and using its keys (as integers), or
  - Listing subdirs of `data/frames/{video_name}/` and using their names as integers.
- Use the first clip or first N clips (e.g. first 5) as `clip_ids` and continue **watch_video_clips**.
- Optionally log a warning: “No clip IDs in Content; using fallback clips {clip_ids}.”

This keeps the pipeline from failing when the LLM outputs empty or non-compliant Content.

### 4. More robust `extract_clip_ids` (optional)

In **`utils/reasoning/response_parser.py`**:

- If after the current logic the list is empty and the string is exactly `"[]"` or empty/whitespace, you could return a default (e.g. `[1]`) only when the caller has a way to pass `video_name` (so that reason.py can still override with a better fallback from episodic memory or frames). Alternatively, leave `extract_clip_ids` as-is and handle only in `reason.py` with the fallback above.

---

## Summary Table

| Video         | Episodic memory      | Likely cause of Content: [] / no IDs     |
|--------------|----------------------|------------------------------------------|
| Rvl4FRGjMtQ  | Empty `{}`           | No clips in graph → LLM has nothing to output. |
| PnvZZwlN2yk  | Empty `{}`           | Same.                                   |
| oc-b4T7H-gM  | One clip `"52"`      | Graph may not show [52] in text, or LLM outputs “no relevant clips” / prose with no digits. |

Fixing empty memorization for the two videos and adding a prompt + code fallback for empty clip IDs should prevent this error and allow the pipeline to continue even when the LLM does not return a valid clip list.
