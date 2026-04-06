import struct, json, os

path = r'kabaddi_app\assets\models\HandTouch_P2.glb'
size = os.path.getsize(path)
print(f"File size: {size} bytes")

with open(path, 'rb') as f:
    magic = f.read(4)
    version = struct.unpack('<I', f.read(4))[0]
    length = struct.unpack('<I', f.read(4))[0]
    print(f"Magic: {magic}, Version: {version}, Declared length: {length}")

    chunk0_len = struct.unpack('<I', f.read(4))[0]
    chunk0_type = f.read(4)
    print(f"Chunk0 type: {chunk0_type}, length: {chunk0_len}")

    json_bytes = f.read(chunk0_len)
    try:
        gltf = json.loads(json_bytes.decode('utf-8'))
        print(f"Keys: {list(gltf.keys())}")
        print(f"scene field: {gltf.get('scene', 'MISSING')}")
        print(f"scenes: {gltf.get('scenes', 'MISSING')}")
        print(f"nodes count: {len(gltf.get('nodes', []))}")
        print(f"meshes count: {len(gltf.get('meshes', []))}")
        print(f"animations count: {len(gltf.get('animations', []))}")
    except Exception as e:
        print(f"JSON parse error: {e}")
        print(f"Raw start: {json_bytes[:200]}")
