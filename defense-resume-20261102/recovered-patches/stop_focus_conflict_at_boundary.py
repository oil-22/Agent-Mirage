"""Request native boundary exit for this verified owned, already semantically failed development run."""
import hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development'
assert not(PREP/'boundary-stop-current.json').exists()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
code=r'''
import hashlib,json,os,signal,time
from pathlib import Path
r=Path(L['root']);p=Path('/proc')/str(L['pid']);assert p.exists()and p.stat().st_uid==1015
command=[s.decode()for s in(p/'cmdline').read_bytes().split(b'\0')if s];assert command==L['command']
held=[]
for f in(p/'fdinfo').iterdir():
 try:
  info=f.read_text()
  if 'FLOCK'in info:held.append({'target':os.readlink(str(p/'fd'/f.name)),'fdinfo':info})
 except FileNotFoundError:pass
assert all(any(x['target']==old['target']for x in held)for old in L['held_locks'])
a=next(r.glob('runs/*/attempt-*'));events=[json.loads(x)for x in(a/'events.jsonl').read_text().splitlines()];lookup={e['seq']:e for e in events}
assert lookup[305]['kind']=='verdict'and lookup[316]['kind']=='candidate'
assert lookup[326]['kind']=='decision_accepted'and lookup[327]['kind']=='action_executed'
assert lookup[326]['data']['candidate']==lookup[316]['data']['text']and lookup[327]['data']['proposal']['name']=='back'
source=r/'boundary-stop-failure-prefix.json';assert not source.exists()
row={'time':time.time(),'uid':1015,'actual_command':command,'held_locks':held,'source_events':[lookup[n]for n in [305,316,324,326,327]],'reason':'Confirmed false minimum/equal-price refusal followed by accepted/executed wrong price-object history. Continue repair in a new condition; do not spend more inference on this known failed development condition.','not_a_completed_full_trial':True,'not_an_official_zero':True,'monitor_remains':'ACTIVE','signal':'SIGUSR1','native_handler':'finish current decision, snapshot final state/trajectory, close owned browser, exit at decision boundary; no service kill'}
source.write_text(json.dumps(row,ensure_ascii=False,indent=2))
row['source_receipt_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
os.kill(L['pid'],signal.SIGUSR1)
row['signal_sent']=True;print(json.dumps(row))
'''
row=json.loads(remote('L='+repr(launch)+'\n'+code,host='4090',timeout=40));out=PREP/('boundary-stop-'+str(time.time_ns())+'.json');out.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'boundary-stop-current.json').write_text(json.dumps({'receipt':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'root':launch['root'],'signal_sent':True,'waiting_for_native_boundary_exit':True,'not_a_completed_full_trial':True,'monitor':'ACTIVE'},indent=2))
print(json.dumps({'root':launch['root'],'signal_sent':True,'native_boundary_exit_requested':True,'service_untouched':True,'monitor':'ACTIVE'}))
