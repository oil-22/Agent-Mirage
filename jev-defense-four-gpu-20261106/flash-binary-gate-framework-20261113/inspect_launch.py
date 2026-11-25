from manage import remote,REMOTE
code=r'''
import json,os
from pathlib import Path
root=Path(ROOT);base=root.parent;lease=base/'resource-attempt-20261106-01'
out={}
for p in [lease/'holder.log',lease/'failure.json',lease/'commands/flash-binary-gate-framework-20261113.claimed',lease/'flash-binary-gate-framework-20261113-launch.json',lease/'flash-binary-gate-framework-20261113.log']:
 if p.exists():out[str(p)]=p.read_text()[-7000:]
out['new_files']=[str(p.relative_to(root))for p in root.rglob('*')if p.is_file()and 'token'not in p.name]
print(json.dumps(out))
'''.replace('ROOT',repr(REMOTE))
print(remote(code,'inspect-once-only-launch')[0])
