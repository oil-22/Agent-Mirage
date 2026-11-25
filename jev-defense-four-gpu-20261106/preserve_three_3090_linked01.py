"""Linked3090-only preservation; correct the actual online-state filename.

The prior4090 complete preservation is never executed again.
"""
import hashlib,importlib.util,json,time
from pathlib import Path

P=Path(__file__).with_name('preserve_three_before_stop.py')
spec=importlib.util.spec_from_file_location('sealed_parent_preservation',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.REMOTE.count("group/'state.json'")==2
m.REMOTE=m.REMOTE.replace("group/'state.json'","group/'online-state.json'")
compile(m.REMOTE,'linked3090-preservation','exec')
stamp=str(time.time_ns());out=P.parent/'three-prestop-preservation-linked3090'/stamp;out.mkdir(parents=True,exist_ok=False)
(out/'linked-source.json').write_text(json.dumps({'parent_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
 'changed_boundary':'two state filename references to actual online-state.json',
 'prior4090_complete_root':'/data/researcher/jev-defense-four-gpu-20261106/three-terminal-prestop-preservation/1794040037028433500',
 'only_host':'3090','stop_or_model_calls':0},indent=2),encoding='utf8')
print(json.dumps({'local_output':str(out),'stamp':stamp}),flush=True)
try:print(json.dumps(m.run('3090',stamp,out),ensure_ascii=False),flush=True)
finally:(out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
