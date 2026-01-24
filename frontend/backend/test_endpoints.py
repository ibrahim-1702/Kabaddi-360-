"""
Simple test script to verify backend endpoints are working
Run this to test CORS and endpoint availability
"""

import requests
import json

BASE_URL = "http://localhost:5000"

print("=" * 70)
print("TESTING BACKEND ENDPOINTS")
print("=" * 70)

# Test 1: OPTIONS request (CORS preflight)
print("\n[Test 1] OPTIONS /api/analyze (CORS preflight)")
try:
    response = requests.options(f"{BASE_URL}/api/analyze")
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    if response.status_code == 200:
        print("  ✓ CORS preflight OK")
    else:
        print(f"  ✗ CORS preflight failed: {response.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 2: POST to analyze (should fail with missing params, but endpoint should respond)
print("\n[Test 2] POST /api/analyze (empty body)")
try:
    response = requests.post(
        f"{BASE_URL}/api/analyze",
        headers={"Content-Type": "application/json"},
        json={}
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    if response.status_code == 400:
        print("  ✓ Endpoint working (expects 400 for missing params)")
    else:
        print(f"  ? Unexpected status: {response.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 3: GET poses endpoint
print("\n[Test 3] GET /api/poses")
try:
    response = requests.get(f"{BASE_URL}/api/poses")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        poses = response.json()
        print(f"  ✓ Found {len(poses)} expert poses")
        for pose in poses[:3]:  # Show first 3
            print(f"    - {pose.get('name', 'Unknown')}")
    else:
        print(f"  ✗ Failed: {response.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("TESTS COMPLETE")
print("=" * 70)
print("\nIf all tests pass, backend is ready!")
print("If OPTIONS test fails → CORS issue")
print("If POST test fails → Endpoint not working")
