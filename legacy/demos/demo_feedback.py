"""
Feedback & TTS Integration Demo

End-to-end demonstration of the feedback and TTS pipeline for
AR-Based Kabaddi Ghost Trainer.

Flow:
  Pose Metrics → Feedback Generator → TTS Engine → Audio Output

This script demonstrates:
1. Loading/simulating pose validation scores
2. Generating structured feedback
3. Converting feedback to speech
4. Saving audio files for offline demos
"""

import numpy as np
from feedback_generator import FeedbackGenerator
from tts_engine import TTSEngine


def demo_feedback_pipeline():
    """
    Demonstrate complete feedback and TTS pipeline.
    """
    print("=" * 70)
    print("FEEDBACK & TTS PIPELINE DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Initialize modules
    print("[1] Initializing modules...")
    feedback_gen = FeedbackGenerator()
    tts_engine = TTSEngine(rate=160, volume=0.9)
    print("✓ Modules initialized\n")
    
    # Check TTS availability
    if tts_engine.engine is None:
        print("[WARNING] TTS engine not available.")
        print("Install pyttsx3 to enable audio: pip install pyttsx3")
        print("Continuing with text-only demo...\n")
        tts_available = False
    else:
        tts_available = True
    
    # Define test scenarios
    scenarios = [
        {
            'name': 'Ghost Validation - Excellent',
            'mode': 'ghost',
            'scores': {'structural': 95.0, 'temporal': 92.0, 'overall': 93.5},
            'audio_file': 'ghost_excellent.wav'
        },
        {
            'name': 'Ghost Validation - Needs Calibration',
            'mode': 'ghost',
            'scores': {'structural': 65.0, 'temporal': 62.0, 'overall': 63.5},
            'audio_file': 'ghost_fair.wav'
        },
        {
            'name': 'User Evaluation - Outstanding',
            'mode': 'user',
            'scores': {'structural': 93.0, 'temporal': 91.0, 'overall': 92.0},
            'audio_file': 'user_excellent.wav'
        },
        {
            'name': 'User Evaluation - Keep Practicing',
            'mode': 'user',
            'scores': {'structural': 55.0, 'temporal': 52.0, 'overall': 53.5},
            'audio_file': 'user_needs_improvement.wav'
        }
    ]
    
    # Process each scenario
    for i, scenario in enumerate(scenarios, 1):
        print("=" * 70)
        print(f"SCENARIO {i}: {scenario['name']}")
        print("=" * 70)
        print()
        
        # Display scores
        print("Input Scores:")
        print(f"  Overall:    {scenario['scores']['overall']:.1f}/100")
        print(f"  Structural: {scenario['scores']['structural']:.1f}/100")
        print(f"  Temporal:   {scenario['scores']['temporal']:.1f}/100")
        print()
        
        # Generate feedback
        if scenario['mode'] == 'ghost':
            feedback = feedback_gen.generate_ghost_feedback(scenario['scores'])
        else:
            feedback = feedback_gen.generate_user_feedback(scenario['scores'])
        
        print("Generated Feedback:")
        print(f"  Category: {feedback['category'].replace('_', ' ').title()}")
        print(f"  Overall:  {feedback['overall']}")
        print(f"  Structural: {feedback['structural']}")
        print(f"  Temporal:   {feedback['temporal']}")
        print()
        
        # Convert to speech and save
        if tts_available:
            print("[Audio Processing]")
            print(f"  Speaking feedback...")
            tts_engine.speak_feedback(feedback, mode='summary', save_file=scenario['audio_file'])
            print(f"  ✓ Audio saved to: {scenario['audio_file']}")
        else:
            print("[Audio] TTS not available - skipping audio generation")
        
        print()
    
    print("=" * 70)
    print("DETERMINISM VERIFICATION")
    print("=" * 70)
    print()
    
    # Verify deterministic behavior
    test_score = {'structural': 75.0, 'temporal': 72.0, 'overall': 73.5}
    
    print("Testing determinism with same input scores:")
    print(f"  Scores: {test_score}")
    print()
    
    feedback1 = feedback_gen.generate_user_feedback(test_score)
    feedback2 = feedback_gen.generate_user_feedback(test_score)
    
    print("First call:")
    print(f"  {feedback1['overall']}")
    print()
    print("Second call:")
    print(f"  {feedback2['overall']}")
    print()
    print(f"Identical outputs? {feedback1 == feedback2}")
    print()
    
    print("=" * 70)
    print("INTEGRATION WITH POSE METRICS")
    print("=" * 70)
    print()
    
    # Demonstrate integration with pose validation metrics
    print("Simulating pose validation workflow...")
    print()
    
    # Simulate pose metric computation (would come from pose_validation_metrics.py)
    print("[Step 1] Pose metrics computed (simulated)")
    simulated_metrics = {
        'structural': 87.3,
        'temporal': 82.1,
        'overall': 84.7
    }
    print(f"  Metrics: {simulated_metrics}")
    print()
    
    print("[Step 2] Generate feedback")
    user_feedback = feedback_gen.generate_user_feedback(simulated_metrics)
    detailed = feedback_gen.generate_detailed_feedback(simulated_metrics, mode='user')
    print(detailed)
    print()
    
    print("[Step 3] Convert to speech")
    if tts_available:
        tts_engine.speak_feedback(user_feedback, mode='summary', save_file='integrated_demo.wav')
        print("  ✓ Feedback spoken and saved")
    else:
        print("  TTS not available - text feedback only")
    print()
    
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    
    if tts_available:
        print("Audio files created:")
        for scenario in scenarios:
            print(f"  - {scenario['audio_file']}")
        print("  - integrated_demo.wav")
        print()
    
    print("Integration Summary:")
    print("  1. Pose metrics provide score dictionary")
    print("  2. FeedbackGenerator maps scores to text")
    print("  3. TTSEngine converts text to speech")
    print("  4. Audio can be played or saved for demos")
    print()


def demo_with_real_metrics():
    """
    Optionally demonstrate with real pose validation metrics.
    
    This requires pose_validation_metrics.py and actual pose data.
    """
    try:
        from pose_validation_metrics import PoseValidationMetrics
        
        print("=" * 70)
        print("DEMO WITH REAL POSE METRICS")
        print("=" * 70)
        print()
        
        # Initialize
        metrics = PoseValidationMetrics()
        feedback_gen = FeedbackGenerator()
        tts_engine = TTSEngine()
        
        # Generate sample data (normally would load from files)
        print("Generating sample pose data...")
        expert_pose = np.random.rand(100, 17, 2) * 100
        ghost_pose = expert_pose + np.random.randn(100, 17, 2) * 2
        user_pose = ghost_pose + np.random.randn(100, 17, 2) * 5
        
        # Compute ghost validation
        print("\n[Ghost Validation]")
        ghost_scores = metrics.ghost_validation_score(expert_pose, ghost_pose)
        print(f"Scores: {ghost_scores}")
        
        ghost_feedback = feedback_gen.generate_ghost_feedback(ghost_scores)
        print(f"Feedback: {ghost_feedback['overall']}")
        
        if tts_engine.engine:
            tts_engine.speak_feedback(ghost_feedback, mode='summary')
        
        # Compute user evaluation
        print("\n[User Evaluation]")
        user_scores = metrics.user_evaluation_score(user_pose, ghost_pose)
        print(f"Scores: {user_scores}")
        
        user_feedback = feedback_gen.generate_user_feedback(user_scores)
        print(f"Feedback: {user_feedback['overall']}")
        
        if tts_engine.engine:
            tts_engine.speak_feedback(user_feedback, mode='summary')
        
        print("\n✓ Real metrics integration successful")
        
    except ImportError:
        print("pose_validation_metrics.py not found - skipping real metrics demo")
    except Exception as e:
        print(f"Error in real metrics demo: {e}")


if __name__ == "__main__":
    """
    Run complete demonstration.
    """
    
    # Main demo
    demo_feedback_pipeline()
    
    # Optional: Demo with real metrics
    print("\n" + "=" * 70)
    print("OPTIONAL: Real Pose Metrics Integration")
    print("=" * 70)
    response = input("\nRun demo with real pose metrics? (y/n): ").strip().lower()
    
    if response == 'y':
        demo_with_real_metrics()
    else:
        print("Skipping real metrics demo.")
    
    print("\n" + "=" * 70)
    print("ALL DEMOS COMPLETE")
    print("=" * 70)
