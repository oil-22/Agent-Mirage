import json
from pathlib import Path
path=Path('/home/researcher/jev-defense-four-gpu-20261106/failed-gui-service-preservation/1793982653388639508/linked-evidence/primary_native_layout_receipt.json')
value=json.loads(path.read_bytes())
print(json.dumps(value))
