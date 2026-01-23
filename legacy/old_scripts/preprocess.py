#!/usr/bin/env python3
"""
preprocess.py

Usage:
  python preprocess.py --indir pose_out --outdir preproc_out --plot-joint left_elbow

What it does:
 - Reads per-frame JSONs produced by extract_pose.py
 - Builds a consistent keypoint matrix [T, K, (x,y,conf)] (coords normalized to [0,1])
 - Root-center (hip midpoint), rotate to make shoulders horizontal, scale by torso length
 - Compute joint angles for common joints and angular velocities
 - Smooth angles with Savitzky-Golay (scipy) or EMA fallback
 - Save outputs: normalized poses (.npy), angles (.npy), and a Parquet summary (requires pandas + pyarrow)
 - Creates one PNG plot: angle vs time for chosen joint

Dependencies:
 pip install numpy pandas pyarrow matplotlib scipy
 (scipy optional — fallback EMA used if missing)
"""

import os
import json
import glob
import argparse
from pathlib import Path
import numpy as np
import math
import matplotlib.pyplot as plt

# Optional imports
try:
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False

# --- Configurable joint names expected in JSON --- #
# We use the BlazePose mapping used in extract_pose.py
JOINT_ORDER = [
    "nose",
    "left_eye_inner","left_eye","left_eye_outer",
    "right_eye_inner","right_eye","right_eye_outer",
    "left_ear","right_ear",
    "left_shoulder","right_shoulder",
    "left_elbow","right_elbow",
    "left_wrist","right_wrist",
    "left_hip","right_hip",
    "left_knee","right_knee",
    "left_ankle","right_ankle"
]

# Joints for which to compute angles (triplets: (a, b, c) angle at b)
ANGLE_TRIPLETS = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_shoulder_angle": ("left_hip", "left_shoulder", "left_elbow"),  # torso-shoulder-elbow
    "right_shoulder_angle": ("right_hip", "right_shoulder", "right_elbow"),
    "hip_angle_left": ("left_shoulder","left_hip","left_knee"),
    "hip_angle_right": ("right_shoulder","right_hip","right_knee")
}

# ---------------------------
# Helpers
# ---------------------------
def load_pose_jsons(indir: str):
    """Loads JSON files sorted by filename and returns list of dicts."""
    files = sorted(glob.glob(os.path.join(indir, "frame_*.json")))
    if not files:
        raise RuntimeError(f"No frame_*.json found in {indir}")
    frames = []
    for p in files:
        with open(p, 'r') as f:
            frames.append(json.load(f))
    return frames

def build_keypoint_matrix(frames, joint_order=JOINT_ORDER):
    """
    Build arrays:
      - pts: shape (T, K, 2) with pixel coords
      - conf: shape (T, K)
      - sizes: store per-frame width/height if present (we assume original extractor kept pixel coords)
    If coordinates are None, fill with np.nan in pts and 0 in conf.
    """
    T = len(frames)
    K = len(joint_order)
    # try to infer frame size from the largest x,y seen
    max_w = 0
    max_h = 0
    for fr in frames:
        for j in fr['joints']:
            if j['x'] is not None and j['y'] is not None:
                max_w = max(max_w, j['x'])
                max_h = max(max_h, j['y'])
    # fallback to 1 to avoid division by zero
    max_w = max(1, max_w)
    max_h = max(1, max_h)

    pts = np.full((T, K, 2), np.nan, dtype=np.float32)
    conf = np.zeros((T, K), dtype=np.float32)
    timestamps = np.zeros(T, dtype=np.float32)

    name_to_idx = {n:i for i,n in enumerate(joint_order)}
    for t, fr in enumerate(frames):
        timestamps[t] = fr.get('timestamp', t)
        for j in fr['joints']:
            name = j.get('name')
            if name in name_to_idx:
                i = name_to_idx[name]
                x = j.get('x')
                y = j.get('y')
                c = j.get('conf', 0.0) or 0.0
                if x is None or y is None:
                    pts[t,i,0] = np.nan
                    pts[t,i,1] = np.nan
                    conf[t,i] = 0.0
                else:
                    pts[t,i,0] = float(x)
                    pts[t,i,1] = float(y)
                    conf[t,i] = float(c)
    return pts, conf, timestamps, max_w, max_h

def fill_missing_with_interpolation(pts, conf):
    """Linear interpolate missing coordinates per keypoint across time where possible."""
    T, K, _ = pts.shape
    pts_f = pts.copy()
    for k in range(K):
        for dim in range(2):
            arr = pts[:, k, dim]
            nans = np.isnan(arr)
            if np.all(nans):
                continue
            # linear interpolate
            idx = np.arange(T)
            good = ~nans
            pts_f[nans, k, dim] = np.interp(idx[nans], idx[good], arr[good])
    # for conf, fill zeros where interpolation filled from neighbors with small value (0.2)
    conf_f = conf.copy()
    conf_f[conf_f == 0] = 0.2
    return pts_f, conf_f

def normalize_coords(pts, max_w, max_h):
    """Convert absolute pixels to [0,1] normalized coords using provided frame extents."""
    pts_n = pts.copy()
    pts_n[...,0] = pts[...,0] / float(max_w)
    pts_n[...,1] = pts[...,1] / float(max_h)
    return pts_n

def compute_midpoint(a, b):
    return ( (a[0]+b[0])/2.0, (a[1]+b[1])/2.0 )

def rotate_points(points, angle_rad):
    """Rotate Nx2 points by angle around origin (counterclockwise)."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    R = np.array([[c, -s],[s, c]], dtype=np.float32)
    return (points @ R.T)

def procrustes_normalize(pts_n):
    """
    For each frame:
      - compute mid-shoulder and mid-hip
      - translate so mid-hip is at origin
      - compute torso length = distance(mid-shoulder, mid-hip)
      - rotate so shoulders are horizontal (angle between shoulders becomes 0)
      - scale so torso_length == 1 (if torso_length==0, skip scaling)
    pts_n: (T, K, 2)
    Returns normalized pts (T,K,2) and scales & angles used.
    """
    T, K, _ = pts_n.shape
    pts_out = np.zeros_like(pts_n)
    scales = np.zeros(T, dtype=np.float32)
    angles = np.zeros(T, dtype=np.float32)
    # indices
    idx = {name:i for i,name in enumerate(JOINT_ORDER)}
    for t in range(T):
        frame = pts_n[t].copy()
        # mid shoulders and mid hips
        ls = frame[idx['left_shoulder']]
        rs = frame[idx['right_shoulder']]
        lh = frame[idx['left_hip']]
        rh = frame[idx['right_hip']]
        mid_should = np.array([(ls[0]+rs[0])/2.0, (ls[1]+rs[1])/2.0], dtype=np.float32)
        mid_hip = np.array([(lh[0]+rh[0])/2.0, (lh[1]+rh[1])/2.0], dtype=np.float32)
        # translate
        frame_t = frame - mid_hip[None,:]
        # torso length
        torso_len = np.linalg.norm(mid_should - mid_hip)
        if torso_len <= 1e-6:
            scales[t] = 1.0
            angles[t] = 0.0
            pts_out[t] = frame_t
            continue
        # rotation angle to make shoulders horizontal:
        # vector from right_shoulder -> left_shoulder
        vec = ls - rs
        angle = math.atan2(vec[1], vec[0])  # angle of shoulder line
        # we want to rotate by -angle so it's horizontal (y=0)
        frame_r = rotate_points(frame_t, -angle)
        # scale to make torso_len = 1
        scale = 1.0 / torso_len
        frame_rs = frame_r * scale
        pts_out[t] = frame_rs
        scales[t] = scale
        angles[t] = -angle
    return pts_out, scales, angles

def vector_angle(a, b, c):
    """Angle at b between vectors ba and bc in degrees. a,b,c are 2D points."""
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    # handle zero-length
    na = np.linalg.norm(ba)
    nb = np.linalg.norm(bc)
    if na < 1e-8 or nb < 1e-8:
        return np.nan
    cosv = np.dot(ba, bc) / (na*nb)
    cosv = np.clip(cosv, -1.0, 1.0)
    ang = math.degrees(math.acos(cosv))
    return ang

def compute_angles_for_frames(pts_norm, conf, angle_triplets=ANGLE_TRIPLETS):
    """Compute angles over time. Returns dict of angle_name -> array (T,)"""
    T = pts_norm.shape[0]
    angles = {}
    idx = {name:i for i,name in enumerate(JOINT_ORDER)}
    for name, (a,b,c) in angle_triplets.items():
        arr = np.full(T, np.nan, dtype=np.float32)
        for t in range(T):
            pa = pts_norm[t, idx[a]]
            pb = pts_norm[t, idx[b]]
            pc = pts_norm[t, idx[c]]
            # if any point has nan, result is nan
            if np.any(np.isnan(pa)) or np.any(np.isnan(pb)) or np.any(np.isnan(pc)):
                arr[t] = np.nan
            else:
                arr[t] = vector_angle(pa, pb, pc)
        angles[name] = arr
    return angles

def smooth_signal(arr, window=9, poly=3):
    """Smooth 1D array using savgol if available, else EMA."""
    if SCIPY_AVAILABLE and len(arr) >= window:
        # need to fill nans first (interpolate)
        x = arr.copy()
        nans = np.isnan(x)
        if np.all(nans):
            return x
        idx = np.arange(len(x))
        good = ~nans
        x[nans] = np.interp(idx[nans], idx[good], x[good])
        # ensure odd window
        if window % 2 == 0:
            window += 1
        return savgol_filter(x, window_length=window, polyorder=min(poly, window-1))
    else:
        # EMA fallback
        x = arr.copy()
        out = np.full_like(x, np.nan)
        alpha = 0.2
        last = None
        for i, val in enumerate(x):
            if np.isnan(val):
                if last is None:
                    out[i] = np.nan
                else:
                    out[i] = last  # hold last
            else:
                if last is None:
                    last = val
                else:
                    last = alpha*val + (1-alpha)*last
                out[i] = last
        return out

# ---------------------------
# Main pipeline
# ---------------------------
def main(args):
    indir = args.indir
    outdir = args.outdir
    ensure = Path(outdir)
    ensure.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Loading JSON frames from {indir} ...")
    frames = load_pose_jsons(indir)
    pts, conf, timestamps, max_w, max_h = build_keypoint_matrix(frames)
    print(f"[INFO] Loaded {pts.shape[0]} frames, {pts.shape[1]} keypoints. Inferred extents: w={max_w}, h={max_h}")

    pts_filled, conf_filled = fill_missing_with_interpolation(pts, conf)
    pts_norm = normalize_coords(pts_filled, max_w, max_h)
    pts_centered, scales, angles_used = procrustes_normalize(pts_norm)

    # compute joint angles
    raw_angles = compute_angles_for_frames(pts_centered, conf_filled)
    # smooth each angle series
    smooth_angles = {}
    for k,v in raw_angles.items():
        smooth_angles[k] = smooth_signal(v, window=args.smooth_window, poly=args.smooth_poly)

    # compute angular velocities (deg/sec) using timestamps
    ang_vel = {}
    dt = np.diff(timestamps, prepend=timestamps[0])
    dt[dt==0] = 1e-3
    for k,v in smooth_angles.items():
        vel = np.gradient(v, dt)
        ang_vel[k] = vel

    # Save arrays
    np.save(os.path.join(outdir, "poses_normalized.npy"), pts_centered)
    np.save(os.path.join(outdir, "scales.npy"), scales)
    np.save(os.path.join(outdir, "angles_raw.npy"), raw_angles)   # note: dict saved as object array
    np.save(os.path.join(outdir, "angles_smooth.npy"), smooth_angles)
    np.save(os.path.join(outdir, "angles_vel.npy"), ang_vel)
    np.save(os.path.join(outdir, "timestamps.npy"), timestamps)
    print(f"[INFO] Saved .npy outputs to {outdir}")

    # Save Parquet summary if pandas available
    if PANDAS_AVAILABLE:
        rows = []
        for t in range(pts_centered.shape[0]):
            row = {"frame_id": int(t), "timestamp": float(timestamps[t])}
            # add overall avg confidence
            row['avg_conf'] = float(np.nanmean(conf_filled[t]))
            # add some angle values
            for k in smooth_angles:
                row[f"angle_{k}"] = float(smooth_angles[k][t]) if not np.isnan(smooth_angles[k][t]) else None
            rows.append(row)
        df = pd.DataFrame(rows)
        df.to_parquet(os.path.join(outdir, "summary.parquet"), index=False)
        print(f"[INFO] Wrote summary.parquet ({df.shape[0]} rows).")
    else:
        print("[WARN] pandas not available: skipping Parquet summary. Install pandas + pyarrow to enable.")

    # Plot requested joint
    joint = args.plot_joint
    if joint:
        if joint not in smooth_angles:
            print(f"[WARN] Joint '{joint}' not found in angle list. Available: {list(smooth_angles.keys())}")
        else:
            y = smooth_angles[joint]
            plt.figure(figsize=(8,3))
            plt.plot(timestamps, y)
            plt.title(f"Joint angle over time: {joint}")
            plt.xlabel("time (s)")
            plt.ylabel("angle (deg)")
            plt.grid(True)
            outpng = os.path.join(outdir, f"angle_{joint}.png")
            plt.tight_layout()
            plt.savefig(outpng)
            plt.close()
            print(f"[INFO] Saved plot to {outpng}")

    print("[DONE] Preprocessing complete.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True, help="Directory with frame_*.json files (from extract_pose.py)")
    ap.add_argument("--outdir", required=True, help="Output directory for normalized data")
    ap.add_argument("--smooth-window", type=int, default=9, help="Savgol window (odd) or used length for smoothing fallback")
    ap.add_argument("--smooth-poly", type=int, default=3, help="Savgol poly order")
    ap.add_argument("--plot-joint", type=str, default="left_elbow", help="Which angle to plot")
    args = ap.parse_args()
    main(args)
