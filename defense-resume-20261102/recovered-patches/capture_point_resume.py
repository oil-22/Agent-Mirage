"""Once-only factual resume snapshot and separately bound retry provenance."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.9-online-resume-evidence.json';assert not out.exists()
x=json.loads((r/'v3.9.9-scroll-validation-resume.json').read_bytes())
code=r'''
import pathlib,json,time,hashlib,collections
root=pathlib.Path(X['root']);state=json.loads((root/'status.json').read_bytes());p=pathlib.Path('/proc',str(X['pid']))
assert p.exists()and p.stat().st_uid==1015
cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert X['root']in cmd and X['release']in cmd
attempt=pathlib.Path(state['attempt']);assert str(attempt)!=X['previous_failed_attempt']and state['defense_version']=='evidence-v3.9.9-bounded-point-evidence-recovery-20261027'
raw=(attempt/'events.jsonl').read_bytes();events=[]
for line in raw.splitlines():
 try:events.append(json.loads(line))
 except json.JSONDecodeError:break
raw=b'\n'.join(json.dumps(e,ensure_ascii=False).encode()for e in events)+b'\n'
counts=dict(collections.Counter(e['kind']for e in events));assert counts.get('candidate',0)>=2 and counts.get('action_executed',0)>=1 and counts.get('verifier_raw',0)>=1
ledger=next(e['data']for e in events if e['kind']=='private_delivery_ledger'and e['data']['fired'])
actor=next(e['data']for e in events if e['kind']=='actor_request'and e['data']['public']['observation_id'].startswith('%03d-'%ledger['step']))
assert len(actor['public']['images'])==1 and actor['public']['images'][0]['sha256']==ledger['delivered_sha256']
assert any(e['kind']=='candidate'and e['data']['observation_id']==actor['public']['observation_id']for e in events)
old=pathlib.Path(X['previous_failed_attempt']);assert not(old/'complete.json').exists()
link={'time':time.time(),'new_attempt':str(attempt),'previous_unfinished_technical_attempt':str(old),'previous_events_sha256':hashlib.sha256((old/'events.jsonl').read_bytes()).hexdigest(),'failure_preservation':X['failure_preservation'],'new_release':X['release'],'core_sha256':X['core_sha256'],'resume_manifest_sha256':hashlib.sha256((root/'v3.9.9-resume-manifest.json').read_bytes()).hexdigest(),'original20_source_root':X['source_root'],'semantic_mirage':None,'scope':'New version attempt only; preceding failure preserved, no terminal overwritten.'}
with(attempt/'retry-origin-v3.9.9.json').open('x')as f:json.dump(link,f,indent=2)
evidence=root/'resume-evidence'/('v3.9.9-'+str(time.time_ns()));evidence.mkdir(parents=True)
(evidence/'events-prefix.jsonl').write_bytes(raw);(evidence/'state.json').write_bytes((root/'status.json').read_bytes());(evidence/'worker-log-prefix.txt').write_bytes(pathlib.Path(X['log']).read_bytes());(evidence/'retry-origin.json').write_bytes((attempt/'retry-origin-v3.9.9.json').read_bytes())
bindings={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in evidence.iterdir()if p.is_file()};(evidence/'manifest.json').write_text(json.dumps(bindings,indent=2))
print(json.dumps({'time':time.time(),'evidence_root':str(evidence),'state':state,'actual_uid':p.stat().st_uid,'actual_command':cmd,'counts':counts,'injection_actually_delivered_and_replied':True,'delivery':ledger,'delivered_actor_observation':actor['public']['observation_id'],'retry_origin':link,'snapshot_sha256':bindings,'full_terminals':len(list((root/'runs').glob('*/complete.json'))),'semantic_mirage_label':None}))
'''
d=json.loads(remote('X='+repr(x)+'\n'+code,host='4090',timeout=45));out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k not in ['snapshot_sha256','retry_origin']},ensure_ascii=True))
