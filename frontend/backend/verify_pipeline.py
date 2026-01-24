"""
Quick verification script - Run this to check if pipeline_runner.py is correct
"""

import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 70)
print("VERIFYING PIPELINE_RUNNER.PY")
print("=" * 70)

try:
    # Try importing the module
    print("\n[1/3] Importing pipeline_runner...")
    import frontend.backend.pipeline_runner as pr
    print("  ✓ Module imported successfully")
    
    # Check if functions exist
    print("\n[2/3] Checking function definitions...")
    
    functions_to_check = [
        'extract_pelvis',
        'dtw_align',
        'run_level2_dtw',
        'compute_joint_errors',
        'aggregate_joint_stats',
        'aggregate_frame_stats',
        'compute_phase_stats',
        'export_frame_joint_errors',
        'compute_structural_similarity',
        'compute_temporal_similarity',
        'compute_overall_score',
        'run_level3_errors',
        'run_level4_scoring',
        'run_demo_pipeline'
    ]
    
    missing = []
    for func_name in functions_to_check:
        if hasattr(pr, func_name):
            print(f"  ✓ {func_name}")
        else:
            print(f"  ✗ {func_name} - MISSING!")
            missing.append(func_name)
    
    if missing:
        print(f"\n❌ ERROR: {len(missing)} functions missing!")
        print("This means the server is using OLD code.")
        print("\nRESTART THE SERVER:")
        print("  1. Stop Flask (Ctrl+C)")
        print("  2. python app.py")
        sys.exit(1)
    
    # Check LEVEL1_AVAILABLE flag
    print("\n[3/3] Checking Level-1 availability...")
    if hasattr(pr, 'LEVEL1_AVAILABLE'):
        print(f"  LEVEL1_AVAILABLE = {pr.LEVEL1_AVAILABLE}")
        if not pr.LEVEL1_AVAILABLE:
            print("  ⚠ WARNING: Level-1 pose extraction not available!")
            print("    Install: pip install ultralytics mediapipe opencv-python")
    else:
        print("  ✗ LEVEL1_AVAILABLE not found")
    
    print("\n" + "=" * 70)
    print("✅ ALL CHECKS PASSED!")
    print("=" * 70)
    print("\nIf you still get errors:")
    print("1. STOP the Flask server (Ctrl+C)")
    print("2. Delete Python cache: rm -rf __pycache__")  
    print("3. START server again: python app.py")
    print("\nServer MUST be restarted to load new code!")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("\nThis usually means:")
    print("1. Wrong directory - run from project root")
    print("2. Missing dependencies - pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
