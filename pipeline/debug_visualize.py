"""
Pipeline Debug Visualizer

Generates diagnostic videos at each pipeline stage to identify
where things go wrong:

  1. 2D pose overlays on each view (front, left, right) side-by-side
  2. 3D skeleton wireframe from 3 camera angles
  3. Per-joint confidence heatmap

Usage:
    python pipeline/debug_visualize.py --technique Bonus --player Player-1

Output:
    outputs/<technique>_<player>/debug/
        debug_2d_all_views.mp4     — 2D poses on all 3 views
        debug_3d_skeleton.mp4      — 3D skeleton from 3 angles
        debug_per_frame_stats.txt  — per-frame joint counts
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

# Ensure project root is on path (so `from pipeline.xxx` works when run directly)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("debug_viz")

# COCO-17 skeleton connections
SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),        # head
    (5, 6),                                   # shoulders
    (5, 7), (7, 9),                           # left arm
    (6, 8), (8, 10),                          # right arm
    (5, 11), (6, 12),                         # torso
    (11, 12),                                 # hips
    (11, 13), (13, 15),                       # left leg
    (12, 14), (14, 16),                       # right leg
]

JOINT_NAMES = [
    "nose", "L_eye", "R_eye", "L_ear", "R_ear",
    "L_sho", "R_sho", "L_elb", "R_elb",
    "L_wri", "R_wri", "L_hip", "R_hip",
    "L_kne", "R_kne", "L_ank", "R_ank",
]

COLORS = {
    "front": (0, 255, 0),    # green
    "left":  (255, 165, 0),  # orange
    "right": (0, 165, 255),  # blue
}


def draw_skeleton_2d(frame, keypoints, confidence, color=(0, 255, 0), conf_thresh=0.3):
    """Draw 2D skeleton on a frame."""
    overlay = frame.copy()

    # Draw bones
    for j1, j2 in SKELETON:
        if (confidence[j1] >= conf_thresh and confidence[j2] >= conf_thresh
                and not np.isnan(keypoints[j1, 0]) and not np.isnan(keypoints[j2, 0])):
            pt1 = (int(keypoints[j1, 0]), int(keypoints[j1, 1]))
            pt2 = (int(keypoints[j2, 0]), int(keypoints[j2, 1]))
            cv2.line(overlay, pt1, pt2, color, 2)

    # Draw joints
    for j in range(17):
        if confidence[j] >= conf_thresh and not np.isnan(keypoints[j, 0]):
            pt = (int(keypoints[j, 0]), int(keypoints[j, 1]))
            # Color by confidence: red=low, green=high
            r = int(255 * (1 - confidence[j]))
            g = int(255 * confidence[j])
            cv2.circle(overlay, pt, 4, (0, g, r), -1)
            # Label
            cv2.putText(overlay, f"{confidence[j]:.1f}", (pt[0]+5, pt[1]-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    return overlay


def generate_2d_debug_video(technique, player, output_dir, debug_frames=50):
    """
    Stage 1: Load videos, extract 2D poses, render overlay on all 3 views side-by-side.
    """
    project_root = Path(__file__).resolve().parent.parent
    cfg_path = Path(__file__).resolve().parent / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    samples_dir = project_root / cfg["paths"]["samples_root"]
    prefix_map = {"Bonus": "bonus", "HandTouch": "hand"}
    prefix = prefix_map.get(technique, technique.lower())

    technique_dir = samples_dir / technique / player

    logger.info("=" * 60)
    logger.info("STAGE 1: 2D Pose Extraction Debug")
    logger.info("=" * 60)

    # Load videos
    from pipeline.data_loader.video_loader import load_multiview_videos
    frames = load_multiview_videos(
        str(technique_dir / f"{prefix}_front.mp4"),
        str(technique_dir / f"{prefix}_left.mp4"),
        str(technique_dir / f"{prefix}_right.mp4"),
        debug_output_dir=str(output_dir),
    )

    # Trim to debug_frames
    for view in frames:
        if debug_frames and len(frames[view]) > debug_frames:
            frames[view] = frames[view][:debug_frames]

    T = len(frames["front"])
    logger.info(f"Using {T} frames per view")

    # Extract 2D poses
    from pipeline.pose_extraction.mediapipe_pose import extract_2d_poses

    pose_cfg = cfg["pose_extraction"]
    all_poses = {}
    all_confs = {}

    for view_name in ["front", "left", "right"]:
        logger.info(f"Extracting 2D poses for [{view_name}]...")
        poses, confs = extract_2d_poses(
            frames[view_name],
            view_name=view_name,
            model_complexity=pose_cfg["model_complexity"],
            min_detection_confidence=pose_cfg["min_detection_confidence"],
            min_tracking_confidence=pose_cfg["min_tracking_confidence"],
        )
        all_poses[view_name] = poses
        all_confs[view_name] = confs

        # Per-view stats
        nan_pct = 100 * np.sum(np.isnan(poses[:, :, 0])) / (T * 17)
        avg_conf = np.nanmean(confs)
        logger.info(f"  [{view_name}] NaN: {nan_pct:.1f}%, avg conf: {avg_conf:.3f}")

    # Save per-view pose files
    for view_name in all_poses:
        np.save(str(output_dir / f"pose_2d_{view_name}.npy"), all_poses[view_name])
        np.save(str(output_dir / f"confidence_{view_name}.npy"), all_confs[view_name])

    # === Render side-by-side debug video ===
    logger.info("Rendering 2D debug video (3 views side-by-side)...")

    # Get frame dimensions
    H, W = frames["front"].shape[1], frames["front"].shape[2]
    # Target width per panel
    panel_w = 640
    scale = panel_w / W
    panel_h = int(H * scale)

    canvas_w = panel_w * 3
    canvas_h = panel_h + 60  # extra space for text

    video_path = str(output_dir / "debug_2d_all_views.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, 15.0, (canvas_w, canvas_h))

    stats_lines = []

    for t in range(T):
        canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        for vi, view_name in enumerate(["front", "left", "right"]):
            frame = frames[view_name][t].copy()

            # Draw skeleton
            frame = draw_skeleton_2d(
                frame,
                all_poses[view_name][t],
                all_confs[view_name][t],
                color=COLORS[view_name],
            )

            # Resize
            frame_resized = cv2.resize(frame, (panel_w, panel_h))

            # Count detected joints
            detected = int(np.sum(~np.isnan(all_poses[view_name][t, :, 0])))

            # Add label
            cv2.putText(frame_resized, f"{view_name.upper()} ({detected}/17 joints)",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        COLORS[view_name], 2)

            canvas[:panel_h, vi * panel_w:(vi + 1) * panel_w] = frame_resized

        # Bottom bar with frame info
        total_detected = sum(
            int(np.sum(~np.isnan(all_poses[v][t, :, 0]))) for v in all_poses
        )
        info_text = f"Frame {t+1}/{T} | Total joints: {total_detected}/51"
        cv2.putText(canvas, info_text, (10, canvas_h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        writer.write(canvas)

        stats_lines.append(f"Frame {t+1}: " + ", ".join(
            f"{v}={int(np.sum(~np.isnan(all_poses[v][t, :, 0])))}/17"
            for v in all_poses
        ))

    writer.release()
    logger.info(f"Saved: {video_path}")

    # Save per-frame stats
    stats_path = str(output_dir / "debug_per_frame_stats.txt")
    with open(stats_path, "w") as f:
        f.write("\n".join(stats_lines))
    logger.info(f"Saved: {stats_path}")

    return frames, all_poses, all_confs


def generate_3d_debug_video(all_poses, all_confs, output_dir):
    """
    Stage 2: Triangulate and render 3D skeleton from 3 camera angles.
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("STAGE 2: 3D Triangulation Debug")
    logger.info("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    cfg_path = Path(__file__).resolve().parent / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    # Synchronize
    from pipeline.synchronization.sync import synchronize_views
    sync_cfg = cfg["synchronization"]
    synced_poses, synced_confs, sync_info = synchronize_views(
        all_poses, all_confs,
        pelvis_weight=sync_cfg["pelvis_weight"],
        wrist_weight=sync_cfg["wrist_weight"],
        ankle_weight=sync_cfg["ankle_weight"],
        correlation_threshold=sync_cfg["correlation_threshold"],
        max_offset_frames=sync_cfg["max_offset_frames"],
        debug_output_dir=str(output_dir),
    )
    logger.info(f"Sync offsets: {sync_info['offsets']}")
    logger.info(f"Sync correlations: {sync_info['correlation_scores']}")

    # Load camera params
    from pipeline.calibration.calibrate import load_camera_params, generate_default_params, save_camera_params
    calib_path = project_root / cfg["paths"]["calibration_file"]
    if calib_path.is_file():
        camera_params = load_camera_params(str(calib_path))
    else:
        camera_params = generate_default_params()
        save_camera_params(camera_params, str(calib_path))

    # Triangulate
    from pipeline.triangulation.triangulate import triangulate_poses
    tri_cfg = cfg["triangulation"]
    poses_3d_raw, tri_stats = triangulate_poses(
        synced_poses, synced_confs, camera_params,
        confidence_threshold=tri_cfg["confidence_threshold"],
        max_reprojection_error=tri_cfg["max_reprojection_error"],
    )

    logger.info(f"Triangulation: {tri_stats['success_pct']}% success")
    np.save(str(output_dir / "pose_3d_raw_debug.npy"), poses_3d_raw)

    # Smooth
    from pipeline.postprocess.smoothing import smooth_poses
    sm_cfg = cfg["smoothing"]
    poses_3d_smooth = smooth_poses(
        poses_3d_raw,
        method=sm_cfg["method"],
        window_length=sm_cfg["window_length"],
        polyorder=sm_cfg["polyorder"],
    )

    # Normalize
    from pipeline.postprocess.normalization import normalize_poses
    norm_cfg = cfg["normalization"]
    poses_3d_clean = normalize_poses(poses_3d_smooth, target_height=norm_cfg["target_height"])

    np.save(str(output_dir / "pose_3d_clean_debug.npy"), poses_3d_clean)

    # === Render 3D skeleton video ===
    logger.info("Rendering 3D skeleton debug video...")
    T = poses_3d_clean.shape[0]

    canvas_w, canvas_h = 1280, 480
    panel_w = canvas_w // 3

    video_path = str(output_dir / "debug_3d_skeleton.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, 15.0, (canvas_w, canvas_h))

    # Camera view angles for 3D rendering
    view_angles = [
        ("Front", 0),
        ("Side", 90),
        ("Top-Down", None),  # special: XZ plane
    ]

    for t in range(T):
        canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
        joints = poses_3d_clean[t]  # (17, 3)

        for vi, (view_label, angle) in enumerate(view_angles):
            panel = np.zeros((canvas_h, panel_w, 3), dtype=np.uint8)

            # Project 3D to 2D for this viewing angle
            if angle is not None:
                # Rotate around Y axis
                rad = np.radians(angle)
                cos_a, sin_a = np.cos(rad), np.sin(rad)
                proj_x = joints[:, 0] * cos_a + joints[:, 2] * sin_a
                proj_y = -joints[:, 1]  # flip Y for screen coords
            else:
                # Top-down: XZ plane
                proj_x = joints[:, 0]
                proj_y = joints[:, 2]

            # Scale to panel
            valid = ~np.isnan(proj_x)
            if np.sum(valid) > 2:
                x_min, x_max = np.nanmin(proj_x), np.nanmax(proj_x)
                y_min, y_max = np.nanmin(proj_y), np.nanmax(proj_y)
                x_range = max(x_max - x_min, 0.01)
                y_range = max(y_max - y_min, 0.01)
                scale = min((panel_w - 80) / x_range, (canvas_h - 80) / y_range)

                cx = panel_w // 2
                cy = canvas_h // 2
                x_center = (x_min + x_max) / 2
                y_center = (y_min + y_max) / 2

                px = ((proj_x - x_center) * scale + cx).astype(int)
                py = ((proj_y - y_center) * scale + cy).astype(int)

                # Draw bones
                for j1, j2 in SKELETON:
                    if valid[j1] and valid[j2]:
                        cv2.line(panel, (px[j1], py[j1]), (px[j2], py[j2]),
                                 (0, 200, 0), 2)

                # Draw joints
                for j in range(17):
                    if valid[j]:
                        nan_raw = np.isnan(poses_3d_raw[t, j, 0])
                        color = (0, 0, 255) if nan_raw else (0, 255, 0)
                        cv2.circle(panel, (px[j], py[j]), 5, color, -1)
                        cv2.putText(panel, JOINT_NAMES[j], (px[j]+6, py[j]-4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)

            # Label
            cv2.putText(panel, view_label, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Joint count
            detected_raw = int(np.sum(~np.isnan(poses_3d_raw[t, :, 0])))
            cv2.putText(panel, f"Raw: {detected_raw}/17 joints", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 200), 1)

            canvas[:, vi * panel_w:(vi + 1) * panel_w] = panel

        # Bottom info
        detected_raw = int(np.sum(~np.isnan(poses_3d_raw[t, :, 0])))
        info = f"Frame {t+1}/{T} | Triangulated: {detected_raw}/17 | Green=real, Red=interpolated"
        cv2.putText(canvas, info, (10, canvas_h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        writer.write(canvas)

    writer.release()
    logger.info(f"Saved: {video_path}")

    # === Print diagnostic summary ===
    logger.info("")
    logger.info("=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)

    # Per-joint triangulation success
    logger.info("Per-joint triangulation success rate:")
    for j in range(17):
        success = np.sum(~np.isnan(poses_3d_raw[:, j, 0]))
        pct = 100 * success / T
        bar = "#" * int(pct // 5) + "." * (20 - int(pct // 5))
        logger.info(f"  {JOINT_NAMES[j]:>6s}: [{bar}] {pct:5.1f}% ({success}/{T})")

    # Value range check
    logger.info(f"\n3D coordinate ranges (clean):")
    for axis, label in enumerate(["X", "Y", "Z"]):
        vals = poses_3d_clean[:, :, axis]
        logger.info(f"  {label}: min={np.nanmin(vals):.4f}, max={np.nanmax(vals):.4f}")

    # Save summary
    summary = {
        "triangulation_success_pct": tri_stats["success_pct"],
        "sync_offsets": sync_info["offsets"],
        "sync_correlations": sync_info["correlation_scores"],
        "per_joint_success": {
            JOINT_NAMES[j]: round(100 * float(np.sum(~np.isnan(poses_3d_raw[:, j, 0]))) / T, 1)
            for j in range(17)
        },
        "coordinate_ranges": {
            ax: {"min": round(float(np.nanmin(poses_3d_clean[:, :, i])), 4),
                 "max": round(float(np.nanmax(poses_3d_clean[:, :, i])), 4)}
            for i, ax in enumerate(["X", "Y", "Z"])
        },
    }
    with open(str(output_dir / "debug_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return poses_3d_clean, tri_stats


def main():
    parser = argparse.ArgumentParser(description="Pipeline Debug Visualizer")
    parser.add_argument("--technique", required=True, choices=["Bonus", "HandTouch"])
    parser.add_argument("--player", required=True)
    parser.add_argument("--debug-frames", type=int, default=50)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "outputs" / f"{args.technique}_{args.player}" / "debug"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output: {output_dir}")

    # Stage 1: 2D debug
    frames, all_poses, all_confs = generate_2d_debug_video(
        args.technique, args.player, output_dir, args.debug_frames
    )

    # Stage 2: 3D debug
    poses_3d, tri_stats = generate_3d_debug_video(
        all_poses, all_confs, output_dir
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("DEBUG VIDEOS GENERATED:")
    logger.info(f"  1. {output_dir / 'debug_2d_all_views.mp4'}")
    logger.info(f"  2. {output_dir / 'debug_3d_skeleton.mp4'}")
    logger.info(f"  3. {output_dir / 'debug_summary.json'}")
    logger.info(f"  4. {output_dir / 'debug_per_frame_stats.txt'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
