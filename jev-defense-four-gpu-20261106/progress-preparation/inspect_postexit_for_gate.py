import json
from pathlib import Path
base=Path('/home/researcher/jev-defense-four-gpu-20261106/independent-service-postexit/1793983761231132390')
print(json.dumps({'receipt':json.loads((base/'receipt.json').read_bytes()),
 'manifest_keys':list(json.loads((base/'service-original-sha256.json').read_bytes()))[:12]}))
