import struct, json

path = r'kabaddi_app\assets\models\HandTouch_P2.glb'

with open(path, 'rb') as f:
    f.read(12)  # header
    chunk0_len = struct.unpack('<I', f.read(4))[0]
    f.read(4)   # JSON type
    gltf = json.loads(f.read(chunk0_len).decode('utf-8'))

nodes = gltf.get('nodes', [])
scenes = gltf.get('scenes', [])
scene_nodes = scenes[0].get('nodes', []) if scenes else []

print(f"Scene root nodes: {scene_nodes}")
for i in scene_nodes:
    n = nodes[i]
    print(f"  Node {i} '{n.get('name','')}': translation={n.get('translation','none')} scale={n.get('scale','none')}")

# Also print all nodes with translation
print("\nAll nodes with translation:")
for i, n in enumerate(nodes):
    if 'translation' in n or 'scale' in n:
        print(f"  Node {i} '{n.get('name','')}': translation={n.get('translation','none')} scale={n.get('scale','none')}")
