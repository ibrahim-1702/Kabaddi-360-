"""
Pipeline Logger

Centralized logging for AR-Based Kabaddi Ghost Trainer pipeline.
"""

import sys
import time
from typing import Optional, Tuple
from datetime import datetime


class PipelineLogger:
    """Centralized logging with verbosity control."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize logger.
        
        Args:
            verbose: Enable debug-level logging
        """
        self.verbose = verbose
        self.stage_timers = {}
        
    def _log(self, level: str, message: str, indent: int = 0):
        """Internal logging function."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        indent_str = "  " * indent
        print(f"[{timestamp}] {indent_str}{message}")
        sys.stdout.flush()
    
    def info(self, message: str, indent: int = 0):
        """Log info-level message."""
        self._log("INFO", message, indent)
    
    def debug(self, message: str, indent: int = 0):
        """Log debug-level message (only if verbose enabled)."""
        if self.verbose:
            self._log("DEBUG", f"[DEBUG] {message}", indent)
    
    def error(self, message: str, indent: int = 0):
        """Log error-level message."""
        self._log("ERROR", f"[ERROR] {message}", indent)
    
    def success(self, message: str, indent: int = 0):
        """Log success message."""
        self._log("SUCCESS", f"[OK] {message}", indent)
    
    def warning(self, message: str, indent: int = 0):
        """Log warning message."""
        self._log("WARNING", f"[WARNING] {message}", indent)
    
    def log_stage_start(self, stage_num: int, total_stages: int, stage_name: str):
        """Log the start of a pipeline stage."""
        self.info("")
        self.info("=" * 70)
        self.info(f"[STAGE {stage_num}/{total_stages}] {stage_name}")
        self.info("=" * 70)
        self.stage_timers[stage_name] = time.time()
    
    def log_stage_complete(self, stage_name: str, output_info: Optional[str] = None):
        """Log the completion of a pipeline stage."""
        if stage_name in self.stage_timers:
            duration = time.time() - self.stage_timers[stage_name]
            self.success(f"Stage complete in {duration:.2f}s")
            del self.stage_timers[stage_name]
        else:
            self.success("Stage complete")
        
        if output_info:
            self.info(f"  -> {output_info}", indent=1)
    
    def log_data_shape(self, name: str, shape: Tuple, expected_format: Optional[str] = None):
        """Log and validate data shape."""
        shape_str = f"{name} shape: {shape}"
        
        if expected_format:
            self.debug(f"{shape_str} (expected: {expected_format})")
        else:
            self.debug(shape_str)
    
    def log_error_detailed(self, stage: str, error: Exception, filepath: Optional[str] = None):
        """Log detailed error information."""
        self.info("")
        self.info("=" * 70)
        self.error(f"Stage: {stage}")
        
        if filepath:
            self.info(f"  File: {filepath}", indent=1)
        
        self.info(f"  Error Type: {type(error).__name__}", indent=1)
        self.info(f"  Error Message: {str(error)}", indent=1)
        self.info("=" * 70)
        self.info("")
    
    def log_input(self, label: str, value: str):
        """Log input parameter."""
        self.info(f"  -> {label}: {value}", indent=1)
    
    def log_output(self, label: str, value: str):
        """Log output information."""
        self.info(f"  [OK] {label}: {value}", indent=1)
    
    def log_skip(self, message: str):
        """Log skipped operation."""
        self.info(f"  [SKIP] {message}", indent=1)
    
    def separator(self):
        """Print separator line."""
        self.info("-" * 70)
    
    def header(self, title: str):
        """Print section header."""
        self.info("")
        self.info("=" * 70)
        self.info(title.center(70))
        self.info("=" * 70)
        self.info("")
