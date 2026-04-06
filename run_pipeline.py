#!/usr/bin/env python3
"""
AR-Based Kabaddi Ghost Trainer - End-to-End Pipeline

This script orchestrates the complete pipeline:
1. Pose extraction + Level-1 cleaning
2. Pose validation metrics
3. Feedback generation + TTS
4. AR visualization

Input Requirements:
    - Pre-extracted poses must be COCO-17 format (T, 17, 2)
    - MediaPipe (33 joints) poses will be converted automatically
    - Level-1 cleaning validates and enforces COCO-17 input strictly
    
Usage Examples:
    # Pre-extracted poses (fastest)
    python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --output results

    # Extract from video
    python run_pipeline.py --expert raider_pose_level1.npy --user-video masked_raider.mp4 --output results
    
    # Disable optional features
    python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --no-tts --no-viz --output results
    
    # Verbose logging
    python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --output results --verbose
"""

import os
import sys
import json
import argparse
import traceback
from pathlib import Path
from typing import Optional, Tuple, Dict

import numpy as np

# Import existing modules
from pipeline_config import PipelineConfig
from pipeline_logger import PipelineLogger


def validate_file_exists(filepath: str, logger: PipelineLogger) -> bool:
    """Validate that a file exists."""
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return False
    return True


def load_or_extract_pose(
    input_path: Optional[str],
    video_path: Optional[str],
    output_dir: str,
    config: PipelineConfig,
    logger: PipelineLogger,
    name: str
) -> Optional[np.ndarray]:
    """
    Load pose from .npy file or extract from video.
    
    Args:
        input_path: Path to .npy file (if already extracted)
        video_path: Path to video file (if needs extraction)
        output_dir: Output directory for intermediate files
        config: Pipeline configuration
        logger: Logger instance
        name: Name for this pose (e.g., 'user', 'expert')
    
    Returns:
        Pose array of shape (T, 17, 2) or None if failed
    """
    # Case 1: Pre-extracted pose
    if input_path:
        logger.log_input(f"{name.capitalize()} pose (pre-extracted)", input_path)
        
        if not validate_file_exists(input_path, logger):
            return None
        
        try:
            pose = np.load(input_path)
            logger.debug(f"Loaded {name} pose from {input_path}")
            logger.log_data_shape(f"{name} pose", pose.shape, "(T, 17, 2) or (T, 17, 3)")
            
            # Handle (T, 17, 3) case - extract only x,y
            if pose.ndim == 3 and pose.shape[1] == 17:
                if pose.shape[2] == 3:
                    logger.debug("Extracting x,y from (T, 17, 3) format")
                    pose = pose[:, :, :2]
                elif pose.shape[2] != 2:
                    logger.error(f"Invalid pose shape: {pose.shape}. Expected (T, 17, 2) or (T, 17, 3)")
                    return None
            else:
                logger.error(f"Invalid pose dimensions: {pose.shape}")
                return None
            
            logger.success(f"Loaded {name} pose: {pose.shape[0]} frames")
            return pose
            
        except Exception as e:
            logger.log_error_detailed(f"Load {name} pose", e, input_path)
            return None
    
    # Case 2: Extract from video
    elif video_path:
        logger.log_input(f"{name.capitalize()} video", video_path)
        
        if not validate_file_exists(video_path, logger):
            return None
        
        try:
            # Import pose extraction modules
            logger.debug("Importing pose extraction modules...")
            from extract_pose import MoveNetTFLite, BlazePoseWrapper, extract_frames_opencv
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'level1_pose'))
            from mp33_to_coco17 import mp33_to_coco17
            from level1_cleaning import clean_level1_poses
            
            # Create output directory for pose JSONs
            pose_json_dir = os.path.join(output_dir, f'{name}_pose_raw')
            os.makedirs(pose_json_dir, exist_ok=True)
            
            logger.info(f"Extracting pose from video...")
            logger.debug(f"  Model: {config.pose_model}")
            logger.debug(f"  Target FPS: {config.target_fps}")
            logger.debug(f"  Output dir: {pose_json_dir}")
            
            # Initialize pose estimator
            if os.path.exists(config.pose_model):
                estimator = MoveNetTFLite(config.pose_model)
                logger.debug("Using MoveNet estimator")
            else:
                estimator = BlazePoseWrapper()
                logger.debug("Using MediaPipe BlazePose estimator")
            
            # Extract frames and poses
            poses_list = []
            frame_count = 0
            
            for frame_id, timestamp, frame_bgr in extract_frames_opencv(video_path, config.target_fps):
                # Run pose estimation
                result = estimator.predict(frame_bgr)
                
                if result:
                    poses_list.append(result)
                    frame_count += 1
                    
                    if frame_count % 30 == 0:
                        logger.debug(f"  Processed {frame_count} frames...")
            
            if not poses_list:
                logger.error("No poses detected in video")
                return None
            
            logger.success(f"Extracted {frame_count} frames")
            
            # Convert to numpy array and process
            # The format depends on the estimator used
            # For MediaPipe: we need to convert from 33 joints to COCO-17
            # For MoveNet: already in 17-joint format
            
            logger.info("Converting to COCO-17 format and applying Level-1 cleaning...")
            
            # Stack poses
            if isinstance(estimator, BlazePoseWrapper):
                # MediaPipe format - need conversion
                logger.debug("Converting from MediaPipe 33 to COCO-17")
                # Extract keypoints from results
                mp33_poses = []
                for result in poses_list:
                    # result is dict with 'keypoints' key
                    kpts = result['keypoints']
                    mp33_poses.append([[kpt['x'], kpt['y']] for kpt in kpts.values()])
                
                mp33_array = np.array(mp33_poses)  # (T, 33, 2)
                logger.log_data_shape("MediaPipe poses", mp33_array.shape)
                
                pose_coco17 = mp33_to_coco17(mp33_array)
            else:
                # MoveNet format - already COCO-17
                logger.debug("Using MoveNet COCO-17 format directly")
                movenet_poses = []
                for result in poses_list:
                    kpts = result['keypoints']
                    movenet_poses.append([[kpts[i]['x'], kpts[i]['y']] for i in range(17)])
                
                pose_coco17 = np.array(movenet_poses)  # (T, 17, 2)
            
            logger.log_data_shape("COCO-17 poses", pose_coco17.shape)
            
            # Apply Level-1 cleaning
            logger.debug("Applying Level-1 cleaning pipeline...")
            pose_cleaned = clean_level1_poses(pose_coco17)
            
            logger.log_data_shape("Cleaned poses", pose_cleaned.shape)
            
            # Save intermediate output
            clean_pose_path = os.path.join(output_dir, f'{name}_pose_cleaned.npy')
            np.save(clean_pose_path, pose_cleaned)
            logger.success(f"Saved cleaned pose to {clean_pose_path}")
            
            return pose_cleaned
            
        except Exception as e:
            logger.log_error_detailed(f"Extract pose from video", e, video_path)
            traceback.print_exc()
            return None
    
    else:
        logger.error(f"Must provide either --{name} (pre-extracted) or --{name}-video")
        return None


def run_validation(
    expert_pose: np.ndarray,
    user_pose: np.ndarray,
    output_dir: str,
    logger: PipelineLogger
) -> Optional[Dict[str, float]]:
    """
    Run pose validation metrics.
    
    Args:
        expert_pose: Expert reference pose (T, 17, 2)
        user_pose: User pose (T, 17, 2)
        output_dir: Output directory
        logger: Logger instance
    
    Returns:
        Scores dictionary or None if failed
    """
    try:
        # Level-2 Temporal Alignment
        logger.info("Applying Level-2 temporal alignment...")
        from temporal_alignment import temporal_alignment
        
        user_indices, expert_indices = temporal_alignment(user_pose, expert_pose)
        
        # Apply alignment to both sequences
        user_pose_aligned = user_pose[user_indices]
        expert_pose_aligned = expert_pose[expert_indices]
        
        logger.debug(f"Aligned sequences: {len(user_indices)} frames")
        logger.log_data_shape("Aligned user pose", user_pose_aligned.shape)
        logger.log_data_shape("Aligned expert pose", expert_pose_aligned.shape)
        
        # Level-3 Error Localization
        logger.info("Computing Level-3 error localization...")
        try:
            from error_localization import compute_error_metrics
            
            error_metrics = compute_error_metrics(user_pose_aligned, expert_pose_aligned)
            
            # Save error metrics
            error_metrics_path = os.path.join(output_dir, 'error_metrics.json')
            with open(error_metrics_path, 'w') as f:
                json.dump(error_metrics, f, indent=2)
            logger.debug(f"Saved error metrics to {error_metrics_path}")
            
        except Exception as e:
            logger.warning(f"Level-3 error localization failed: {str(e)} (continuing with similarity scoring)")
        
        # Continue with existing similarity computation using aligned poses
        from pose_validation_metrics import PoseValidationMetrics
        
        logger.log_input("Expert pose", f"{expert_pose_aligned.shape}")
        logger.log_input("User pose", f"{user_pose_aligned.shape}")

        def clean_nan_pose(pose: np.ndarray) -> np.ndarray:
            """Replace NaN keypoints with forward-filled or zero values.
            Undetected face joints (eyes/ears) produce NaN that propagate
            through normalize_by_torso and destroy all scores."""
            pose = pose.copy()
            T, J, C = pose.shape
            for j in range(J):
                for c in range(C):
                    col = pose[:, j, c]
                    nan_mask = np.isnan(col)
                    if nan_mask.all():
                        pose[:, j, c] = 0.0
                    elif nan_mask.any():
                        # Forward-fill
                        idx = np.where(~nan_mask)[0]
                        pose[:, j, c] = np.interp(np.arange(T), idx, col[idx])
            return pose
        
        user_pose_clean = clean_nan_pose(user_pose_aligned)
        expert_pose_clean = clean_nan_pose(expert_pose_aligned)
        
        # Initialize metrics
        metrics = PoseValidationMetrics()
        logger.debug("Initialized PoseValidationMetrics")
        
        # Compute scores on aligned+cleaned sequences
        logger.info("Computing validation metrics...")
        scores = metrics.user_evaluation_score(user_pose_clean, expert_pose_clean)
        
        logger.success("Validation complete")
        logger.log_output("Structural score", f"{scores['structural']:.2f}/100")
        logger.log_output("Temporal score", f"{scores['temporal']:.2f}/100")
        logger.log_output("Overall score", f"{scores['overall']:.2f}/100")
        
        # Save scores
        scores_path = os.path.join(output_dir, 'scores.json')
        with open(scores_path, 'w') as f:
            json.dump(scores, f, indent=2)
        logger.debug(f"Saved scores to {scores_path}")
        
        return scores
        
    except Exception as e:
        logger.log_error_detailed("Pose validation", e)
        traceback.print_exc()
        return None


def run_feedback_pipeline(
    scores: Dict[str, float],
    output_dir: str,
    enable_tts: bool,
    config: PipelineConfig,
    logger: PipelineLogger
) -> Optional[Tuple[Dict[str, str], Optional[str]]]:
    """
    Generate feedback and optionally convert to speech.
    
    Args:
        scores: Validation scores
        output_dir: Output directory
        enable_tts: Whether to generate TTS audio
        config: Pipeline configuration
        logger: Logger instance
    
    Returns:
        Tuple of (feedback_dict, audio_path) or None if failed
    """
    try:
        from feedback_generator import FeedbackGenerator
        
        logger.log_input("Scores", f"Overall: {scores['overall']:.1f}/100")
        
        # Generate feedback
        logger.info("Generating feedback...")
        feedback_gen = FeedbackGenerator()
        feedback = feedback_gen.generate_user_feedback(scores)
        
        logger.success("Feedback generated")
        logger.log_output("Category", feedback['category'])
        logger.log_output("Overall message", feedback['overall'][:60] + "...")
        
        # Save feedback text
        feedback_json_path = os.path.join(output_dir, 'feedback.json')
        with open(feedback_json_path, 'w') as f:
            json.dump(feedback, f, indent=2)
        logger.debug(f"Saved feedback JSON to {feedback_json_path}")
        
        # Save detailed feedback text
        detailed_text = feedback_gen.generate_detailed_feedback(scores, mode='user')
        feedback_txt_path = os.path.join(output_dir, 'feedback.txt')
        with open(feedback_txt_path, 'w') as f:
            f.write(detailed_text)
        logger.debug(f"Saved feedback text to {feedback_txt_path}")
        
        audio_path = None
        
        # TTS conversion (optional)
        if enable_tts:
            try:
                from tts_engine import TTSEngine
                
                logger.info("Converting feedback to speech...")
                tts = TTSEngine(rate=config.tts_rate, volume=config.tts_volume)
                
                audio_path = os.path.join(output_dir, 'feedback.wav')
                success = tts.speak_feedback(feedback, mode='summary', save_file=audio_path)
                
                if success:
                    logger.success(f"Audio saved to {audio_path}")
                else:
                    logger.warning("TTS conversion failed (continuing without audio)")
                    audio_path = None
                    
            except Exception as e:
                logger.warning(f"TTS engine error: {str(e)} (continuing without audio)")
                audio_path = None
        else:
            logger.log_skip("TTS disabled")
        
        return feedback, audio_path
        
    except Exception as e:
        logger.log_error_detailed("Feedback generation", e)
        traceback.print_exc()
        return None


def run_visualization(
    expert_pose: np.ndarray,
    user_pose: np.ndarray,
    output_dir: str,
    enable_viz: bool,
    config: PipelineConfig,
    logger: PipelineLogger
) -> Optional[str]:
    """
    Render AR visualization video.
    
    Args:
        expert_pose: Expert pose (T, 17, 2)
        user_pose: User pose (T, 17, 2)
        output_dir: Output directory
        enable_viz: Whether to generate visualization
        config: Pipeline configuration
        logger: Logger instance
    
    Returns:
        Video path or None if skipped/failed
    """
    if not enable_viz:
        logger.log_skip("Visualization disabled")
        return None
    
    try:
        from ar_pose_renderer import PoseRenderer
        
        logger.log_input("Expert pose frames", f"{expert_pose.shape[0]}")
        logger.log_input("User pose frames", f"{user_pose.shape[0]}")
        
        # Initialize renderer
        logger.info("Rendering comparison video...")
        renderer = PoseRenderer(
            canvas_size=config.canvas_size,
            fps=config.viz_fps,
            line_thickness=config.line_thickness,
            joint_radius=config.joint_radius
        )
        
        logger.debug(f"Canvas size: {config.canvas_size}")
        logger.debug(f"FPS: {config.viz_fps}")
        
        # Render overlay
        video_path = os.path.join(output_dir, 'comparison.mp4')
        renderer.render_overlay(expert_pose, user_pose, video_path)
        
        logger.success(f"Video saved to {video_path}")
        
        return video_path
        
    except Exception as e:
        logger.warning(f"Visualization error: {str(e)} (continuing without video)")
        logger.debug(traceback.format_exc())
        return None


def main(args):
    """Main pipeline execution."""
    
    # Initialize configuration and logger
    config = PipelineConfig.from_args(args)
    logger = PipelineLogger(verbose=config.verbose)
    
    # Print header
    logger.header("AR-Based Kabaddi Ghost Trainer - Pipeline Execution")
    
    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Verbose logging: {config.verbose}")
    logger.info(f"TTS enabled: {config.enable_tts}")
    logger.info(f"Visualization enabled: {config.enable_viz}")
    
    total_stages = 4
    current_stage = 0
    
    # =========================================================================
    # STAGE 1: Load/Extract Expert Pose
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Load Expert/Reference Pose")
    
    expert_pose = load_or_extract_pose(
        input_path=args.expert_pose,
        video_path=args.expert_video if hasattr(args, 'expert_video') else None,
        output_dir=output_dir,
        config=config,
        logger=logger,
        name='expert'
    )
    
    if expert_pose is None:
        logger.error("Failed to load expert pose. Aborting pipeline.")
        sys.exit(1)
    
    logger.log_stage_complete("Load Expert Pose", f"Shape: {expert_pose.shape}")
    
    # =========================================================================
    # STAGE 2: Load/Extract User Pose + Level-1 Cleaning
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Load/Extract User Pose + Level-1 Cleaning")
    
    user_pose = load_or_extract_pose(
        input_path=args.user_pose,
        video_path=args.user_video if hasattr(args, 'user_video') else None,
        output_dir=output_dir,
        config=config,
        logger=logger,
        name='user'
    )
    
    if user_pose is None:
        logger.error("Failed to load/extract user pose. Aborting pipeline.")
        sys.exit(1)
    
    logger.log_stage_complete("User Pose Processing", f"Shape: {user_pose.shape}")
    
    # =========================================================================
    # STAGE 3: Pose Validation
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Pose Validation")
    
    scores = run_validation(expert_pose, user_pose, output_dir, logger)
    
    if scores is None:
        logger.error("Failed to compute validation scores. Aborting pipeline.")
        sys.exit(1)
    
    logger.log_stage_complete("Validation", f"Overall: {scores['overall']:.2f}/100")
    
    # =========================================================================
    # STAGE 4: Feedback Generation + TTS + Visualization
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Feedback Generation + TTS + Visualization")
    
    # Generate feedback and TTS
    feedback_result = run_feedback_pipeline(scores, output_dir, config.enable_tts, config, logger)
    
    if feedback_result is None:
        logger.error("Failed to generate feedback. Aborting pipeline.")
        sys.exit(1)
    
    feedback, audio_path = feedback_result
    
    logger.separator()
    
    # Generate visualization
    video_path = run_visualization(expert_pose, user_pose, output_dir, config.enable_viz, config, logger)
    
    logger.log_stage_complete("Feedback & Visualization")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    logger.info("")
    logger.header("Pipeline Complete - Summary")
    
    logger.info("[SCORES] Validation Scores:")
    logger.info(f"  • Structural: {scores['structural']:.2f}/100", indent=1)
    logger.info(f"  • Temporal: {scores['temporal']:.2f}/100", indent=1)
    logger.info(f"  • Overall: {scores['overall']:.2f}/100", indent=1)
    
    logger.info("")
    logger.info("[FILES] Generated Files:")
    logger.info(f"  • Scores: {os.path.join(output_dir, 'scores.json')}", indent=1)
    logger.info(f"  • Feedback (JSON): {os.path.join(output_dir, 'feedback.json')}", indent=1)
    logger.info(f"  • Feedback (Text): {os.path.join(output_dir, 'feedback.txt')}", indent=1)
    
    if audio_path:
        logger.info(f"  • Audio: {audio_path}", indent=1)
    
    if video_path:
        logger.info(f"  • Video: {video_path}", indent=1)
    
    logger.info("")
    logger.info("[FEEDBACK] Feedback:")
    logger.info(f"  {feedback['overall']}", indent=1)
    
    logger.info("")
    logger.success("[SUCCESS] All stages completed successfully!")
    logger.info("")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AR-Based Kabaddi Ghost Trainer - Complete Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-extracted poses
  python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --output results
  
  # Extract from video
  python run_pipeline.py --expert raider_pose_level1.npy --user-video masked_raider.mp4 --output results
  
  # Disable TTS and visualization
  python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --no-tts --no-viz --output results
  
  # Verbose logging
  python run_pipeline.py --expert raider_pose_level1.npy --user pose_3d.npy --output results --verbose
        """
    )
    
    # Expert/reference pose
    expert_group = parser.add_mutually_exclusive_group(required=True)
    expert_group.add_argument(
        '--expert-pose',
        type=str,
        help="Path to expert pose .npy file (pre-extracted)"
    )
    expert_group.add_argument(
        '--expert-video',
        type=str,
        help="Path to expert video file (will extract pose)"
    )
    
    # User pose
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument(
        '--user-pose',
        type=str,
        help="Path to user pose .npy file (pre-extracted)"
    )
    user_group.add_argument(
        '--user-video',
        type=str,
        help="Path to user video file (will extract pose)"
    )
    
    # Output
    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help="Output directory for all results"
    )
    
    # Optional features
    parser.add_argument(
        '--no-tts',
        action='store_true',
        help="Disable text-to-speech audio generation"
    )
    parser.add_argument(
        '--no-viz',
        action='store_true',
        help="Disable AR visualization video"
    )
    
    # Logging
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Enable verbose debug logging"
    )
    
    # Advanced options
    parser.add_argument(
        '--pose-model',
        type=str,
        default="movenet_lightning.tflite",
        help="Pose estimation model (default: movenet_lightning.tflite)"
    )
    parser.add_argument(
        '--target-fps',
        type=float,
        default=30.0,
        help="Target FPS for video extraction (default: 30.0)"
    )
    parser.add_argument(
        '--width',
        type=int,
        default=640,
        help="Visualization canvas width (default: 640)"
    )
    parser.add_argument(
        '--height',
        type=int,
        default=480,
        help="Visualization canvas height (default: 480)"
    )
    
    args = parser.parse_args()
    
    try:
        main(args)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
