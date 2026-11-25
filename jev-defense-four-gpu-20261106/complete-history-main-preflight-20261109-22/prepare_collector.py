"""Rebind the existing read-only collector to the new22output only."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
source=HERE.parent/'unicode-guard-real-preflight-20261109-18/collect_read_only.py'
target=HERE/'collect_read_only.py'
assert not target.exists()
text=source.read_text(encoding='utf8')
assert 'unicode-guard-real-preflight-20261109-18'in text
text=text.replace('unicode-guard-real-preflight-20261109-18',HERE.name).replace('unicode18-collect-','main22-collect-')
with target.open('x',encoding='utf8')as stream:stream.write(text)
print(json.dumps({'collector':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'no_remote_or_model_action':True}))
