"""Seal exact zero-call startup failure and released resources before repair."""
import base64
import json
import time
from pathlib import Path
from remote_util import HERE, remote, save, sha


def main():
    assert not (HERE / 'startup-failure-preservation-current.json').exists()
    pointer = json.loads((HERE / 'preparation-current.json').read_bytes()); package = Path(pointer['package']); m = json.loads((package / 'manifest.json').read_bytes())
    code = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\n' + r'''
import base64,hashlib,json,os,time
from pathlib import Path
p=Path(P);o=Path(O)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
seals=json.loads((o/'postexit-seal.json').read_bytes())
for n,h in seals.items():assert sha((p if n.startswith('flash/service/')else o)/n)==h,n
status=json.loads((o/'primary/status.json').read_bytes());assert status['phase']=='technical_failure'and status['done']==status['attempted_actor_calls']==status['complete_actor_replies']==0
assert not list((o/'primary/requests').iterdir())and not list((p/'flash/service/requests').iterdir())
assert 'AssertionError: flash/gate-contract.json'in(o/'primary.log').read_text()
released=json.loads((o/'released.json').read_bytes());assert released['fresh_lease_locks_closed']==17
lease=json.loads((o/'lease.json').read_bytes());processes=[]
for saved in[lease['holder'],json.loads((o/'primary/process.json').read_bytes()),json.loads((p/'flash/service/process.json').read_bytes())]:
 proc=Path('/proc',str(saved['pid']));actual=None
 if proc.exists():
  s=(proc/'stat').read_text().rsplit(')',1)[1].split();actual={'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]};assert actual['state']in['Z','X']or any(actual[k]!=saved[k]for k in['uid','command','start_ticks'])
 processes.append({'saved':saved,'actual':actual})
kernel=Path('/proc/locks').read_text().splitlines();locks=[]
for record in lease['lock_records']:
 st=Path(record['path']).stat();assert st.st_ino==record['inode'];key=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino);matches=[]
 for line in kernel:
  for item in line.split():
   fields=item.split(':')
   if len(fields)!=3:continue
   try:value=(int(fields[0],16),int(fields[1],16),int(fields[2]))
   except ValueError:continue
   if value==key:matches.append(line)
 assert not matches;locks.append({'path':record['path'],'inode':st.st_ino,'kernel_locks':matches})
files={str(q):{'sha256':sha(q),'bytes':q.stat().st_size,'base64':base64.b64encode(q.read_bytes()).decode()}for folder in[o,p/'flash/service']for q in folder.rglob('*')if q.is_file()}
print(json.dumps({'status':status,'processes':processes,'locks':locks,'all_original_exited_and_17_locks_released':True,'actual_new_actor_Flash_GUI_calls':0,'files':files,'eight_GPU_seconds':8*(released['time']-lease['created']),'not_semantic_zero':True}))
'''
    raw, op = remote('3090', code, 'preserve-zero-call-current-contract-binding-startup-failure', timeout=90)
    value = json.loads(raw); root = HERE / ('startup-failure-preservation-' + str(time.time_ns())); root.mkdir()
    rows = {}
    for remote_path, data in value.pop('files').items():
        prefix = 'output/' if remote_path.startswith(m['output3090'] + '/') else 'package/'
        relative = remote_path[len(m['output3090'] if prefix == 'output/' else m['package3090']) + 1:]
        dest = root / prefix / relative; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(base64.b64decode(data['base64'], validate=True)); assert sha(dest) == data['sha256']
        rows[remote_path] = {'sha256': data['sha256'], 'local': dest.relative_to(root).as_posix()}
    save(root / 'result.json', {'operation': str(op), **value, 'files': rows, 'source_preparation': pointer, 'all_source_files_already_sealed_locally': True, 'repair_planned': 'retain historical capacity proof and old contract; separately bind active audited new contract before strict installation; no prompt/model/history/budget/algorithm change'})
    gui_raw, gui_op = remote('4090', 'from pathlib import Path\nimport json\np=Path(' + repr(m['package4090']) + ')\nassert not any((p/n).exists()for n in["batch","control","background"])\nprint(json.dumps({"GUI_unstarted":True,"old_source_manifest_sha256":' + repr(pointer['manifest_sha256']) + '}))', 'verify-new-GUI-unstarted-before-linked-startup-repair')
    save(root / 'GUI-unstarted.json', {'operation': str(gui_op), 'result': json.loads(gui_raw)})
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'startup-failure-preservation-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'preserved_files': len(rows), **value}))


if __name__ == '__main__':
    main()
