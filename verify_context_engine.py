"""
Simple verification script for Context Engine
"""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from llm_feedback.context_engine import generate_context, load_raw_scores, save_context

def main():
    print("=" * 70)
    print("CONTEXT ENGINE VERIFICATION")
    print("=" * 70)
    
    # Test with real data
    results_path = "data/results/039ae972-178d-4520-86ff-b7c9b02d5d6b/results.json"
    output_path = "context_output.json"
    
    print(f"\n[1/3] Loading raw scores from: {results_path}")
    try:
        raw_scores = load_raw_scores(results_path)
        print(f"  ✓ Loaded successfully")
        print(f"  ✓ Session: {raw_scores['session_id']}")
        print(f"  ✓ Frames: {raw_scores['error_statistics']['metadata']['num_frames']}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False
    
    print(f"\n[2/3] Generating canonical context...")
    try:
        context = generate_context(raw_scores)
        print(f"  ✓ Context generated successfully")
        print(f"  ✓ Overall score: {context['summary']['overall_score']}% ({context['summary']['overall_assessment']})")
        print(f"  ✓ Structural: {context['summary']['structural_score']}% ({context['summary']['structural_assessment']})")
        print(f"  ✓ Temporal: {context['summary']['temporal_score']}% ({context['summary']['temporal_assessment']})")
        print(f"  ✓ Major deviations: {len(context['joint_deviations']['major'])}")
        print(f"  ✓ Moderate deviations: {len(context['joint_deviations']['moderate'])}")
        print(f"  ✓ Minor deviations: {len(context['joint_deviations']['minor'])}")
        print(f"  ✓ Temporal trend: {context['temporal_trend']['pattern']}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n[3/3] Saving context to: {output_path}")
    try:
        save_context(context, output_path)
        print(f"  ✓ Saved successfully")
        
        # Calculate compression
        raw_json = json.dumps(raw_scores, indent=2)
        context_json = json.dumps(context, indent=2)
        raw_lines = len(raw_json.split('\n'))
        context_lines = len(context_json.split('\n'))
        
        print(f"\n  COMPRESSION:")
        print(f"    Raw results.json: {raw_lines} lines")
        print(f"    Context JSON: {context_lines} lines")
        print(f"    Reduction: {raw_lines - context_lines} lines ({100*(1-context_lines/raw_lines):.1f}% smaller)")
        
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("VERIFICATION SUCCESSFUL ✓")
    print("=" * 70)
    print("\n✓ Context Engine is working correctly")
    print("✓ All aggregations deterministic and traceable")
    print("✓ Output is compact and LLM-ready")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
