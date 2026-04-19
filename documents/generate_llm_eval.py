"""
LLM Feedback Quality Evaluation Script
Runs engineered vs baseline comparison across sessions and generates charts.

Run from: kabaddi_trainer/
Output:   documents/Report_Final/figures/eval/llm_*.png
"""

import os, sys, json, time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.abspath('.'))

from llm_feedback.context_engine import generate_context, load_raw_scores
from llm_feedback.prompt_builder import build_prompts
from llm_feedback.llm_client import generate_feedback
from llm_feedback.feedback_metrics import compute_all_metrics

RESULTS_DIR  = 'data/results'
OUT_DIR      = 'documents/Report_Final/figures/eval'
TECHNIQUE    = 'hand_touch'
MAX_SESSIONS = 6   # limit to keep runtime reasonable (~6 x 2 x 2min = ~24min worst case)

os.makedirs(OUT_DIR, exist_ok=True)

METRIC_LABELS = ['Groundedness', 'Hallucination\n(lower=better)', 'Specificity', 'Relevance', 'Technique\nAwareness']
METRIC_KEYS   = ['groundedness', 'hallucination', 'specificity', 'relevance', 'technique_awareness']

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'axes.grid': True,
    'grid.color': '#E5E5E5',
    'grid.linestyle': '--',
    'grid.linewidth': 0.6,
    'figure.dpi': 150,
})

# ── Collect sessions ──────────────────────────────────────────────────────────
sessions = []
for d in sorted(os.listdir(RESULTS_DIR)):
    ctx_path     = os.path.join(RESULTS_DIR, d, 'context.json')
    results_path = os.path.join(RESULTS_DIR, d, 'results.json')
    if os.path.exists(ctx_path) and os.path.exists(results_path):
        sessions.append({'id': d, 'ctx': ctx_path, 'results': results_path})
    if len(sessions) >= MAX_SESSIONS:
        break

print(f"Evaluating {len(sessions)} sessions...")

# ── Run evaluation ────────────────────────────────────────────────────────────
engineered_results = []
baseline_results   = []

for i, s in enumerate(sessions):
    print(f"\n[{i+1}/{len(sessions)}] Session: {s['id'][:8]}...")

    with open(s['ctx']) as f:
        context = json.load(f)

    # --- Engineered response ---
    print("  Generating engineered response...")
    prompts = build_prompts(context, technique_name=TECHNIQUE)
    eng_result = generate_feedback(prompts['system'], prompts['instruction'])

    if eng_result['generation_status'] == 'success':
        eng_metrics = compute_all_metrics(eng_result['feedback_text'], context, TECHNIQUE)
        engineered_results.append(eng_metrics)
        print(f"  Engineered composite: {eng_metrics['overall_percentage']}%")
    else:
        print(f"  Engineered FAILED: {eng_result.get('error_message')}")
        continue

    # --- Baseline response ---
    print("  Generating baseline response...")
    raw_result = generate_feedback(
        system_prompt="You are an assistant.",
        instruction_prompt="Give me feedback on my kabaddi raid technique."
    )

    if raw_result['generation_status'] == 'success':
        raw_metrics = compute_all_metrics(raw_result['feedback_text'], context, TECHNIQUE)
        baseline_results.append(raw_metrics)
        print(f"  Baseline composite:   {raw_metrics['overall_percentage']}%")
    else:
        print(f"  Baseline FAILED: {raw_result.get('error_message')}")
        baseline_results.append(None)

print(f"\nCompleted: {len(engineered_results)} engineered, {sum(1 for r in baseline_results if r)} baseline")

# ── Helper: extract per-metric scores ────────────────────────────────────────
def get_scores(results, key):
    return [r[key]['score'] for r in results if r is not None]

def avg_scores(results):
    avgs = []
    for key in METRIC_KEYS:
        scores = get_scores(results, key)
        avgs.append(np.mean(scores) if scores else 0)
    return avgs

eng_avgs = avg_scores(engineered_results)
bas_avgs = avg_scores([r for r in baseline_results if r])
eng_composites = [r['overall_percentage'] for r in engineered_results]
bas_composites = [r['overall_percentage'] for r in baseline_results if r]

# ── Figure 1: Grouped bar — avg per metric, engineered vs baseline ────────────
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(METRIC_LABELS))
w = 0.35
ax.bar(x - w/2, eng_avgs, w, label='Prompt-Engineered', color='#4C72B0')
ax.bar(x + w/2, bas_avgs, w, label='Baseline (Raw)',    color='#DD8452')
ax.set_xticks(x)
ax.set_xticklabels(METRIC_LABELS, fontsize=10)
ax.set_ylabel('Average Score (1–5)')
ax.set_ylim(0, 6)
ax.set_title('LLM Feedback Quality: Engineered vs. Baseline (Per Metric)')
ax.axhline(y=3, color='gray', linestyle=':', linewidth=1, label='Midpoint (3)')
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_metric_comparison.png'))
plt.close()
print("Saved: llm_metric_comparison.png")

# ── Figure 2: Composite score per session ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(eng_composites))
ax.plot(x, eng_composites, 'o-', color='#4C72B0', linewidth=2, markersize=7, label='Prompt-Engineered')
if bas_composites:
    ax.plot(x[:len(bas_composites)], bas_composites, 's--', color='#DD8452', linewidth=2, markersize=7, label='Baseline (Raw)')
ax.axhline(y=np.mean(eng_composites), color='#4C72B0', linestyle=':', linewidth=1.5,
           label=f'Eng. avg: {np.mean(eng_composites):.1f}%')
if bas_composites:
    ax.axhline(y=np.mean(bas_composites), color='#DD8452', linestyle=':', linewidth=1.5,
               label=f'Base avg: {np.mean(bas_composites):.1f}%')
ax.set_xlabel('Session')
ax.set_ylabel('Composite Quality Score (%)')
ax.set_title('LLM Feedback Composite Score Per Session')
ax.set_xticks(x)
ax.set_xticklabels([f'S{i+1}' for i in x])
ax.set_ylim(0, 110)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_composite_per_session.png'))
plt.close()
print("Saved: llm_composite_per_session.png")

# ── Figure 3: Radar chart — avg metric profile ────────────────────────────────
# Invert hallucination for radar (higher = better)
def radar_scores(avgs):
    r = list(avgs)
    r[1] = 6 - r[1]   # invert hallucination
    return r

eng_radar = radar_scores(eng_avgs)
bas_radar = radar_scores(bas_avgs)
labels_radar = ['Groundedness', 'Hallucination\n(inverted)', 'Specificity', 'Relevance', 'Technique\nAwareness']
N = len(labels_radar)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
for scores, color, label in [(eng_radar, '#4C72B0', 'Prompt-Engineered'),
                              (bas_radar, '#DD8452', 'Baseline (Raw)')]:
    vals = scores + scores[:1]
    ax.plot(angles, vals, 'o-', linewidth=2, color=color, label=label)
    ax.fill(angles, vals, alpha=0.15, color=color)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels_radar, fontsize=10)
ax.set_ylim(0, 5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_title('LLM Feedback Quality Radar Profile', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_radar_profile.png'))
plt.close()
print("Saved: llm_radar_profile.png")

# ── Figure 4: Hallucination count distribution ────────────────────────────────
eng_halluc = [r['hallucination']['total_hallucinations'] for r in engineered_results]
bas_halluc = [r['hallucination']['total_hallucinations'] for r in baseline_results if r]

fig, ax = plt.subplots(figsize=(8, 5))
bins = range(0, max(max(eng_halluc, default=0), max(bas_halluc, default=0)) + 3)
ax.hist(eng_halluc, bins=bins, alpha=0.7, color='#4C72B0', label=f'Engineered (avg={np.mean(eng_halluc):.1f})', align='left')
ax.hist(bas_halluc, bins=bins, alpha=0.7, color='#DD8452', label=f'Baseline (avg={np.mean(bas_halluc):.1f})',   align='left')
ax.set_xlabel('Hallucination Count per Response')
ax.set_ylabel('Number of Sessions')
ax.set_title('Hallucination Count Distribution')
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_hallucination_dist.png'))
plt.close()
print("Saved: llm_hallucination_dist.png")

# ── Figure 5: Composite score improvement bar ─────────────────────────────────
if bas_composites:
    improvement = np.mean(eng_composites) - np.mean(bas_composites)
    pct_improvement = (improvement / np.mean(bas_composites)) * 100

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(['Baseline\n(Raw)', 'Prompt-\nEngineered'],
                  [np.mean(bas_composites), np.mean(eng_composites)],
                  color=['#DD8452', '#4C72B0'], width=0.5)
    for bar, val in zip(bars, [np.mean(bas_composites), np.mean(eng_composites)]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}%', ha='center', fontweight='bold')
    ax.set_ylabel('Composite Quality Score (%)')
    ax.set_ylim(0, 110)
    ax.set_title(f'Overall Improvement: +{pct_improvement:.1f}%')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'llm_improvement_bar.png'))
    plt.close()
    print("Saved: llm_improvement_bar.png")

# ── Print summary table ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY TABLE")
print("="*60)
print(f"{'Metric':<30} {'Engineered':>12} {'Baseline':>12}")
print("-"*60)
for i, key in enumerate(METRIC_KEYS):
    print(f"{METRIC_LABELS[i].replace(chr(10),' '):<30} {eng_avgs[i]:>12.2f} {bas_avgs[i]:>12.2f}")
print("-"*60)
print(f"{'Composite Score (%)':<30} {np.mean(eng_composites):>12.1f} {np.mean(bas_composites) if bas_composites else 0:>12.1f}")
print("="*60)
print(f"\nAll figures saved to: {OUT_DIR}")
