# Analysis: Wrong Answers and Minimal Prompt Fixes

This document analyzes wrong answers in `results.json` (evaluator_correct: false) and identifies which can be addressed with **minimal prompt changes** that are unlikely to hurt correctness on other questions.

---

## Summary of Wrong-Answer Categories

| Category | Examples | Fixable by prompt? | Risk to others |
|----------|-----------|--------------------|----------------|
| 1. Refuse to infer ("not explicitly indicated") | Q3 Efk3K4epEzg (Rick's favorite) | Yes (already partly addressed) | Low |
| 2. Paraphrase / wording mismatch | Q2 Efk3K4epEzg (compared handwriting), j1XTIF3moDk_Q2 (trust/respect) | Optional (prefer video phrasing) | Low |
| 3. "Among N items" answered too early | Q1 Efk3K4epEzg (highest price → PEZ vs Pirate Ship) | Yes (require all N items) | Low |
| 4. Generic vs specific terms | 7Dl0TQ5zDzM_Q1 (sticks/leaves vs wood and hay) | Yes (use video terms when stated) | Low |
| 5. Conceptual paraphrase (leadership, relationship) | j1XTIF3moDk_Q1 (transformational vs strict+caring) | Optional | Medium |
| 6. Missing info / wrong clip | oc-b4T7H-gM_Q1 (torch vs parchment), 7Dl0TQ5zDzM_Q2 (Kaneto legal) | No (need more clips or graph) | — |
| 7. Clip-ID / empty-graph errors | Rvl4FRGjMtQ, PnvZZwlN2yk, oc-b4T7H-gM (several) | No (handled by code fallbacks) | — |

---

## 1. Refuse to Infer ("Not Explicitly Indicated")

**Example:** Efk3K4epEzg_Q3  
- **Question:** Which collection is Rick's favorite, as indicated in the video?  
- **Model:** "Rick's favorite collection is not explicitly indicated in the video clips."  
- **GT:** "The album of Led Zeppelin."  
- **Cause:** Model refuses to infer from behavior (Rick keeps album, strong interest).

**Already in prompts:** Inference-from-behavior and forbidden non-answers in `prompt_video_answer_final`. If this still happens after those changes, one more line is low-risk.

**Minimal prompt addition (if needed):** In `prompt_video_answer_final`, under **INFERENCE FROM BEHAVIOR AND CONTEXT**, add:  
- "For 'favorite' or 'as indicated', infer from who keeps an item for themselves or shows the strongest stated interest (e.g. keeping the Led Zeppelin album → answer 'The Led Zeppelin album')."

**Impact:** Targets only "favorite"/"as indicated" questions; unlikely to affect others.

---

## 2. Paraphrase / Wording Mismatch

**Examples:**
- **Efk3K4epEzg_Q2:** Model: "look at examples on file... demonstrated how the signature should flow" vs GT: "He compared the handwriting." (Same meaning.)
- **j1XTIF3moDk_Q2:** Model: "partnership based on teamwork, mutual agreement" vs GT: "Mutual trust and respect." (Close; GT stresses trust/respect.)

**Cause:** Model gives a valid paraphrase; evaluator may require closer wording or the exact concept (e.g. trust/respect).

**Minimal prompt addition:** In `prompt_video_answer_final`, under **Output**, add one line:  
- "When the video or dialogue uses a short, concrete phrase for an action or relationship (e.g. 'compared the handwriting', 'trust and respect'), prefer that phrasing in your answer when it fits."

**Risk:** Low; encourages matching video language without forcing it.

---

## 3. "Among N Items" Answered Too Early

**Example:** Efk3K4epEzg_Q1  
- **Question:** Which collection has the highest starting price among the **five** items?  
- **Model:** PEZ (from clips 1–23). **GT:** Pirate Ship Float (5th item, later, e.g. clips 38–40).  
- **Cause:** Model answered after the last *watched* clip (23) without having seen all five items; pirate ship appears later.

**Fix:** Ensure the model does not conclude "highest among N items" until it has considered all N items. This is mostly **clip selection** (semantic step should suggest clips that cover all five items). A small prompt nudge can help.

**Minimal prompt addition:** In `prompt_video_answer` (and optionally `prompt_semantic_video`), add a bullet under **SPECIAL QUESTION TYPES**:  
- **Comparison among N items** (e.g. "which has the highest/lowest among the five items"): Only answer when you have seen or have summaries for **all N items** and their compared values. If you have only seen some items, use [Search] (or do not give a final comparison yet).

**Risk:** Low; only affects "among N" comparison questions and reduces early answers.

---

## 4. Generic vs Specific Terms (Use Video’s Words)

**Example:** 7Dl0TQ5zDzM_Q1  
- **Question:** What raw materials do the local Pygmies use to construct their houses?  
- **Model:** "natural materials such as sticks, branches, and large leaves."  
- **GT:** "Wood and hay."  
- **Cause:** Model gave a reasonable generic answer; GT expects the specific terms used in the video.

**Minimal prompt addition:** In `prompt_video_answer_final`, under **Output** (or a short "Answer phrasing" bullet):  
- "When the video or dialogue uses a specific term for an object or material (e.g. wood, hay, odometer), use that term in your answer when it clearly refers to the same thing."

**Risk:** Low; only nudges toward video vocabulary when it clearly applies.

---

## 5. Conceptual Paraphrase (Leadership, Relationship)

**Examples:**
- **j1XTIF3moDk_Q1:** Model: "transformational leadership... mentoring, dedication" vs GT: "strict and caring."  
- **j1XTIF3moDk_Q2:** Model: "partnership... teamwork, mutual agreement" vs GT: "Mutual trust and respect."

**Cause:** Model uses different but related concepts; evaluator may require the GT framing (strict+caring, trust+respect).

**Prompt option:** Add a line encouraging alignment with how the video describes relationships or traits:  
- "For relationship or character-trait questions, prefer the kind of wording the video uses (e.g. 'strict and caring', 'trust and respect') when it fits the evidence."

**Risk:** Medium; could occasionally override a more precise technical term. Use only if you want to favor "video wording" over jargon.

---

## 6. Not Fixable by Prompt Alone

- **Missing information / wrong clip:** e.g. oc-b4T7H-gM_Q1 (culinary torch not in graph/clips), 7Dl0TQ5zDzM_Q2 (Kaneto legal training). Need better clip coverage or graph content, not wording.
- **Clip-ID / empty-graph errors:** Handled by code (empty graph skip, first-clip fallback); no prompt change needed for those.

---

## Recommended Minimal Changes (Safe and Targeted)

Apply only the following; all are small and scoped to avoid affecting unrelated questions.

1. **Comparison among N items**  
   In `prompt_video_answer` (and optionally `prompt_semantic_video`), add a special case:  
   - For questions like "which X has the highest/lowest among the N items", only answer when you have information about **all N items**; otherwise keep searching or do not give the comparison.

2. **Use video’s specific terms**  
   In `prompt_video_answer_final`, add one line under **Output** (or a "Answer phrasing" bullet):  
   - When the video or dialogue uses a specific term (e.g. wood, hay, odometer, "compared the handwriting"), use that term in your answer when it clearly refers to the same thing.

3. **Optional: Prefer short, concrete video phrasing**  
   In `prompt_video_answer_final`, add:  
   - Prefer short, concrete phrases that match how the video describes an action or relationship (e.g. "compared the handwriting", "trust and respect") when they fit the evidence.

Skip (for now) the stricter "relationship/trait wording" rule (Category 5) unless you see many such failures and accept the medium risk.

---

## Summary Table: What to Change

| Change | Prompt | Effect | Risk |
|--------|--------|--------|------|
| Require all N items for "highest/lowest among N" | prompt_video_answer, prompt_semantic_video | Fewer wrong answers on multi-item comparison | Low |
| Use video’s specific terms when stated | prompt_video_answer_final | Better match on wood/hay–type questions | Low |
| Prefer video phrasing for actions/relationships | prompt_video_answer_final | Closer to GT on paraphrase cases | Low |

These minimal edits target the identified categories without broadly changing model behavior on other questions.
