"""Verify true worker/lock or collect a stable post-exit terminal, without inference."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'native-direction-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def inspect():
    completed=PREP/'completed-current.json'
    if completed.exists():
        row=json.loads(completed.read_bytes());review=Path(row['directory'])/'review.json'
        assert sha(review.read_bytes())==row['review_sha256']
        return {'terminal':True,'already_finalized':True,'completed_receipt':str(completed),'calls':row['calls'],'root':row['remote_root'],'do_not_poll_exited_pid':True}
    launch=json.loads((PREP/'launch-current.json').read_bytes())
    code=r'''
import base64,hashlib,io,json,os,zipfile
from pathlib import Path
r=Path(L['root']);p=Path('/proc')/str(L['pid']);process=None
if p.exists():
 command=[s.decode()for s in(p/'cmdline').read_bytes().split(b'\0')if s]
 assert command==L['command'] and p.stat().st_uid==1015
 held=[{'target':os.readlink(str(p/'fd'/f.name)),'fdinfo':f.read_text()}for f in(p/'fdinfo').iterdir()if 'FLOCK'in f.read_text()]
 assert any(x['target'].endswith('/native-direction-development.lock')for x in held)
 process={'uid':1015,'command':command,'held_locks':held}
status=json.loads((r/'status.json').read_bytes())if(r/'status.json').exists()else None
row={'root':str(r),'process':process,'status':status,'log_tail':(r/'worker.log').read_text()[-3500:]}
if process is None:
 files={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in r.rglob('*')if f.is_file()}
 if(r/'terminal-sha256.json').exists():
  manifest=json.loads((r/'terminal-sha256.json').read_bytes())
  for n,h in manifest.items():assert files[n]==h,n
  row['terminal_manifest_sha256']=files['terminal-sha256.json']
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
  for n in files:z.writestr(n,(r/n).read_bytes())
 row.update(postexit_sha256=files,zip=base64.b64encode(b.getvalue()).decode())
print(json.dumps(row))
'''
    row=json.loads(remote('L='+repr(launch)+'\n'+code,host='4090',timeout=90))
    if 'zip'in row:
        out=PREP/('terminal-'+str(time.time_ns()));out.mkdir()
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
            for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
            z.extractall(out)
        for n,h in row['postexit_sha256'].items():assert sha((out/n).read_bytes())==h,n
        chains=[]
        for f in sorted((out/'journal').glob('*/events.jsonl')):
            head='0'*64;count=0
            for line in f.read_text(encoding='utf-8').splitlines():
                event=json.loads(line);got=event.pop('sha256');assert event['previous']==head and sha(canon(event))==got
                assert event['seq']==count;head=got;count+=1
            chains.append({'case':f.parent.name,'events':count,'head':head})
        row.update(collected_root=str(out),event_chains=chains)
        (out/'postexit-evidence.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    snapshot=PREP/('inspection-'+str(time.time_ns())+'.json')
    snapshot.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    pointer={'receipt':str(snapshot),'sha256':sha(snapshot.read_bytes()),'root':row['root'],'process':row['process'],'status':row['status'],'terminal':row['process']is None}
    for n in ['collected_root','terminal_manifest_sha256','event_chains']: 
        if n in row:pointer[n]=row[n]
    (PREP/'inspection-current.json').write_text(json.dumps(pointer,indent=2))
    return pointer
if __name__=='__main__':print(json.dumps(inspect()))
