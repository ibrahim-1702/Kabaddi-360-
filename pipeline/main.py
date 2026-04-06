"""
Multi-View 3D Reconstruction Pipeline — Main Orchestrator

Runs all pipeline stages sequentially with validation at each step.

Usage:
    python -m pipeline.main --technique Bonus --player Player-1
    python -m pipeline.main --technique Bonus --player Player-1 --debug-frames 50
    python -m pipeline.main --technique HandTouch --player Player-2 --output-dir outputs/ht2
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import yaml

# ── Setup logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def load_config(config_path: str) -> dict:
    """Load pipeline configuration from YAML."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_pipeline(args):
    """Execute the full multi-view 3D reconstruction pipeline."""

    start_time = time.time()

    # ── Resolve paths ──────────────────────────────────────────────────────
    project_root = Path(__file__).resolve().parent.parent
    config_path = Path(__file__).resolve().parent / "config.yaml"

    cfg = load_config(str(config_path))

    samples_dir = project_root / cfg["paths"]["samples_root"]
    technique_dir = samples_dir / args.technique / args.player

    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / cfg["paths"]["output_root"] / f"{args.technique}_{args.player}"
    )
    debug_dir = output_dir / "debug"
    pose_2d_dir = output_dir / "pose_2d"
    pose_3d_dir = output_dir / "pose_3d"
    anim_dir = output_dir / "animations"

    for d in [output_dir, debug_dir, pose_2d_dir, pose_3d_dir, anim_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Determine video filename prefix
    prefix_map = {
        "Bonus": "bonus",
        "HandTouch": "hand",
    }
    prefix = prefix_map.get(args.technique, args.technique.lower())

    front_video = technique_dir / f"{prefix}_front.mp4"
    left_video = technique_dir / f"{prefix}_left.mp4"
    right_video = technique_dir / f"{prefix}_right.mp4"

    logger.info("=" * 70)
    logger.info("MULTI-VIEW 3D RECONSTRUCTION PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Technique : {args.technique}")
    logger.info(f"Player    : {args.player}")
    logger.info(f"Output    : {output_dir}")
    logger.info(f"Front     : {front_video}")
    logger.info(f"Left      : {left_video}")
    logger.info(f"Right     : {right_video}")
    logger.info("=" * 70)

    # Validate input files exist
    for vp in [front_video, left_video, right_video]:
        if not vp.is_file():
            logger.error(f"Video not found: {vp}")
            sys.exit(1)

    # ======================================================================
    # STEP 1: VIDEO LOADING
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 1: Video Loading")
    logger.info("━" * 50)

    from pipeline.data_loader.video_loader import load_multiview_videos

    frames = load_multiview_videos(
        str(front_video),
        str(left_video),
        str(right_video),
        fps_tolerance=cfg["video_loader"]["fps_tolerance"],
        duration_tolerance=cfg["video_loader"]["duration_tolerance"],
        debug_output_dir=str(debug_dir),
    )

    for view, f_arr in frames.items():
        logger.info(f"  [{view}] frames shape: {f_arr.shape}")

    logger.info("✓ Step 1 complete")

    # ======================================================================
    # STEP 2: 2D POSE EXTRACTION
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 2: 2D Pose Extraction (MediaPipe)")
    logger.info("━" * 50)

    from pipeline.pose_extraction.mediapipe_pose import (
        extract_2d_poses,
        save_debug_overlay_video,
    )

    pose_cfg = cfg["pose_extraction"]
    debug_frames = args.debug_frames or pose_cfg.get("debug_frames", None)

    poses_2d = {}
    confs_2d = {}

    for view_name in ["front", "left", "right"]:
        view_frames = frames[view_name]

        # Debug mode: extract only first N frames
        if debug_frames and debug_frames < len(view_frames):
            logger.info(f"[{view_name}] Debug mode: using first {debug_frames} frames")
            view_frames_extract = view_frames[:debug_frames]
        else:
            view_frames_extract = view_frames

        poses, confs = extract_2d_poses(
            view_frames_extract,
            view_name=view_name,
            model_complexity=pose_cfg["model_complexity"],
            min_detection_confidence=pose_cfg["min_detection_confidence"],
            min_tracking_confidence=pose_cfg["min_tracking_confidence"],
        )

        poses_2d[view_name] = poses
        confs_2d[view_name] = confs

        # Save 2D poses
        np.save(str(pose_2d_dir / f"pose_2d_{view_name}.npy"), poses)
        np.save(str(pose_2d_dir / f"confidence_{view_name}.npy"), confs)

        logger.info(f"  [{view_name}] pose shape: {poses.shape}")

        # Save debug overlay for front view
        if view_name == "front":
            save_debug_overlay_video(
                view_frames_extract, poses, confs,
                str(debug_dir / "pose_overlay_front.mp4"),
            )

    # Validate shapes
    for view_name, p in poses_2d.items():
        assert p.shape[1] == 17 and p.shape[2] == 2, (
            f"Invalid pose shape for {view_name}: {p.shape}"
        )

    logger.info("✓ Step 2 complete")

    # Release video frames to save memory
    del frames
    logger.info("  (freed video frame memory)")

    # ======================================================================
    # STEP 3: TEMPORAL SYNCHRONIZATION
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 3: Temporal Synchronization")
    logger.info("━" * 50)

    from pipeline.synchronization.sync import synchronize_views

    sync_cfg = cfg["synchronization"]

    synced_poses, synced_confs, sync_info = synchronize_views(
        poses_2d,
        confs_2d,
        pelvis_weight=sync_cfg["pelvis_weight"],
        wrist_weight=sync_cfg["wrist_weight"],
        ankle_weight=sync_cfg["ankle_weight"],
        correlation_threshold=sync_cfg["correlation_threshold"],
        max_offset_frames=sync_cfg["max_offset_frames"],
        debug_output_dir=str(debug_dir),
    )

    logger.info(f"  Offsets: {sync_info['offsets']}")
    logger.info(f"  Correlations: {sync_info['correlation_scores']}")
    logger.info(f"  Aligned frames: {sync_info['aligned_frame_count']}")
    logger.info("✓ Step 3 complete")

    # ======================================================================
    # STEP 4: CAMERA CALIBRATION CHECK
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 4: Camera Parameters")
    logger.info("━" * 50)

    from pipeline.calibration.calibrate import (
        load_camera_params,
        generate_default_params,
        save_camera_params,
    )

    calib_path = project_root / cfg["paths"]["calibration_file"]

    if calib_path.is_file():
        camera_params = load_camera_params(str(calib_path))
    else:
        logger.warning(
            "No camera_params.json found — generating SYNTHETIC defaults. "
            "Results will be approximate."
        )
        # Get resolution from first view
        sample_view = next(iter(synced_poses.values()))
        # We don't have frames anymore, use info from debug
        info_path = debug_dir / "video_info.json"
        if info_path.is_file():
            with open(info_path) as f:
                vinfo = json.load(f)
            w = vinfo["front"]["width"]
            h = vinfo["front"]["height"]
        else:
            w, h = 1920, 1080

        camera_params = generate_default_params(w, h)
        save_camera_params(camera_params, str(calib_path))

    is_default = camera_params.get("is_default", False)
    if is_default:
        logger.warning("⚠ USING SYNTHETIC CALIBRATION — 3D results may be distorted")
    else:
        logger.info("Using calibrated camera parameters")

    logger.info("✓ Step 4 complete")

    # ======================================================================
    # STEP 5: 3D TRIANGULATION
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 5: 3D Triangulation")
    logger.info("━" * 50)

    from pipeline.triangulation.triangulate import triangulate_poses

    tri_cfg = cfg["triangulation"]

    poses_3d_raw, tri_stats = triangulate_poses(
        synced_poses,
        synced_confs,
        camera_params,
        confidence_threshold=tri_cfg["confidence_threshold"],
        max_reprojection_error=tri_cfg["max_reprojection_error"],
    )

    np.save(str(pose_3d_dir / "pose_3d_raw.npy"), poses_3d_raw)
    logger.info(f"  Raw 3D shape: {poses_3d_raw.shape}")
    logger.info(f"  Success rate: {tri_stats['success_pct']}%")

    # Save triangulation stats
    with open(str(debug_dir / "triangulation_stats.json"), "w") as f:
        json.dump(tri_stats, f, indent=2)

    logger.info("✓ Step 5 complete")

    # ======================================================================
    # STEP 6: 3D SMOOTHING
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 6: 3D Pose Smoothing")
    logger.info("━" * 50)

    from pipeline.postprocess.smoothing import smooth_poses

    sm_cfg = cfg["smoothing"]

    poses_3d_smooth = smooth_poses(
        poses_3d_raw,
        method=sm_cfg["method"],
        window_length=sm_cfg["window_length"],
        polyorder=sm_cfg["polyorder"],
        ema_alpha=sm_cfg["ema_alpha"],
    )

    np.save(str(pose_3d_dir / "pose_3d_smooth.npy"), poses_3d_smooth)
    logger.info(f"  Smoothed 3D shape: {poses_3d_smooth.shape}")
    logger.info("✓ Step 6 complete")

    # ======================================================================
    # STEP 7: NORMALIZATION
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 7: Normalization & Scale")
    logger.info("━" * 50)

    from pipeline.postprocess.normalization import normalize_poses

    norm_cfg = cfg["normalization"]

    poses_3d_clean = normalize_poses(
        poses_3d_smooth,
        target_height=norm_cfg["target_height"],
    )

    np.save(str(pose_3d_dir / "pose_3d_clean.npy"), poses_3d_clean)
    logger.info(f"  Clean 3D shape: {poses_3d_clean.shape}")
    logger.info("✓ Step 7 complete")

    # ======================================================================
    # STEP 8: BVH EXPORT
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 8: BVH Animation Export")
    logger.info("━" * 50)

    from pipeline.animation.bvh_export import export_bvh

    anim_cfg = cfg["animation"]
    bvh_path = str(anim_dir / "animation.bvh")

    export_bvh(
        poses_3d_clean,
        fps=anim_cfg["fps"],
        output_path=bvh_path,
    )

    logger.info(f"  BVH file: {bvh_path}")
    logger.info("✓ Step 8 complete")

    # ======================================================================
    # STEP 9: BLENDER RETARGET (OPTIONAL)
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 9: Blender Retarget (Optional)")
    logger.info("━" * 50)

    from pipeline.animation.blender_retarget import (
        run_blender_retarget,
        check_blender_available,
        generate_unity_metadata,
    )

    fbx_path = str(anim_dir / "avatar_animation.fbx")
    blender_path = anim_cfg.get("blender_path", "blender")

    if check_blender_available(blender_path):
        success = run_blender_retarget(
            bvh_path, fbx_path, blender_path=blender_path
        )
        if success:
            logger.info(f"  FBX file: {fbx_path}")
        else:
            logger.warning("  Blender retarget failed — BVH is still available")
    else:
        logger.info("  Blender not available — skipping FBX export")
        logger.info("  BVH file can be imported into Blender manually")

    # Generate Unity metadata
    T = poses_3d_clean.shape[0]
    fps = anim_cfg["fps"]
    generate_unity_metadata(
        fps=fps,
        frame_count=T,
        duration=T / fps,
        output_path=str(anim_dir / "unity_metadata.json"),
    )

    logger.info("✓ Step 9 complete")

    # ======================================================================
    # STEP 10: FINAL VALIDATION & REPORT
    # ======================================================================
    logger.info("")
    logger.info("━" * 50)
    logger.info("STEP 10: Final Validation")
    logger.info("━" * 50)

    # Check files exist
    checks = {
        "pose_3d_clean.npy": (pose_3d_dir / "pose_3d_clean.npy").is_file(),
        "animation.bvh": Path(bvh_path).is_file(),
    }

    # Check motion continuity
    velocity = np.linalg.norm(np.diff(poses_3d_clean, axis=0), axis=2)
    max_vel = np.max(velocity)
    mean_vel = np.mean(velocity)
    teleport_frames = int(np.sum(velocity > 10 * mean_vel)) if mean_vel > 0 else 0

    checks["no_teleporting_joints"] = bool(teleport_frames == 0)

    # Compute missing joint percentage
    nan_mask = np.isnan(poses_3d_raw[:, :, 0])
    missing_pct = float(100.0 * np.sum(nan_mask) / nan_mask.size)

    elapsed = time.time() - start_time

    report = {
        "technique": args.technique,
        "player": args.player,
        "elapsed_seconds": round(elapsed, 2),
        "checks": checks,
        "sync_offsets": sync_info["offsets"],
        "correlation_scores": sync_info["correlation_scores"],
        "triangulation_success_pct": tri_stats["success_pct"],
        "missing_joint_pct_raw": round(missing_pct, 2),
        "pose_3d_shape": list(poses_3d_clean.shape),
        "motion_stats": {
            "mean_velocity": round(float(mean_vel), 6),
            "max_velocity": round(float(max_vel), 6),
            "teleport_frames": int(teleport_frames),
        },
        "output_files": {
            "pose_3d_raw": str(pose_3d_dir / "pose_3d_raw.npy"),
            "pose_3d_smooth": str(pose_3d_dir / "pose_3d_smooth.npy"),
            "pose_3d_clean": str(pose_3d_dir / "pose_3d_clean.npy"),
            "bvh": bvh_path,
            "unity_metadata": str(anim_dir / "unity_metadata.json"),
        },
    }

    report_path = str(debug_dir / "report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Also write plain text report
    txt_report = str(debug_dir / "report.txt")
    with open(txt_report, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("PIPELINE REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Technique:       {args.technique}\n")
        f.write(f"Player:          {args.player}\n")
        f.write(f"Elapsed:         {elapsed:.1f}s\n\n")
        f.write(f"Sync offsets:    {sync_info['offsets']}\n")
        f.write(f"Correlations:    {sync_info['correlation_scores']}\n\n")
        f.write(f"Triangulation:   {tri_stats['success_pct']}% success\n")
        f.write(f"Missing joints:  {missing_pct:.1f}% (raw)\n\n")
        f.write(f"3D pose shape:   {poses_3d_clean.shape}\n")
        f.write(f"Mean velocity:   {mean_vel:.6f}\n")
        f.write(f"Max velocity:    {max_vel:.6f}\n")
        f.write(f"Teleport frames: {teleport_frames}\n\n")
        f.write("Checks:\n")
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            f.write(f"  {status} {check_name}\n")
        f.write("\n" + "=" * 60 + "\n")

    # Print summary
    logger.info("")
    all_passed = all(checks.values())
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        logger.info(f"  {status} {check_name}")

    logger.info("")
    logger.info(f"Report saved: {report_path}")
    logger.info(f"Elapsed time: {elapsed:.1f}s")

    if all_passed:
        logger.info("")
        logger.info("=" * 70)
        logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
    else:
        logger.warning("")
        logger.warning("⚠ PIPELINE COMPLETED WITH WARNINGS — check report")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Multi-View 3D Reconstruction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--technique", required=True,
        choices=["Bonus", "HandTouch"],
        help="Kabaddi technique name",
    )
    parser.add_argument(
        "--player", required=True,
        help="Player directory name (e.g., Player-1)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Custom output directory (default: outputs/<technique>_<player>)",
    )
    parser.add_argument(
        "--debug-frames", type=int, default=None,
        help="Process only first N frames (debug mode)",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
