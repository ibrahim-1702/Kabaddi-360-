# Feedback Quality Metrics — Algorithm Analysis & Tightening Proposals

This document explains how each of the 5 automated feedback metrics is currently calculated, identifies weaknesses in each, and proposes concrete tightening strategies.

---

## 1. Groundedness (Higher = Better)

### Current Algorithm

Checks if the feedback text mentions data items that actually exist in the context JSON.

```
Items checked:
  - Joints flagged as major/moderate deviations (set matching)
  - Overall assessment label (e.g., "Fair")
  - Temporal trend pattern (e.g., "improving")

ratio = (joints_mentioned + assessment_match + trend_match) / (total_context_joints + 2)
score = clamp(round(ratio * 5), 1, 5)
```

### Weaknesses

| # | Weakness | Example |
|---|----------|---------|
| 1 | **Only checks presence, not correctness** | Feedback says "your left wrist is excellent" when context says left_wrist is a *major* deviation → still scores as grounded |
| 2 | **Phase quality labels are ignored** | Context has early=Poor, mid=Fair, late=Good — not checked at all |
| 3 | **Structural/temporal assessment labels not checked** | Only overall_assessment is checked, not structural_assessment or temporal_assessment |
| 4 | **Equal weight for all items** | Mentioning 1 obscure joint counts the same as mentioning the overall assessment |

### Tightening Proposals

- **Check phase quality labels**: Verify if feedback says "early phase was poor" when context says early quality = "Poor"
- **Check structural and temporal assessments**: Add `structural_assessment` and `temporal_assessment` to the items checked (currently only `overall_assessment`)
- **Add dominant joint verification**: Check if the dominant joints per phase (stored in context) are mentioned in the correct phase context
- **Weight major deviations higher**: Major joints should count 2x compared to moderate joints


---

## 2. Hallucination (Lower = Better)

### Current Algorithm

Counts two types of hallucinated content:

```
1. Hallucinated joints:
   mentioned_joints = {all COCO-17 names found in feedback}
   context_joints   = {all joints in major + moderate + minor tiers}
   hallucinated     = mentioned_joints - context_joints

2. Fabricated numeric claims:
   regex: \d+[.\d]* (%|degrees?|percent)
   count all matches

total = |hallucinated_joints| + numeric_claims
score = step_function(total)  →  0→1, 1→2, ≤3→3, ≤5→4, >5→5
```

### Weaknesses

| # | Weakness | Example |
|---|----------|---------|
| 1 | **Step function thresholds are too lenient** | 3 hallucinated joints still only scores 3/5 |
| 2 | **No severity weighting** | Hallucinating a "left ankle" (major body part) counts the same as hallucinating a "nose" |
| 3 | **Doesn't detect fabricated improvement claims** | "You improved by 30%" — the number without a unit isn't caught |
| 4 | **Doesn't detect invented phase claims** | "In the mid phase, your knees were perfect" when context says mid phase quality = "Poor" |
| 5 | **Doesn't catch invented severity claims** | "Minor issues with right shoulder" when right_shoulder is actually a major deviation |

### Tightening Proposals

- **Stricter step function**: 0→1, 1→3, 2→4, ≥3→5 (any hallucination is penalized heavily)
- **Detect fabricated percentages/numbers broadly**: Expand regex to catch standalone numbers like "improved by 30" or "95% accuracy"
- **Phase-claim cross-checking**: If feedback says "early phase was excellent" but context says early quality = "Poor", count as hallucination
- **Severity contradiction detection**: If feedback says a joint is "minor" but context has it as "major", flag it


---

## 3. Specificity (Higher = Better)

### Current Algorithm

Counts specific vs. generic term usage:

```
n_s = count of distinct COCO-17 joint names in feedback
n_g = count of generic terms matched (from list of 11 vague phrases)
n_p = count of phase terms ("early", "mid", "late") found

specificity_index = n_s + n_p - n_g
score = step_function(index)  →  ≥5→5, ≥3→4, ≥1→3, ≥0→2, <0→1
```

### Weaknesses

| # | Weakness | Example |
|---|----------|---------|
| 1 | **"mid" matches sub-words** | "midway through your practice" → counts as a phase mention |
| 2 | **No frequency counting** | Mentioning "left wrist" 10 times counts the same as mentioning it once |
| 3 | **No actionable advice check** | Feedback can name joints without giving any corrective advice |
| 4 | **Generic list is too small (only 11 terms)** | Many other vague phrases like "keep it up", "good job", "try harder" aren't penalized |
| 5 | **Phase terms not verified for correctness** | Saying "early" when talking about a late-phase issue still scores positively |

### Tightening Proposals

- **Word-boundary matching**: Use regex `\bearly\b`, `\bmid\b`, `\blate\b` to avoid sub-word matches
- **Expand generic terms list**: Add common filler phrases: "keep it up", "nice work", "try harder", "focus more", "be careful", "pay attention"
- **Frequency-weighted scoring**: Count total occurrences, not just distinct joint names — repeated specific references show deeper engagement
- **Actionable advice detection**: Check for correction verbs like "straighten", "bend", "extend", "rotate", "lower", "raise" near joint mentions


---

## 4. Relevance (Higher = Better)

### Current Algorithm

Tone-matching between feedback language and the actual score:

```
1. Look up expected tone words for the actual assessment level
   (e.g., "Excellent" → ["excellent", "great", "outstanding", ...])
2. Count matching tone words (m) in feedback
3. Count mismatched tones (d) — ONLY checks extreme opposites:
   - "Excellent" words in "Needs Improvement" context
   - "Needs Improvement" words in "Excellent" context
   
score = conditional:
  m≥2 and d=0 → 5
  m≥1 and d=0 → 4
  m≥1 and d≤1 → 3
  d≤2         → 2
  else        → 1
```

### Weaknesses

| # | Weakness | Example |
|---|----------|---------|
| 1 | **Only checks extreme mismatches** | "Good" words in a "Needs Improvement" context are NOT flagged — only "Excellent" ↔ "Needs Improvement" |
| 2 | **Common words create false positives** | "well" and "good" appear in normal sentences ("as well as", "good morning") — inflates matching |
| 3 | **No score range validation** | Doesn't check if actual numeric score (e.g., 45.2) is consistent with the feedback's claims |
| 4 | **No penalty for hedging** | Feedback that says "decent but could be better" for a 95% score isn't penalized |
| 5 | **"significant" is in the wrong tier** | "significant improvement" (positive) matches "significant" in Needs Improvement tier |

### Tightening Proposals

- **Check ALL adjacent mismatches, not just extremes**: "Good" words in "Needs Improvement" context should also be flagged, not just "Excellent"
- **Context-aware word matching**: Use bigrams/trigrams instead of single words — "significant improvement" ≠ "significant issues"
- **Score range validation**: If overall_score < 60, positive words should count as mismatches. If > 90, negative words should count as mismatches
- **Remove ambiguous words**: Remove "well", "significant", "nice" from tone lists to reduce false positives — keep only clearly valenced words


---

## 5. Technique Awareness (Higher = Better)

### Current Algorithm

```
1. Check if full technique name appears in feedback (boolean)
2. Check which individual words of technique name appear (excluding ≤2 chars)
3. Check for kabaddi-specific terms: ["raid", "raider", "kabaddi", "touch", "bonus", "cant"]

score = conditional:
  full_name + kabaddi_terms → 5
  full_name only           → 4
  partial_words + kabaddi  → 3
  kabaddi_terms only       → 2
  none                     → 1
```

### Weaknesses

| # | Weakness | Example |
|---|----------|---------|
| 1 | **"bonus" matches technique name and kabaddi list** | For technique "Bonus Step", "bonus" appears in both — easily gets score 5 |
| 2 | **No check for technique-specific advice** | Saying "Bonus Step" once in passing scores the same as giving detailed technique-specific coaching |
| 3 | **Kabaddi terms list is too short** | Missing terms like "mat", "lobby", "baulk line", "do-or-die", "super raid", "ankle hold" |
| 4 | **Case sensitivity edge cases** | "BONUS STEP" or "Bonus step" might not match depending on casing |

### Tightening Proposals

- **Deduplicate technique name from kabaddi terms**: Don't count words that overlap between the two checks
- **Multiple mention requirement**: Require the technique name to appear ≥2 times for full score (not just once in passing)
- **Expand kabaddi vocabulary**: Add sport-specific terms: "mat", "lobby", "baulk", "do-or-die raid", "super raid", "running hand touch", "ankle hold", "thigh hold"
- **Context-aware matching**: Check if the technique name appears near actionable advice, not just anywhere


---

## 6. Composite Score

### Current Formula

```
Q = (G + (6 - H) + S + R + T) / 25 × 100
```

### Weakness

- **Equal weighting**: All 5 metrics contribute equally, but Groundedness and Hallucination are arguably more important than Technique Awareness for coaching quality

### Tightening Proposal

- **Weighted composite**: Give higher weight to Groundedness (30%) and Hallucination (30%), with Specificity (20%), Relevance (10%), Technique Awareness (10%)


---

## Summary: Priority Tightening Actions

| Priority | Change | Impact |
|----------|--------|--------|
| 🔴 High | Stricter hallucination thresholds (1 hallucination → score 3) | Raw LLM will score much lower |
| 🔴 High | Check ALL tone mismatches, not just extreme opposites | Better differentiation between engineered and raw |
| 🟡 Medium | Add phase quality label checking to Groundedness | Engineered feedback will score higher |
| 🟡 Medium | Word-boundary matching for phase terms | Fewer false positives in specificity |
| 🟡 Medium | Remove ambiguous tone words ("well", "significant") | Cleaner relevance scoring |
| 🟢 Low | Expand kabaddi vocabulary | Minor improvement to technique awareness |
| 🟢 Low | Weighted composite score | Better reflects real quality |
