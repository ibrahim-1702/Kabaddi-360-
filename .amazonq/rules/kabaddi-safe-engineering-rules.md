AMAZON Q — GLOBAL ENGINEERING RULES
(Kabaddi Ghost Trainer Project)

These rules are ALWAYS ACTIVE and override all prompts unless explicitly stated.

---

## 1. PROJECT SCOPE
- Project: Kabaddi Ghost Trainer
- Current stable stage: Level-1 pose pipeline
- Input format: numpy.ndarray of shape (T, 17, 2)
- Skeleton format: COCO-17 ONLY

No AR, no live video, no feedback generation unless explicitly approved.

---

## 2. INPUT ASSUMPTIONS
- Do NOT assume any user input video exists.
- Pre-recorded or masked videos are NOT user input.
- Operate only on existing `.npy` pose files unless stated otherwise.

---

## 3. NO HALLUCINATION POLICY
- Do NOT invent:
  - files
  - folders
  - modules
  - classes
  - datasets
  - results
- If a required file or behavior is missing, STOP and ask.

---

## 4. CHANGE DISCIPLINE
- One small change at a time.
- No refactors unless explicitly requested.
- No optimizations unless correctness is already verified.
- Modify only files explicitly mentioned in the task.

---

## 5. DEVELOPMENT WORKFLOW (MANDATORY)
You MUST follow this order:

1. Restate your understanding of the task.
2. Propose the smallest safe change (design only).
3. Wait for approval before coding.
4. Implement exactly what was approved.
5. Explain how to verify the change.

Skipping steps is not allowed.

---

## 6. LEGACY & IGNORE POLICY
- Do NOT modify legacy or deprecated code.
- Ignore files/folde
