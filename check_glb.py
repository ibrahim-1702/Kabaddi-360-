import struct, json, os

path = r'samples\3D\Techniques\HandTouch\USE\HandTouch_P2.glb'
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
    gltf = json.loads(json_bytes.decode('utf-8'))

    print(f"Keys in GLTF JSON: {list(gltf.keys())}")
    print(f"scene field: {gltf.get('scene', 'MISSING')}")
    print(f"scenes: {gltf.get('scenes', 'MISSING')}")
    print(f"nodes count: {len(gltf.get('nodes', []))}")
    print(f"meshes count: {len(gltf.get('meshes', []))}")
    print(f"animations count: {len(gltf.get('animations', []))}")
