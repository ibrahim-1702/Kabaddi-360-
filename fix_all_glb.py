"""
Patches all GLBs in kabaddi_app/assets/models/ that are missing scene/scale.
Adds scene+scenes fields and sets root node scale to 0.01 (cm -> meters).
"""
import struct, json, shutil, glob, os

MODELS_DIR = r"kabaddi_app\assets\models"

for path in glob.glob(os.path.join(MODELS_DIR, "*.glb")):
    if path.endswith(".bak"):
        continue

    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"glTF":
            continue
        version = struct.unpack("<I", f.read(4))[0]
        f.read(4)
        chunk0_len = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # JSON type
        json_bytes = f.read(chunk0_len)
        rest = f.read()

    gltf = json.loads(json_bytes.decode("utf-8"))

    needs_scene = "scene" not in gltf or "scenes" not in gltf
    needs_scale = gltf["nodes"][0].get("scale") != [0.01, 0.01, 0.01]

    if not needs_scene and not needs_scale:
        print(f"SKIP (already patched): {os.path.basename(path)}")
        continue

    if needs_scene:
        gltf["scene"] = 0
        gltf["scenes"] = [{"nodes": [0]}]

    if needs_scale:
        gltf["nodes"][0]["scale"] = [0.01, 0.01, 0.01]

    new_json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    padding = (4 - len(new_json_bytes) % 4) % 4
    new_json_bytes += b" " * padding
    new_total = 12 + 8 + len(new_json_bytes) + len(rest)

    shutil.copy2(path, path + ".bak")

    with open(path, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<I", version))
        f.write(struct.pack("<I", new_total))
        f.write(struct.pack("<I", len(new_json_bytes)))
        f.write(b"JSON")
        f.write(new_json_bytes)
        f.write(rest)

    patches = []
    if needs_scene: patches.append("scene")
    if needs_scale: patches.append("scale=0.01")
    print(f"PATCHED [{', '.join(patches)}]: {os.path.basename(path)}")
