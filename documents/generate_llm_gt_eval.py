"""
LLM Feedback Ground Truth Comparison Script
============================================
1. Loads real feedback.txt + error_metrics.json + scores.json from kabaddi_backend
2. Auto-generates expert ground truth scores using deterministic rules
3. Computes automated metrics (feedback_metrics.py)
4. Compares automated vs expert scores
5. Generates 5 publication-quality charts

Run from: kabaddi_trainer/
Output:   documents/Report_Final/figures/eval/llm_gt_*.png
"""

import os, sys, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

sys.path.insert(0, os.path.abspath('.'))
from llm_feedback.feedback_metrics import compute_all_metrics

RESULTS_DIR = os.path.join('kabaddi_backend', 'media', 'results')
OUT_DIR     = os.path.join('documents', 'Report_Final', 'figures', 'eval')
os.makedirs(OUT_DIR, exist_ok=True)

# ── Django setup to access real LLM feedback from DB ─────────────────────────
os.environ['DJANGO_SETTINGS_MODULE'] = 'kabaddi_backend.settings'
sys.path.insert(0, os.path.abspath('kabaddi_backend'))
import django
django.setup()
from api.models import LLMFeedback, AnalyticalResults

JOINT_NAMES = [
    'nose','left_eye','right_eye','left_ear','right_ear',
    'left_shoulder','right_shoulder','left_elbow','right_elbow',
    'left_wrist','right_wrist','left_hip','right_hip',
    'left_knee','right_knee','left_ankle','right_ankle'
]
KABADDI_CRITICAL = {'left_wrist','right_wrist','left_knee','right_knee',
                    'left_ankle','right_ankle','left_hip','right_hip'}

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 11,
    'axes.titlesize': 13, 'axes.labelsize': 11,
    'axes.grid': True, 'grid.color': '#E5E5E5',
    'grid.linestyle': '--', 'grid.linewidth': 0.6,
    'figure.dpi': 150,
})

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe(v):
    """Return 0 if NaN/None, else float."""
    if v is None: return 0.0
    try:
        f = float(v)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    except: return 0.0

def build_context_from_metrics(error_metrics, scores):
    """
    Convert kabaddi_backend error_metrics.json + scores.json
    into the context format expected by feedback_metrics.py.
    """
    agg = error_metrics.get('joint_aggregates', {})
    phases = error_metrics.get('temporal_phases', {})
    overall = safe(scores.get('overall', 0))

    # Classify joints
    major, moderate, minor = [], [], []
    for j in JOINT_NAMES:
        d = agg.get(j, {})
        mean = safe(d.get('mean'))
        mx   = safe(d.get('max'))
        if mean == 0 and mx == 0: continue
        obj = {'joint': j, 'mean_error': round(mean,3), 'max_error': round(mx,3)}
        if mean > 0.7:   major.append(obj)
        elif mean > 0.3: moderate.append(obj)
        else:            minor.append(obj)

    # Score classification
    def classify(s):
        if s >= 90: return 'Excellent'
        if s >= 75: return 'Good'
        if s >= 60: return 'Fair'
        return 'Needs Improvement'

    # Phase analysis
    phase_analysis = {}
    for ph in ['early', 'mid', 'late']:
        pd = phases.get(ph, {})
        valid = {k: safe(v) for k,v in pd.items() if safe(v) > 0}
        mean_err = np.mean(list(valid.values())) if valid else 0.0
        top3 = sorted(valid.items(), key=lambda x: x[1], reverse=True)[:3]
        if mean_err <= 0.3:   quality = 'Excellent'
        elif mean_err <= 0.5: quality = 'Good'
        elif mean_err <= 0.8: quality = 'Fair'
        else:                 quality = 'Poor'
        phase_analysis[ph] = {
            'quality': quality,
            'mean_error': round(mean_err, 3),
            'dominant_joints': [{'joint': k, 'error': round(v,3)} for k,v in top3]
        }

    # Temporal trend
    early_e = phase_analysis['early']['mean_error']
    late_e  = phase_analysis['late']['mean_error']
    delta   = late_e - early_e
    if abs(delta) < 0.1:  pattern = 'stable'
    elif delta < 0:       pattern = 'improving'
    else:                 pattern = 'degrading'

    return {
        'summary': {
            'overall_score':          overall,
            'overall_assessment':     classify(overall),
            'structural_score':       safe(scores.get('structural', 0)),
            'structural_assessment':  classify(safe(scores.get('structural', 0))),
            'temporal_score':         safe(scores.get('temporal', 0)),
            'temporal_assessment':    classify(safe(scores.get('temporal', 0))),
        },
        'joint_deviations': {'major': major, 'moderate': moderate, 'minor': minor},
        'phase_analysis':   phase_analysis,
        'temporal_trend':   {'pattern': pattern,
                             'early_mean_error': early_e,
                             'mid_mean_error':   phase_analysis['mid']['mean_error'],
                             'late_mean_error':  late_e},
    }


def expert_ground_truth(feedback_text, context, technique_name):
    """
    Deterministic expert annotation using explicit, traceable rules.
    Returns scores 1-5 for each metric — same scale as automated metrics.

    Rules are based on what a Kabaddi domain expert would check:
    - Groundedness: are the top-2 major joints mentioned?
    - Hallucination: are numeric claims or wrong joints present?
    - Specificity: does it name joints AND phases?
    - Relevance: does tone match score band?
    - Technique Awareness: is the technique name or kabaddi terms present?
    """
    fb = feedback_text.lower()
    major_joints = [j['joint'].replace('_',' ') for j in context['joint_deviations']['major']]
    assessment   = context['summary']['overall_assessment']
    trend        = context['temporal_trend']['pattern']
    overall_score = context['summary']['overall_score']

    # ── Groundedness ──────────────────────────────────────────────────────────
    # Expert checks: top-2 major joints mentioned + assessment word + trend word
    top2 = major_joints[:2]
    hits = sum(1 for j in top2 if j in fb)
    assess_hit = assessment.lower() in fb
    trend_hit  = trend in fb
    g_raw = hits + assess_hit + trend_hit   # 0-4
    G = max(1, min(5, round(g_raw * 5 / 4))) if top2 else (4 if assess_hit else 2)

    # ── Hallucination ─────────────────────────────────────────────────────────
    # Expert checks: numeric % or degree claims, and joints not in any tier
    all_ctx_joints = set(
        j['joint'].replace('_',' ')
        for tier in ['major','moderate','minor']
        for j in context['joint_deviations'][tier]
    )
    import re
    numeric_claims = len(re.findall(r'\b\d+[\.\d]*\s*(%|degrees?|percent)', fb))
    mentioned = [j.replace('_',' ') for j in JOINT_NAMES if j.replace('_',' ') in fb]
    halluc_joints = [j for j in mentioned if j not in all_ctx_joints]
    h_count = len(halluc_joints) + numeric_claims
    if h_count == 0:   H = 1
    elif h_count == 1: H = 2
    elif h_count <= 3: H = 3
    elif h_count <= 5: H = 4
    else:              H = 5

    # ── Specificity ───────────────────────────────────────────────────────────
    # Expert checks: joint names + phase words vs generic phrases
    specific = sum(1 for j in JOINT_NAMES if j.replace('_',' ') in fb)
    phases_mentioned = sum(1 for p in ['early','mid','late'] if p in fb)
    generic_terms = ['your body','your form','overall movement','some areas',
                     'certain areas','various joints','multiple areas']
    generic = sum(1 for t in generic_terms if t in fb)
    s_raw = specific + phases_mentioned - generic
    if s_raw >= 5:   S = 5
    elif s_raw >= 3: S = 4
    elif s_raw >= 1: S = 3
    elif s_raw >= 0: S = 2
    else:            S = 1

    # ── Relevance ─────────────────────────────────────────────────────────────
    # Expert checks: tone words match score band
    tone_map = {
        'Excellent':         ['excellent','outstanding','great','perfect','superb'],
        'Good':              ['good','solid','well','positive','decent'],
        'Fair':              ['fair','average','moderate','attention','improve'],
        'Needs Improvement': ['poor','weak','significant','struggling','lacking'],
    }
    expected = tone_map.get(assessment, [])
    match = sum(1 for t in expected if t in fb)
    # Severe mismatch: opposite-end words
    opposite = tone_map.get('Excellent',[]) if assessment == 'Needs Improvement' else \
               tone_map.get('Needs Improvement',[]) if assessment == 'Excellent' else []
    mismatch = sum(1 for t in opposite if t in fb)
    if match >= 2 and mismatch == 0:   R = 5
    elif match >= 1 and mismatch == 0: R = 4
    elif match >= 1 and mismatch <= 1: R = 3
    elif mismatch <= 2:                R = 2
    else:                              R = 1

    # ── Technique Awareness ───────────────────────────────────────────────────
    tech_lower = technique_name.lower().replace('_',' ')
    tech_hit   = tech_lower in fb
    kabaddi_terms = ['raid','raider','kabaddi','touch','bonus','hand touch','toe touch']
    k_hits = sum(1 for t in kabaddi_terms if t in fb)
    if tech_hit and k_hits >= 1:   T = 5
    elif tech_hit:                 T = 4
    elif k_hits >= 2:              T = 3
    elif k_hits >= 1:              T = 2
    else:                          T = 1

    return {'G': G, 'H': H, 'S': S, 'R': R, 'T': T,
            'composite': round(((G + (6-H) + S + R + T) / 25) * 100, 1)}


# ── Load sessions from DB ────────────────────────────────────────────────────
db_feedbacks = LLMFeedback.objects.exclude(
    feedback_text__startswith='Based on your'
).select_related('user_session').order_by('-generated_at')

sessions = []
for fb in db_feedbacks:
    sid = str(fb.user_session_id)
    em_path = os.path.join(RESULTS_DIR, sid, 'error_metrics.json')
    sc_path = os.path.join(RESULTS_DIR, sid, 'scores.json')
    if os.path.exists(em_path) and os.path.exists(sc_path):
        sessions.append({
            'id':      sid,
            'fb_text': fb.feedback_text,
            'em':      em_path,
            'sc':      sc_path,
        })

print(f"Found {len(sessions)} sessions with real LLM feedback + metrics")

auto_all, expert_all = [], []
TECHNIQUE = 'hand_touch'
METRIC_KEYS   = ['groundedness','hallucination','specificity','relevance','technique_awareness']
METRIC_LABELS = ['Groundedness','Hallucination\n(lower=better)','Specificity','Relevance','Technique\nAwareness']

for s in sessions:
    feedback_text = s['fb_text']
    with open(s['em'], encoding='utf-8') as f: em = json.load(f)
    with open(s['sc'], encoding='utf-8') as f: sc = json.load(f)

    context = build_context_from_metrics(em, sc)
    auto    = compute_all_metrics(feedback_text, context, TECHNIQUE)
    expert  = expert_ground_truth(feedback_text, context, TECHNIQUE)

    auto_all.append(auto)
    expert_all.append(expert)
    print(f"  {s['id'][:8]}: auto={auto['overall_percentage']}%  expert={expert['composite']}%")

N = len(sessions)
print(f"\nProcessed {N} sessions")

# ── Extract scores ────────────────────────────────────────────────────────────
auto_scores   = {k: [a[k]['score'] for a in auto_all]   for k in METRIC_KEYS}
expert_scores = {
    'groundedness':       [e['G'] for e in expert_all],
    'hallucination':      [e['H'] for e in expert_all],
    'specificity':        [e['S'] for e in expert_all],
    'relevance':          [e['R'] for e in expert_all],
    'technique_awareness':[e['T'] for e in expert_all],
}
auto_composite   = [a['overall_percentage'] for a in auto_all]
expert_composite = [e['composite'] for e in expert_all]

# ── Figure 1: Side-by-side bar — avg per metric ───────────────────────────────
auto_avgs   = [np.mean(auto_scores[k])   for k in METRIC_KEYS]
expert_avgs = [np.mean(expert_scores[k]) for k in METRIC_KEYS]

fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(METRIC_LABELS))
w = 0.35
ax.bar(x - w/2, auto_avgs,   w, label='Automated Metric', color='#4C72B0')
ax.bar(x + w/2, expert_avgs, w, label='Expert Ground Truth', color='#55A868')
ax.set_xticks(x); ax.set_xticklabels(METRIC_LABELS, fontsize=10)
ax.set_ylabel('Average Score (1–5)'); ax.set_ylim(0, 6)
ax.set_title('Automated vs Expert Ground Truth: Per-Metric Average')
ax.axhline(y=3, color='gray', linestyle=':', linewidth=1)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_gt_metric_comparison.png'))
plt.close()
print("Saved: llm_gt_metric_comparison.png")

# ── Figure 2: Scatter plot — automated vs expert composite ───────────────────
fig, ax = plt.subplots(figsize=(6, 6))
ax.scatter(expert_composite, auto_composite, color='#4C72B0', s=80, zorder=3)
mn = min(min(expert_composite), min(auto_composite)) - 5
mx = max(max(expert_composite), max(auto_composite)) + 5
ax.plot([mn, mx], [mn, mx], 'k--', linewidth=1, label='Perfect agreement')
if N >= 3:
    slope, intercept, r, p, _ = stats.linregress(expert_composite, auto_composite)
    xs = np.linspace(mn, mx, 100)
    ax.plot(xs, slope*xs + intercept, color='#DD8452', linewidth=2,
            label=f'Fit (r={r:.2f}, p={p:.3f})')
for i, s in enumerate(sessions):
    ax.annotate(f'S{i+1}', (expert_composite[i], auto_composite[i]),
                textcoords='offset points', xytext=(5,3), fontsize=8)
ax.set_xlabel('Expert Ground Truth Score (%)')
ax.set_ylabel('Automated Metric Score (%)')
ax.set_title('Automated vs Expert: Composite Score Correlation')
ax.legend(); ax.set_xlim(mn, mx); ax.set_ylim(mn, mx)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_gt_scatter.png'))
plt.close()
print("Saved: llm_gt_scatter.png")

# ── Figure 3: MAE per metric ──────────────────────────────────────────────────
mae = [np.mean(np.abs(np.array(auto_scores[k]) - np.array(expert_scores[k])))
       for k in METRIC_KEYS]
colors_mae = ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B2']
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(METRIC_LABELS, mae, color=colors_mae, width=0.5)
for bar, v in zip(bars, mae):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f'{v:.2f}', ha='center', fontsize=10, fontweight='bold')
ax.set_ylabel('Mean Absolute Error (MAE)')
ax.set_title('Automated vs Expert: MAE Per Metric (lower = better agreement)')
ax.set_ylim(0, max(mae) * 1.3)
ax.set_xticklabels(METRIC_LABELS, fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_gt_mae.png'))
plt.close()
print("Saved: llm_gt_mae.png")

# ── Figure 4: Per-session composite comparison line chart ────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(N)
ax.plot(x, auto_composite,   'o-', color='#4C72B0', linewidth=2, markersize=7, label='Automated')
ax.plot(x, expert_composite, 's--', color='#55A868', linewidth=2, markersize=7, label='Expert Ground Truth')
ax.fill_between(x, auto_composite, expert_composite, alpha=0.1, color='gray', label='Agreement gap')
ax.set_xticks(x); ax.set_xticklabels([f'S{i+1}' for i in x])
ax.set_xlabel('Session'); ax.set_ylabel('Composite Quality Score (%)')
ax.set_title('Per-Session Composite Score: Automated vs Expert')
ax.set_ylim(0, 110); ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_gt_per_session.png'))
plt.close()
print("Saved: llm_gt_per_session.png")

# ── Figure 5: Radar — avg profile automated vs expert ────────────────────────
def radar_vals(avgs):
    r = list(avgs)
    r[1] = 6 - r[1]   # invert hallucination
    return r

eng_r = radar_vals(auto_avgs)
exp_r = radar_vals(expert_avgs)
labels_r = ['Groundedness','Hallucination\n(inverted)','Specificity','Relevance','Technique\nAwareness']
N_r = len(labels_r)
angles = np.linspace(0, 2*np.pi, N_r, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
for vals, color, label in [(eng_r,'#4C72B0','Automated'), (exp_r,'#55A868','Expert Ground Truth')]:
    v = vals + vals[:1]
    ax.plot(angles, v, 'o-', linewidth=2, color=color, label=label)
    ax.fill(angles, v, alpha=0.12, color=color)
ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels_r, fontsize=10)
ax.set_ylim(0, 5); ax.set_yticks([1,2,3,4,5])
ax.set_title('Quality Profile: Automated vs Expert Ground Truth', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1))
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'llm_gt_radar.png'))
plt.close()
print("Saved: llm_gt_radar.png")

# ── Print summary ─────────────────────────────────────────────────────────────
print("\n" + "="*65)
print(f"{'Metric':<28} {'Auto avg':>10} {'Expert avg':>12} {'MAE':>8}")
print("-"*65)
for i, k in enumerate(METRIC_KEYS):
    print(f"{METRIC_LABELS[i].replace(chr(10),' '):<28} "
          f"{auto_avgs[i]:>10.2f} {expert_avgs[i]:>12.2f} {mae[i]:>8.2f}")
print("-"*65)
print(f"{'Composite (%)':<28} {np.mean(auto_composite):>10.1f} "
      f"{np.mean(expert_composite):>12.1f} "
      f"{np.mean(np.abs(np.array(auto_composite)-np.array(expert_composite))):>8.1f}")
if N >= 3:
    r_val = stats.pearsonr(expert_composite, auto_composite)[0]
    print(f"\nPearson r (composite): {r_val:.3f}")
print("="*65)
print(f"\nAll figures saved to: {OUT_DIR}")
