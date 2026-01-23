"""
Pipeline Configuration Management

Centralized configuration for AR-Based Kabaddi Ghost Trainer pipeline.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    
    # Pose extraction settings
    pose_model: str = "movenet_lightning.tflite"
    target_fps: float = 30.0
    max_dim: int = 1024
    
    # Level-1 cleaning settings
    ema_alpha: float = 0.75
    outlier_threshold: float = 3.0
    
    # TTS settings
    tts_rate: int = 160
    tts_volume: float = 0.9
    
    # Visualization settings
    canvas_size: Tuple[int, int] = (640, 480)
    viz_fps: int = 30
    line_thickness: int = 2
    joint_radius: int = 4
    
    # General settings
    verbose: bool = False
    enable_tts: bool = False
    enable_viz: bool = True
    
    @classmethod
    def from_args(cls, args):
        """Create configuration from command-line arguments."""
        return cls(
            pose_model=getattr(args, 'pose_model', cls.pose_model),
            target_fps=getattr(args, 'target_fps', cls.target_fps),
            max_dim=getattr(args, 'max_dim', cls.max_dim),
            tts_rate=getattr(args, 'tts_rate', cls.tts_rate),
            tts_volume=getattr(args, 'tts_volume', cls.tts_volume),
            canvas_size=(getattr(args, 'width', cls.canvas_size[0]), 
                        getattr(args, 'height', cls.canvas_size[1])),
            viz_fps=getattr(args, 'viz_fps', cls.viz_fps),
            verbose=getattr(args, 'verbose', cls.verbose),
            enable_tts=not getattr(args, 'no_tts', False),
            enable_viz=not getattr(args, 'no_viz', False),
        )
