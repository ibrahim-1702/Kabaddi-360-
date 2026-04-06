"""
Patches kabaddi_app/assets/models/HandTouch_P2.glb root node scale
from centimeters to meters (0.01, 0.01, 0.01).
"""

import struct, json, shutil

GLB_PATH = r"kabaddi_app\assets\models\HandTouch_P2.glb"
BACKUP_PATH = GLB_PATH + ".scale.bak"

with open(GLB_PATH, "rb") as f:
    magic = f.read(4)
    assert magic == b"glTF"
    version = struct.unpack("<I", f.read(4))[0]
    f.read(4)  # old total length

    chunk0_len = struct.unpack("<I", f.read(4))[0]
    chunk0_type = f.read(4)
    assert chunk0_type == b"JSON"
    json_bytes = f.read(chunk0_len)
    rest = f.read()

gltf = json.loads(json_bytes.decode("utf-8"))

# Patch root node (node 0) scale to convert cm → meters
gltf["nodes"][0]["scale"] = [0.01, 0.01, 0.01]

new_json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
padding = (4 - len(new_json_bytes) % 4) % 4
new_json_bytes += b" " * padding

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

print(f"Patched root node scale → [0.01, 0.01, 0.01]")
print(f"New total size: {new_total_length} bytes")
