"""Retrieve exactly four public artifacts; leave auth/task/trace private on server."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
remote='/data/researcher/jev-defense-four-gpu-20261106/environment-transport-preflight-1793976484270917404/public'
dest=ROOT/'environment-transport-evidence-1793976484270917404';dest.mkdir(exist_ok=False)
names=['receipt.json','initial.png','same-live-recapture.png','seal.json']
cmd=['D:/Git/usr/bin/scp.exe','-F','C:/Users/researcher/.ssh/config']+['4090:'+remote+'/'+name for name in names]+[str(dest)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
assert r.returncode==0,r.stderr
assert {p.name for p in dest.iterdir()}==set(names)
mapping=json.loads((dest/'seal.json').read_bytes())
assert set(mapping)==set(names)-{'seal.json'}
for name,digest in mapping.items():assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
receipt=json.loads((dest/'receipt.json').read_bytes())
assert receipt['phase']=='environment_transport_preflight_complete'
assert all(receipt.get(k)is True for k in ['same_live_recapture_passed','native_parser_passed','official_scorer_transport_passed','no_site_reset'])
assert receipt['scorer_calls']==1 and receipt['scorer_transport_test']['observed_reward']==0.0
assert receipt['model_calls']==receipt['task_actions']==0
print(json.dumps({'root':str(dest),'receipt_sha256':hashlib.sha256((dest/'receipt.json').read_bytes()).hexdigest(),
    'scorer_test_calls':1,'initial_transport_reward':0.0,'new_model_calls':0,'task_agent_actions':0,'private_files_pulled':0}))
