import struct, json, os, glob

for path in glob.glob(r'kabaddi_app\assets\models\*.glb'):
    if path.endswith('.bak'):
        continue
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            print(f"{path}: NOT a GLB")
            continue
        f.read(8)
        chunk0_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        gltf = json.loads(f.read(chunk0_len).decode('utf-8'))
    n0 = gltf['nodes'][0] if gltf.get('nodes') else {}
    hips = next((n for n in gltf.get('nodes', []) if 'hip' in n.get('name','').lower() or 'Hips' in n.get('name','')), None)
    print(f"\n{os.path.basename(path)} ({size//1024}KB)")
    print(f"  scene={gltf.get('scene','MISSING')}  scenes={'OK' if gltf.get('scenes') else 'MISSING'}")
    print(f"  node0='{n0.get('name','')}' scale={n0.get('scale','none')} translation={n0.get('translation','none')}")
    if hips:
        print(f"  hips='{hips.get('name')}' translation={hips.get('translation','none')}")
