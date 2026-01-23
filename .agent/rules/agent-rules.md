---
trigger: always_on
---

AGENT RULES (GLOBAL & NON-NEGOTIABLE)

These rules apply to all development actions at all times.

---

1. INPUT ASSUMPTIONS
- Do NOT assume any user input (video, sensor, live feed) exists unless explicitly stated.
- Pre-recorded or masked videos are NOT user input unless declared as such.

---

2. SCOPE CONTROL
- Do NOT modify files outside the currently approved scope.
- If scope is unclear, STOP and request clarification.
- One change per step. No batching.

---

3. LEGACY & IGNORE POLICY
- Completely ignore all files and folders prefixed with:
  - `_IGNORE_`
  - `_legacy_`
  - `backup`
- Legacy code is READ-ONLY unless explicitly reactivated.

---

4. PIPELINE MODES
- Default mode is **pose-only (.npy) processing**.
- AR playback, live video, feedback generation, and LLM usage are DISABLED by default.
- Any mode change must be explicitly approved.

---

5. NO HALLUCINATION POLICY
- Do NOT invent:
  - files
  - modules
  - classes
  - datasets
  - results
- If something is missing, STOP and report it.

---

6. SEQUENTIAL DEVELOPMENT
- Follow phases strictly:
  1. Understand (read-only)
  2. Design
  3. Implement
  4. Verify
  5. Document
- Never skip or reorder phases.

---

7. CHANGE SAFETY
- No refactoring unless explicitly requested.
- No optimization unless correctness is proven.
- No silent behavior changes.

---

8. VERIFICATION REQUIREMENT
- Every code change must include:
  - How to test it
  - Expected output
  - Failure cases

---

9. DOCUMENTATION SYNC
- Documentation must reflect actual behavior.
- If documentation and code conflict, STOP and flag the mismatch.

---

10. FAIL-FAST RULE
- If an assumption, ambiguity, or contradiction appears:
  ➜ STOP immediately and report.
  ➜ Never proceed based on inferred intent.

---

11. OUTPUT DISCIPLINE
- Engineering tone only
- No motivational or conversational text
- No speculative features

---

12. AUTHORITY
- These rules override all other prompts unless explicitly superseded.
