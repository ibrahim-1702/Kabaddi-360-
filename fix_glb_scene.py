"""
Patches kabaddi_app/assets/models/HandTouch_P2.glb by injecting
"scene": 0 and "scenes": [{"nodes": [0]}] into the GLB JSON chunk.
"""

import struct
import json
import shutil
import os

GLB_PATH = r"kabaddi_app\assets\models\HandTouch_P2.glb"
BACKUP_PATH = GLB_PATH + ".bak"

with open(GLB_PATH, "rb") as f:
    magic = f.read(4)
    assert magic == b"glTF", "Not a valid GLB file"
    version = struct.unpack("<I", f.read(4))[0]
    f.read(4)  # old total length, will recompute

    chunk0_len = struct.unpack("<I", f.read(4))[0]
    chunk0_type = f.read(4)
    assert chunk0_type == b"JSON", "First chunk is not JSON"
    json_bytes = f.read(chunk0_len)

    rest = f.read()  # BIN chunk + anything after

gltf = json.loads(json_bytes.decode("utf-8"))

if "scene" in gltf and "scenes" in gltf:
    print("File already has scene/scenes — no patch needed.")
    exit(0)

gltf["scene"] = 0
gltf["scenes"] = [{"nodes": [0]}]

new_json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")

# GLB chunk lengths must be 4-byte aligned
padding = (4 - len(new_json_bytes) % 4) % 4
new_json_bytes += b" " * padding  # space is valid JSON whitespace

new_total_length = 12 + 8 + len(new_json_bytes) + len(rest)

shutil.copy2(GLB_PATH, BACKUP_PATH)
print(f"Backup saved: {BACKUP_PATH}")

with open(GLB_PATH, "wb") as f:
    f.write(b"glTF")
    f.write(struct.pack("<I", version))
    f.write(struct.pack("<I", new_total_length))
    f.write(struct.pack("<I", len(new_json_bytes)))
    f.write(b"JSON")
    f.write(new_json_bytes)
    f.write(rest)

print(f"Patched: {GLB_PATH}")
print(f"New total size: {new_total_length} bytes")
