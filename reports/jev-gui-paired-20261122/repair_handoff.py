"""New native-action compatibility work; all v1 terminals remain immutable."""
import json
import sys
from pathlib import Path

import control
from prepare import HERE, read, save, sha

REPAIR = HERE / 'action-envelope-repair'


def configure():
    control.POINTER = read(HERE / 'frozen-current.json')
    control.ROOT = Path(control.POINTER['root'])
    control.PACKAGE = Path(control.POINTER['runtime'])
    assert sha(control.PACKAGE / 'manifest.json') == control.POINTER['manifest_sha256']
    control.MANIFEST = read(control.PACKAGE / 'manifest.json')
    REPAIR.mkdir(exist_ok=True)


def old(host, code, label, timeout=40):
    return control.remote(host, control.prefix(host) + code, label, timeout=timeout)


def capture_failures():
    dest = REPAIR / 'actual-early-failures.json'
    assert not dest.exists()
    gui = old('4090', r'''
import hashlib,json,sys
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from gate_core import canonical,digest
assert sha(p/'manifest.json')==EXPECTED
plan=json.loads((p/'plan.json').read_bytes())
out=[]
for spec in plan['queue'][:20]:
 q,=(p/'batch/runs'/spec['run_id']).glob('attempt-*');term=q/'terminal.json';seal=json.loads((q/'seal.json').read_bytes())
 assert sha(term)==seal['terminal.json']and sha(q/'controller/events.jsonl')==seal['controller/events.jsonl']
 t=json.loads(term.read_bytes());assert t['run']==spec and t['actor_calls']==1 and t['environment_actions']==0 and not t['injection_fired']
 assert t['outcome']=='native_contract_failure'and t['official_reward']==0 and not t['infrastructure_failure']
 head='0'*64;events=[]
 for idx,line in enumerate((q/'controller/events.jsonl').read_bytes().splitlines()):
  e=json.loads(line);h=e.pop('sha256');assert e['seq']==idx and e['previous']==head and digest(canonical(e))==h
  head=h;events.append(e)
 failure,=[e['data']for e in events if e['kind']=='native_actor_or_parser_failure']
 reply,=[e['data']for e in events if e['kind']=='actual_actor_reply']
 assert not failure['executed'] and failure['message']=='Expected exactly one action JSON block'
 out.append({'run_id':spec['run_id'],'task_id':spec['task_id'],'request_id':reply['request_id'],'reply_sha256':reply['text_sha256'],
  'terminal_sha256':seal['terminal.json'],'journal_sha256':seal['controller/events.jsonl'],'official_score':0})
print(json.dumps(out))
''', 'seal-action-envelope-early-GUI-failures')
    model = old('3090', f'GUI={gui["result"]!r}\n' + r'''
import hashlib,json,sys
from pathlib import Path
p=Path(ROOT);out=Path(OUTPUT)/'primary';sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from gate_core import canonical,digest
assert sha(p/'manifest.json')==EXPECTED
end={}
head='0'*64
for idx,line in enumerate((out/'journal/events.jsonl').read_bytes().split(b'\n')[:-1]):
 e=json.loads(line);h=e.pop('sha256');assert e['seq']==idx and e['previous']==head and digest(canonical(e))==h
 head=h
 if e['kind']=='run_end':end[e['data']['run_id']]=e['data']['terminal_sha256']
replies={};joined=[]
for n,g in enumerate(GUI,1):
 q=out/'requests'/f'{n:05}';seal=json.loads((q/'seal.json').read_bytes()); raw=(q/'wire-request.bin').read_bytes()
 w=json.loads(raw);reply=json.loads((q/'response.json').read_bytes());gen=json.loads((q/'actual-generation.json').read_bytes())
 for name in ['wire-request.bin','response.json','actual-generation.json','first-forward.json']:assert sha(q/name)==seal[name]
 assert w['run_id']==g['run_id'] and w['decision_index']==1 and end[g['run_id']]==g['terminal_sha256']
 assert reply['request_id']==w['request_id']==g['request_id'] and reply['request_sha256']==digest(raw)
 assert gen['natural_EOS']and gen['actual_forward_calls']>0
 h=digest(reply['text'].encode());assert h==g['reply_sha256']
 if h not in replies:replies[h]={'task_id':g['task_id'],'text':reply['text']}
 joined.append({**g,'model_seal_sha256':sha(q/'seal.json')})
assert len(replies)==2
print(json.dumps({'joined':joined,'exact_distinct_replies_by_sha256':replies,'new_calls':0}))
''', 'join-action-envelope-actual-v1-replies')
    save(dest, {'original_manifest_sha256': control.POINTER['manifest_sha256'], 'GUI': gui, 'model': model})
    print(json.dumps({'path': str(dest), 'sha256': sha(dest), 'terminal_failures': len(gui['result']),
                      'distinct_actual_replies': len(model['result']['exact_distinct_replies_by_sha256'])}))


def drain():
    dest = REPAIR / 'drain-armed.json'
    assert not dest.exists()
    source = (HERE / 'drain_after_pair.py').read_text(encoding='utf-8')
    result = old('4090', f'WATCH_SOURCE={source!r}\n' + r'''
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha,identity
assert os.getuid()==1015 and sha(p/'manifest.json')==EXPECTED and not(p/'STOP').exists()
manifest=json.loads((p/'manifest.json').read_bytes());assert sha(p/'plan.json')==manifest['plan_sha256']
queue=json.loads((p/'plan.json').read_bytes())['queue'];started={r.name for r in (p/'batch/runs').iterdir()if r.is_dir()}
n=len(started);assert 0<n<len(queue)and started=={row['run_id']for row in queue[:n]}
root=p.parent/'action-envelope-repair-drain';root.mkdir(mode=0o700,exist_ok=False)
script=root/'drain_after_pair.py';script.write_text(WATCH_SOURCE);compile(WATCH_SOURCE,str(script),'exec')
def job_identity(name):
 row=json.loads((p/'control'/name).read_bytes());current=identity(row['pid'])
 assert current['state']not in ('Z','X') and current['uid']==1015 and all(row[k]==current[k]for k in ('uid','command','start_ticks'))
 return current
outer=job_identity('process.json');runner=job_identity('runner-process.json')
prefix=n+(1 if n%2 else 0)
assert prefix<len(queue)and (n%2 or not list((p/'batch/runs'/queue[prefix-1]['run_id']).glob('attempt-*/terminal.json')))
job={'runtime':ROOT,'manifest':EXPECTED,'plan_sha256':manifest['plan_sha256'],'prefix':prefix,
 'target':queue[prefix-1],'outer':outer,'runner':runner,'site_lock':'/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock'}
(root/'job.json').write_text(json.dumps(job))
argv=[sys.executable,'-B','-u',str(script),str(root/'job.json')]
with(root/'watch.log').open('xb')as f:
 child=subprocess.Popen(argv,cwd=root,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
launch={'root':str(root),'script_sha256':sha(script),'job':job,'identity':identity(child.pid),'argv':argv,'armed_only':True}
with(root/'launch.json').open('x')as f:json.dump(launch,f)
print(json.dumps(launch))
''', 'arm-current-pair-natural-drain')
    save(dest, result)
    print(json.dumps({'receipt': str(dest), 'remote': result['result']['root'], 'target_prefix': result['result']['job']['prefix'],
                      'target_run': result['result']['job']['target']['run_id']}))


if __name__ == '__main__':
    configure()
    {'capture': capture_failures, 'drain': drain}[sys.argv[1]]()
