
import numpy as np
import os
import json

# Using the specific session ID found
session_id = "039ae972-178d-4520-86ff-b7c9b02d5d6b"
base_dir = r"c:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\data\results"
session_dir = os.path.join(base_dir, session_id)

expert_path = os.path.join(session_dir, "expert_aligned.npy")
user_path = os.path.join(session_dir, "user_aligned.npy")
json_path = os.path.join(session_dir, "joint_errors.json")

def print_empirical_data():
    try:
        expert = np.load(expert_path)
        user = np.load(user_path)
        
        print(f"Loaded successfully from: {session_dir}")
        print(f"Shapes: Expert={expert.shape}, User={user.shape}")
        
        # Select Frame 25, Joint 13 (Left Knee)
        frame_idx = 25
        joint_idx = 13 # Left Knee
        
        if frame_idx >= len(expert):
            frame_idx = len(expert) - 1
            
        e_pt = expert[frame_idx, joint_idx]
        u_pt = user[frame_idx, joint_idx]
        
        print("\n=== RAW COORDINATES (Normalized) ===")
        print(f"Frame: {frame_idx}")
        print(f"Joint: 13 (Left Knee)")
        print(f"Expert Point (x_e, y_e): ({e_pt[0]:.6f}, {e_pt[1]:.6f})")
        print(f"User Point   (x_u, y_u): ({u_pt[0]:.6f}, {u_pt[1]:.6f})")
        
        # Calculate Error
        diff_x = e_pt[0] - u_pt[0]
        diff_y = e_pt[1] - u_pt[1]
        dist = np.sqrt(diff_x**2 + diff_y**2)
        print(f"\nCalculated Distance: {dist:.6f}")
        
        # Statistics simulation for the REPORT
        # We also want the "Overall Mean Joint Error" used for structural scoring
        all_diffs = expert - user
        all_dists = np.linalg.norm(all_diffs, axis=2) # T x 17
        
        # Clean NaNs (crucial step in algorithm)
        clean_means = []
        for j in range(17):
            joint_dists = all_dists[:, j]
            mean_j = np.nanmean(joint_dists)
            clean_means.append(mean_j)
            
        overall_mean_joint_error = np.nanmean(clean_means)
        
        print(f"\n=== STRUCTURAL DATA ===")
        print(f"Mean Errors for first 3 joints: {clean_means[:3]}")
        print(f"Overall Mean Joint Error (nanmean): {overall_mean_joint_error:.6f}")
        
        # Temporal
        num_frames = len(user)
        print(f"\n=== TEMPORAL DATA ===")
        print(f"Aligned Frame Count (T_aligned): {num_frames}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print_empirical_data()
