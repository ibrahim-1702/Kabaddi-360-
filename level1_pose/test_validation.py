"""
Test input validation for level1_cleaning.py

Tests validation logic added in Phase 3.
"""

import numpy as np
import sys
sys.path.insert(0, '.')
from level1_cleaning import clean_level1_poses


def test_valid_input():
    """Valid input should pass through successfully."""
    print("Test 1: Valid input (100, 17, 2)...")
    poses = np.random.rand(100, 17, 2)
    result = clean_level1_poses(poses)
    assert result.shape == (100, 17, 2)
    print("  [PASS] Valid input processed successfully\n")


def test_invalid_type():
    """Non-array input should raise TypeError."""
    print("Test 2: Invalid type (list instead of ndarray)...")
    try:
        clean_level1_poses([[1, 2], [3, 4]])
        print("  [FAIL]: Should have raised TypeError\n")
    except TypeError as e:
        print(f"  [PASS]: {e}\n")


def test_invalid_ndim():
    """Wrong number of dimensions should raise ValueError."""
    print("Test 3: Invalid dimensions (2D instead of 3D)...")
    poses = np.random.rand(100, 34)  # 2D instead of 3D
    try:
        clean_level1_poses(poses)
        print("  [FAIL]: Should have raised ValueError\n")
    except ValueError as e:
        print(f"  [PASS]: {e}\n")


def test_invalid_coords():
    """Last dimension != 2 should raise ValueError."""
    print("Test 4: Invalid coordinates (3D coords instead of 2D)...")
    poses = np.random.rand(100, 17, 3)  # 3D coords
    try:
        clean_level1_poses(poses)
        print("  [FAIL]: Should have raised ValueError\n")
    except ValueError as e:
        print(f"  [PASS]: {e}\n")


def test_invalid_joints():
    """Wrong joint count should raise ValueError."""
    print("Test 5: Invalid joint count (33 instead of 17)...")
    poses = np.random.rand(100, 33, 2)  # MediaPipe 33 instead of COCO-17
    try:
        clean_level1_poses(poses)
        print("  [FAIL]: Should have raised ValueError\n")
    except ValueError as e:
        print(f"  [PASS]: {e}\n")


def test_empty_sequence():
    """Empty sequence should raise ValueError."""
    print("Test 6: Empty sequence (0 frames)...")
    poses = np.random.rand(0, 17, 2)
    try:
        clean_level1_poses(poses)
        print("  [FAIL]: Should have raised ValueError\n")
    except ValueError as e:
        print(f"  [PASS]: {e}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Input Validation Tests - Level-1 Pose Cleaning")
    print("=" * 60)
    print()
    
    test_valid_input()
    test_invalid_type()
    test_invalid_ndim()
    test_invalid_coords()
    test_invalid_joints()
    test_empty_sequence()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
