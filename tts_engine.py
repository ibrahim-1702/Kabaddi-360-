"""
Text-to-Speech Engine for AR-Based Kabaddi Ghost Trainer

This module provides offline text-to-speech conversion using pyttsx3.
Converts feedback text into speech for audio playback and demo purposes.

Features:
- Offline TTS (no internet required)
- Configurable voice properties
- Optional audio file export
- Fallback handling

Dependencies:
- pyttsx3: pip install pyttsx3
"""

import os
from typing import Optional


class TTSEngine:
    """
    Offline TTS engine using pyttsx3 for feedback audio generation.
    
    Provides real-time speech playback and audio file export capabilities.
    """
    
    def __init__(self, rate: int = 150, volume: float = 0.9):
        """
        Initialize TTS engine with default settings.
        
        Args:
            rate: Speech rate (words per minute), default 150
            volume: Volume level [0.0, 1.0], default 0.9
        """
        self.rate = rate
        self.volume = volume
        self.engine = None
        self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """
        Initialize pyttsx3 engine with error handling.
        
        Sets up the TTS engine with configured parameters.
        Gracefully handles initialization failures.
        """
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            print("[TTS] Engine initialized successfully")
        except ImportError:
            print("[TTS] WARNING: pyttsx3 not installed. Install with: pip install pyttsx3")
            self.engine = None
        except Exception as e:
            print(f"[TTS] ERROR: Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def configure(
        self, 
        rate: Optional[int] = None, 
        volume: Optional[float] = None,
        voice_id: Optional[int] = None
    ) -> None:
        """
        Configure TTS engine properties.
        
        Args:
            rate: Speech rate (words per minute)
            volume: Volume level [0.0, 1.0]
            voice_id: Voice index (0 for first available, 1 for second, etc.)
        """
        if self.engine is None:
            print("[TTS] Engine not available. Skipping configuration.")
            return
        
        if rate is not None:
            self.rate = rate
            self.engine.setProperty('rate', rate)
        
        if volume is not None:
            self.volume = max(0.0, min(1.0, volume))  # Clamp to [0, 1]
            self.engine.setProperty('volume', self.volume)
        
        if voice_id is not None:
            voices = self.engine.getProperty('voices')
            if 0 <= voice_id < len(voices):
                self.engine.setProperty('voice', voices[voice_id].id)
                print(f"[TTS] Voice set to: {voices[voice_id].name}")
            else:
                print(f"[TTS] WARNING: Invalid voice_id {voice_id}. Available: 0-{len(voices)-1}")
    
    def list_available_voices(self) -> None:
        """
        Print list of available voices on the system.
        
        Useful for selecting different voice options.
        """
        if self.engine is None:
            print("[TTS] Engine not available.")
            return
        
        voices = self.engine.getProperty('voices')
        print(f"\n[TTS] Available Voices ({len(voices)} total):")
        print("-" * 60)
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} ({voice.id})")
            print(f"   Languages: {voice.languages}")
            print(f"   Gender: {voice.gender if hasattr(voice, 'gender') else 'N/A'}")
        print("-" * 60)
    
    def speak_text(self, text: str, wait: bool = True) -> bool:
        """
        Convert text to speech and play audio.
        
        Args:
            text: Text to convert to speech
            wait: If True, block until speech completes
        
        Returns:
            True if successful, False otherwise
        """
        if self.engine is None:
            print("[TTS] Engine not available. Cannot speak text.")
            return False
        
        try:
            self.engine.say(text)
            if wait:
                self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"[TTS] ERROR during speech: {e}")
            return False
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Convert text to speech and save as audio file.
        
        Args:
            text: Text to convert to speech
            filename: Output filename (e.g., 'feedback.wav')
        
        Returns:
            True if successful, False otherwise
        
        Note:
            pyttsx3 typically saves as WAV format on Windows,
            but format may vary by platform.
        """
        if self.engine is None:
            print("[TTS] Engine not available. Cannot save audio.")
            return False
        
        try:
            # Ensure absolute path
            if not os.path.isabs(filename):
                filename = os.path.abspath(filename)
            
            # Save to file
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"[TTS] Audio saved: {filename} ({file_size} bytes)")
                return True
            else:
                print(f"[TTS] WARNING: File not created: {filename}")
                return False
        except Exception as e:
            print(f"[TTS] ERROR saving audio: {e}")
            return False
    
    def speak_feedback(
        self, 
        feedback_dict: dict, 
        mode: str = 'summary',
        save_file: Optional[str] = None
    ) -> bool:
        """
        Speak feedback from feedback generator output.
        
        Args:
            feedback_dict: Output from FeedbackGenerator
            mode: 'summary' for overall only, 'detailed' for all components
            save_file: Optional filename to save audio
        
        Returns:
            True if successful, False otherwise
        """
        if mode == 'summary':
            text = feedback_dict.get('overall', '')
        elif mode == 'detailed':
            parts = [
                feedback_dict.get('overall', ''),
                "Structural assessment: " + feedback_dict.get('structural', ''),
                "Temporal assessment: " + feedback_dict.get('temporal', '')
            ]
            text = ". ".join(parts)
        else:
            print(f"[TTS] WARNING: Unknown mode '{mode}'. Using 'summary'.")
            text = feedback_dict.get('overall', '')
        
        # Speak the text
        success = self.speak_text(text, wait=True)
        
        # Optionally save to file
        if save_file and success:
            self.save_to_file(text, save_file)
        
        return success


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    """
    Example usage demonstrating TTS functionality.
    """
    
    print("=" * 70)
    print("TEXT-TO-SPEECH ENGINE - DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Initialize TTS engine
    tts = TTSEngine(rate=160, volume=0.9)
    
    if tts.engine is None:
        print("\n[ERROR] TTS engine not available. Install pyttsx3:")
        print("  pip install pyttsx3")
        print("\nExiting demo.")
        exit(1)
    
    # List available voices
    tts.list_available_voices()
    print()
    
    # Test 1: Simple text-to-speech
    print("TEST 1: Simple Speech")
    print("-" * 70)
    test_text = "Outstanding performance! You matched the expert technique exceptionally well."
    print(f"Text: {test_text}")
    print("\n[Speaking...]")
    tts.speak_text(test_text)
    print("[Done]\n")
    
    # Test 2: Save to file
    print("TEST 2: Save Audio to File")
    print("-" * 70)
    output_file = "test_feedback_audio.wav"
    print(f"Saving to: {output_file}")
    success = tts.save_to_file(test_text, output_file)
    if success:
        print(f"✓ Audio file created successfully")
    print()
    
    # Test 3: Feedback dictionary (simulated)
    print("TEST 3: Feedback Dictionary Speech")
    print("-" * 70)
    sample_feedback = {
        'overall': "Great job! Your performance is very good with minor areas for improvement.",
        'structural': "Your pose structure is mostly accurate.",
        'temporal': "Your timing is mostly synchronized.",
        'category': 'very_good'
    }
    
    print("Feedback:")
    for key, value in sample_feedback.items():
        if key != 'category':
            print(f"  {key}: {value}")
    
    print("\n[Speaking summary...]")
    tts.speak_feedback(sample_feedback, mode='summary')
    print("[Done]")
    print()
    
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    
    # Cleanup test file
    if os.path.exists(output_file):
        print(f"\nNote: Test audio file saved as '{output_file}'")
