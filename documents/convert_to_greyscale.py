"""Convert selected review1 diagrams to greyscale for the report."""
from PIL import Image
import os

REVIEW1 = r"c:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\review1"
DOCS = r"c:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\documents\figures"

os.makedirs(DOCS, exist_ok=True)

# Map: source_filename -> output_name
diagrams = {
    "AR Ghost Architectures  .png": "system_architecture_overview.png",
    "Block Diagram1.drawio.png": "person_detection_pipeline.png",
    "mermaid-diagram-2026-01-26-081857.png": "pose_estimation_flow.png",
    "mermaid-diagram-2026-01-26-090441.png": "level1_cleaning_stage1.png",
    "mermaid-diagram-2026-01-26-092139.png": "level1_cleaning_stage2.png",
    "mermaid-diagram-2026-01-26-092348.png": "pelvis_trajectory_extraction.png",
    "mermaid-diagram-2026-01-26-092601.png": "dtw_alignment.png",
    "mermaid-diagram-2026-01-26-092729.png": "aligned_sequence_generation.png",
    "mermaid-diagram-2026-01-26-092911.png": "error_computation.png",
    "mermaid-diagram-2026-01-26-093401.png": "statistical_aggregation.png",
    "mermaid-diagram-2026-01-26-093544.png": "similarity_scoring.png",
    "mermaid-diagram-2026-01-26-093806.png": "data_serialization.png",
}

for src_name, dst_name in diagrams.items():
    src = os.path.join(REVIEW1, src_name)
    dst = os.path.join(DOCS, dst_name)
    if not os.path.exists(src):
        print(f"SKIP (not found): {src_name}")
        continue
    img = Image.open(src).convert("L")  # greyscale
    img.save(dst)
    print(f"OK: {src_name} -> {dst_name}")

print("\nDone. All greyscale images saved to:", DOCS)
