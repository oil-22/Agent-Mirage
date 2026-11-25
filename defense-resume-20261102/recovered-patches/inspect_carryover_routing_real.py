"""Read-only status, actual ownership/lock/events and immutable terminal collection."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'carryover-routing-real-development';launch=json.loads((PREP/'launch.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
code='LAUNCH='+repr(launch)+'\n'+r'''
import pathlib,json,hashlib,base64,io,zipfile,time
root=pathlib.Path(LAUNCH['root']);proc=pathlib.Path('/proc')/str(LAUNCH['pid']);process=None
if proc.exists():
 assert proc.stat().st_uid==1015
 cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert str(root)in cmd and 'carryover_routing_real_preflight.py'in cmd
 lock=pathlib.Path(LAUNCH['lock']);assert str(lock)in [str(p.resolve())for p in(proc/'fd').iterdir()]
 inode=lock.stat().st_ino;lines=[x for x in pathlib.Path('/proc/locks').read_text().splitlines()if any(t.count(':')==2 and t.rsplit(':',1)[-1]==str(inode)for t in x.split())];assert lines
 process={'uid':proc.stat().st_uid,'full_command':cmd,'held_lock_lines':lines,'lock_inode':inode}
raw=(root/'journal/events.jsonl').read_bytes()if(root/'journal/events.jsonl').exists()else b'';lines=raw.splitlines();lines=lines if not raw or raw.endswith(b'\n')else lines[:-1];head='0'*64;response_calls=0
for line in lines:
 e=json.loads(line);h=e.pop('sha256');assert e['previous']==head and hashlib.sha256(json.dumps(e,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h;head=h
 if e['kind']in ['actor_response','audit_response']:response_calls+=len(e['data']['calls'])
r={'time':time.time(),'process':process,'status':json.loads((root/'status.json').read_bytes())if(root/'status.json').exists()else None,'verified_prefix_event_count':len(lines),'event_chain_head':head,'actual_response_call_count':response_calls,'terminal':False,'files':{}}
if process is None and(root/'terminal-sha256.json').exists():
 manifest=(root/'terminal-sha256.json').read_bytes()
 for n,h in json.loads(manifest).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
 r['terminal']=True;r['terminal_manifest_sha256']=hashlib.sha256(manifest).hexdigest();r['verified_terminal_files']=len(json.loads(manifest));assert not raw or raw.endswith(b'\n')
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
  for p in root.rglob('*'):
   if p.is_file():b=p.read_bytes();n=str(p.relative_to(root));z.writestr(n,b);r['files'][n]=hashlib.sha256(b).hexdigest()
 r['zip_base64']=base64.b64encode(buf.getvalue()).decode()
print(json.dumps(r))
'''
r=json.loads(remote(code,host='4090',timeout=90));zip_b64=r.pop('zip_base64',None)
if zip_b64:
 dest=Path(launch['local_root'])/'collected';dest.mkdir(exist_ok=True)
 with zipfile.ZipFile(io.BytesIO(base64.b64decode(zip_b64)))as z:
  for name in z.namelist():
   p=dest/name;data=z.read(name);assert sha(data)==r['files'][name];p.parent.mkdir(parents=True,exist_ok=True)
   if p.exists():assert p.read_bytes()==data
   else:p.write_bytes(data)
 r['collected_root']=str(dest)
snapshot=PREP/('inspection-'+str(time.time_ns())+'.json');snapshot.write_text(json.dumps(r,indent=2),encoding='utf-8');(PREP/'current.json').write_text(json.dumps({'snapshot':str(snapshot),'snapshot_sha256':sha(snapshot.read_bytes()),**r},indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items()if k not in {'files','process'}}))
