import json,shutil,time
from pathlib import Path
from manage import HERE,remote,save,sha
failed=HERE/'operations/1794497707797968700-independent-audit'
dest=HERE/('audit-environment-failure-preservation-'+str(time.time_ns()));dest.mkdir()
for p in [HERE/'audit_remote.py',HERE/'manage.py',failed/'source.py',failed/'stdout.txt',failed/'stderr.txt',failed/'receipt.json']:
 name=('failed-operation-'+p.name) if p.parent==failed else p.name
 shutil.copyfile(p,dest/name)
code=r'''
from pathlib import Path
import hashlib,json,time
r=Path('/home/researcher/jev-defense-four-gpu-20261106/binary-gate-comparison-20261112')
rows=[]
for d in r.glob('independent-audit-*'):
 if d.is_dir() and not (d/'audit.json').exists():
  rows.append({'path':str(d),'files':{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()}})
print(json.dumps({'unfinished_audits':rows,'terminal_sha256':hashlib.sha256((r/'terminal.json').read_bytes()).hexdigest(),'terminal_seal_sha256':hashlib.sha256((r/'terminal-seal.json').read_bytes()).hexdigest(),'failure':'Flash audit environment lacks pydantic needed to import NeoHorse schema','planned_repair':'Use existing NeoHorse Python only for CPU audit; audit source and all inference workers/inputs/results unchanged','new_model_calls':0,'time':time.time()}))
'''
out,op=remote(code,'preserve-audit-environment-failure');save(dest/'remote-preservation.json',json.loads(out))
save(dest/'seal.json',{p.name:sha(p) for p in dest.iterdir() if p.is_file()})
save(HERE/'audit-environment-repair.json',{'preservation':str(dest),'operation':str(op),'prior_python':'flash-preparation/env-flash-01/bin/python','new_python':'/home/researcher/jev-defense-local-20261102/env-neohorse/bin/python','algorithm_change':False,'new_model_calls':0,'time':time.time()})
print(json.dumps({'preserved':str(dest),'model_calls_unchanged':54}))
