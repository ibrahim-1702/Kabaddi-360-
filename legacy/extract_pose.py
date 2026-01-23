#!/usr/bin/env python3
"""
extract_pose.py

Usage:
  python extract_pose.py --video path/to/video.mp4 --outdir ./pose_out --model movenet_lightning.tflite

This script:
 - extracts frames from a video
 - runs MoveNet TFLite (preferred) or MediaPipe BlazePose (fallback)
 - saves per-frame JSON with structure:
   { "frame_id": int, "timestamp": float, "joints": [ {"name":str,"x":float,"y":float,"conf":float}, ... ] }

Requirements (install via pip):
 pip install opencv-python numpy pandas matplotlib pyarrow   # optional: pandas/pyarrow for parquet saving
 # For MoveNet (TFLite):
 pip install tensorflow  # or tflite-runtime if you prefer
 # For MediaPipe fallback:
 pip install mediapipe

Note: if both TF and mediapipe are present, MoveNet will be used if a valid tflite model is supplied.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import numpy as np

# ---------------------------
# Utility: frame extraction
# ---------------------------
def extract_frames_opencv(video_path: str, target_fps: float = None):
    """Yields (frame_id, timestamp_seconds, frame_bgr)"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        timestamp = frame_id / video_fps
        yield frame_id, timestamp, frame
        frame_id += 1
    cap.release()

# ---------------------------
# MoveNet (TFLite) wrapper
# ---------------------------
class MoveNetTFLite:
    def __init__(self, model_path: str):
        # Try tflite_runtime first (lightweight), then tensorflow
        self.interpreter = None
        self.model_path = model_path
        try:
            from tflite_runtime.interpreter import Interpreter
            self.interpreter = Interpreter(model_path)
        except Exception:
            try:
                import tensorflow as tf
                self.interpreter = tf.lite.Interpreter(model_path=model_path)
            except Exception as e:
                raise RuntimeError("Cannot load TFLite interpreter. Install tflite-runtime or tensorflow.") from e
        self.interpreter.allocate_tensors()
        # get input details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        # assume input size square
        inp_shape = self.input_details[0]['shape']
        self.input_height = int(inp_shape[1])
        self.input_width = int(inp_shape[2])

        # movenet keypoint names (COCO-style):
        self.keypoint_names = [
            "nose","left_eye","right_eye","left_ear","right_ear",
            "left_shoulder","right_shoulder","left_elbow","right_elbow",
            "left_wrist","right_wrist","left_hip","right_hip",
            "left_knee","right_knee","left_ankle","right_ankle"
        ]

    def preprocess(self, frame_bgr: np.ndarray):
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.input_width, self.input_height))
        img = img.astype(np.float32)
        img = img[np.newaxis, ...]
        # normalization expected for MoveNet: [-1,1] or [0,1] depending on model; use 0-255 -> /255
        img = img / 255.0
        return img

    def predict(self, frame_bgr: np.ndarray) -> List[Dict]:
        inp = self.preprocess(frame_bgr)
        self.interpreter.set_tensor(self.input_details[0]['index'], inp)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        # MoveNet outputs [1, 17, 3] => y,x,score (normalized)
        kps = output_data[0]  # shape (17,3)
        joints = []
        h, w = frame_bgr.shape[:2]
        for idx, (y, x, score) in enumerate(kps):
            joints.append({
                "name": self.keypoint_names[idx],
                "x": float(x * w),
                "y": float(y * h),
                "conf": float(score)
            })
        return joints

# ---------------------------
# MediaPipe BlazePose wrapper (fallback)
# ---------------------------
class BlazePoseWrapper:
    def __init__(self, model_complexity: int = 1):
        try:
            import mediapipe as mp
        except Exception as e:
            raise RuntimeError("mediapipe not installed. pip install mediapipe") from e
        self.mp = mp
        self.pose = mp.solutions.pose.Pose(static_image_mode=False,
                                           model_complexity=model_complexity,
                                           enable_segmentation=False,
                                           min_detection_confidence=0.4,
                                           min_tracking_confidence=0.4)
        # define a mapping of relevant landmarks to names. BlazePose has 33 landmarks.
        # We'll map a subset similar to MoveNet names for compatibility.
        self.landmark_map = {
            0: "nose",
            1: "left_eye_inner",
            2: "left_eye",
            3: "left_eye_outer",
            4: "right_eye_inner",
            5: "right_eye",
            6: "right_eye_outer",
            7: "left_ear",
            8: "right_ear",
            11: "left_shoulder",
            12: "right_shoulder",
            13: "left_elbow",
            14: "right_elbow",
            15: "left_wrist",
            16: "right_wrist",
            23: "left_hip",
            24: "right_hip",
            25: "left_knee",
            26: "right_knee",
            27: "left_ankle",
            28: "right_ankle"
        }

    def predict(self, frame_bgr: np.ndarray) -> List[Dict]:
        img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.pose.process(img_rgb)
        h, w = frame_bgr.shape[:2]
        joints = []
        if not result.pose_landmarks:
            # return zero-confidence keypoints with NaNs or -1 coordinates
            for idx, name in self.landmark_map.items():
                joints.append({"name": name, "x": None, "y": None, "conf": 0.0})
            return joints

        for idx, name in self.landmark_map.items():
            lm = result.pose_landmarks.landmark[idx]
            joints.append({
                "name": name,
                "x": float(lm.x * w),
                "y": float(lm.y * h),
                "conf": float(lm.visibility if hasattr(lm, 'visibility') else lm.visibility if hasattr(lm, 'visibility') else lm.z if hasattr(lm, 'z') else 1.0)
            })
        return joints

# ---------------------------
# Main driver
# ---------------------------
def ensure_dir(d: str):
    Path(d).mkdir(parents=True, exist_ok=True)

def save_json(obj: dict, outpath: str):
    with open(outpath, 'w') as f:
        json.dump(obj, f, indent=2)

def main(args):
    ensure_dir(args.outdir)

    # Choose model: MoveNet if model path supplied and available, else MediaPipe
    pose_model = None
    use_movenet = False
    if args.model and os.path.isfile(args.model):
        try:
            print(f"[INFO] Loading MoveNet model from {args.model} ...")
            pose_model = MoveNetTFLite(args.model)
            use_movenet = True
            print("[INFO] Using MoveNet (TFLite).")
        except Exception as e:
            print(f"[WARN] MoveNet load failed: {e}. Will try MediaPipe fallback.")
            pose_model = None

    if pose_model is None:
        try:
            print("[INFO] Initializing MediaPipe BlazePose fallback...")
            pose_model = BlazePoseWrapper()
            print("[INFO] Using MediaPipe BlazePose.")
        except Exception as e:
            print("[ERROR] No pose model available. Install tensorflow or mediapipe and/or provide a MoveNet tflite model.")
            raise

    sample_printed = False
    n_saved = 0
    for frame_id, timestamp, frame in extract_frames_opencv(args.video):
        # optional resizing for speed
        if args.max_dim:
            h,w = frame.shape[:2]
            maxd = max(h,w)
            if maxd > args.max_dim:
                scale = args.max_dim / maxd
                frame = cv2.resize(frame, (int(w*scale), int(h*scale)))

        joints = []
        try:
            joints = pose_model.predict(frame)
        except Exception as e:
            print(f"[WARN] Prediction failed on frame {frame_id}: {e}")
            # create zero-confidence list with approximate joint names if possible
            joints = [{"name": f"kp_{i}", "x": None, "y": None, "conf": 0.0} for i in range(17)]

        out_obj = {
            "frame_id": int(frame_id),
            "timestamp": float(timestamp),
            "joints": joints
        }

        outpath = os.path.join(args.outdir, f"frame_{frame_id:06d}.json")
        save_json(outobj := out_obj, outpath)

        n_saved += 1

        # print a sample frame keypoints (first frame or user-specified sample)
        if not sample_printed and (args.sample_frame is None or frame_id == args.sample_frame):
            print("\n--- Sample keypoints (frame {}) ---".format(frame_id))
            print(json.dumps(outobj, indent=2))
            sample_printed = True

        # Optionally stop after N frames (for quick tests)
        if args.max_frames and n_saved >= args.max_frames:
            break

    print(f"[DONE] Saved {n_saved} pose JSON files to {args.outdir}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extract pose per frame and save JSONs.")
    p.add_argument("--video", required=True, help="Path to input video")
    p.add_argument("--outdir", required=True, help="Output directory for per-frame JSONs")
    p.add_argument("--model", required=False, default=None, help="Path to MoveNet .tflite model (optional). If omitted, uses MediaPipe")
    p.add_argument("--max-frames", type=int, default=None, help="Stop after saving N frames (for testing)")
    p.add_argument("--sample-frame", type=int, default=0, help="Which frame to print sample keypoints for (default 0)")
    p.add_argument("--max-dim", type=int, default=1024, help="Resize frames so longest side <= max-dim (speeds processing)")
    args = p.parse_args()
    main(args)
