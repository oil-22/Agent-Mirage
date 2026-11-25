"""Bounded prelaunch ownership/site checks; no model load, GUI action or signals."""
import argparse
import json
from pathlib import Path
import time
from orchestrate import admitted, remote, COMMON, save, sha, HERE, PACKAGE, REMOTE_PACKAGE, OUTPUT, GUIROOT


PRIMARY = r'''
import fcntl,socket
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
assert os.getuid()==1033
leasepath=base/'resource-attempt-20261106-01/lease.json'
assert sha(leasepath)==M['lease_sha256'];lease=json.loads(leasepath.read_bytes())
h=lease['holder'];actual=identity(h['pid'])
assert same_live(h)and all(str(actual[k])==str(M['expected_holder'][k])for k in['pid','uid','command','start_ticks'])
locks=[]
for row in lease['lock_records']:
 proc=Path('/proc',str(h['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(h['pid'])in info
 locks.append({'path':row['path'],'fd':row['fd'],'inode':row['inode'],'fdinfo':info})
assert len(locks)==9
cards=[]
for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
 i,u,f=[s.strip()for s in line.split(',')];cards.append({'index':int(i),'uuid':u,'free_MiB':int(f)})
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
 if not line.strip():continue
 u,p,f=[s.strip()for s in line.split(',')]
 try:actual_process=identity(int(p))
 except(OSError,UnicodeError)as exc:actual_process={'unreadable':str(exc)}
 compute.append({'uuid':u,'used_MiB':f,'actual':actual_process})
targets={r['uuid']for r in lease['gpu']}
assert {r['index']for r in lease['gpu']}=={4,5,6,7}
for row in lease['gpu']:
 card=next(c for c in cards if c['index']==row['index'])
 assert card['uuid']==row['uuid']and card['free_MiB']>=23000
assert not any(r['uuid']in targets for r in compute),'External compute on the task cards; do not preempt'
with Path(lease['inference_lock']).open('r+')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
with socket.socket()as s:s.bind(('192.0.2.11',19143))
ram=int(next(line.split()[1]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')))*1024
assert ram>=64*1024**3
storage=Path(OUTPUT).parent;assert storage.resolve()==storage and storage.stat().st_uid==1033
v=os.statvfs(storage);available=v.f_bavail*v.f_frsize
assert available>=1024**4 and storage.stat().st_dev!=Path('/home/researcher').stat().st_dev
assert not Path(OUTPUT).exists()and not Path(PACKAGE).exists(),'New namespace already exists; inspect it before any action'
previous=[]
for name in['prefill-scheduled-full-history-gui-20261109-32','remaining-full-history-gui-20261110-33','remaining29-full-history-gui-20261110-37']:
 old=(base if name=='prefill-scheduled-full-history-gui-20261109-32'else storage)/name
 for n in['launcher-process.json','worker/process.json']:
  if(old/n).is_file():
   record=json.loads((old/n).read_bytes());assert not same_live(record)
   previous.append({'namespace':name,'record':record,'actual':identity(record['pid'])})
 assert(old/'exit.json').is_file()and(old/'worker/terminal.json').is_file()
commands=base/'resource-attempt-20261106-01/commands'
assert all(p.with_suffix('.claimed').is_file()for p in commands.glob('*.json'))
print(json.dumps({'time':time.time(),'uid':os.getuid(),'holder':actual,'held_locks':locks,'cards':cards,'compute':compute,
 'RAM_available_bytes':ram,'storage_free_bytes':available,'previous_service_identities':previous,
 'port19143_bind_check_passed':True,'inference_mutex_available':True,'task_GPUs4to7_empty_owned_leases':True,
 'all_model_GUI_scorer_calls_from_check':0,'foreign_processes_changed':False,'resource_locks_held_by_original_holder':True}))
'''

GUI = r'''
import fcntl,requests
assert os.getuid()==1015
root=Path(ROOT);assert not root.exists(),'Inspect the existing namespace instead of duplicating deployment'
base=root.parent;previous=[]
for name in['prefill-scheduled-full-history-gui-20261109-32','remaining-full-history-gui-20261110-33','remaining29-full-history-gui-20261110-37']:
 old=base/name
 for n in['control/process.json','control/runner-process.json']:
  record=json.loads((old/n).read_bytes());assert not same_live(record)
  previous.append({'namespace':name,'record':record,'actual':identity(record['pid'])})
 assert(old/'control/exit.json').is_file()
lockpath=base/'.full-gui-site29980.lock'
with lockpath.open('r+')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
assert all(r['Id']==expected and r['Config']['Labels']['owner']=='whz-qwen27-vwa'and r['State']['Running']for r,expected in zip(rows,ids))
assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(r.get('Name')=='qwen27_vwa_db_data'for r in rows[1]['Mounts'])
http=requests.get('http://192.0.2.10:29980/',timeout=20);assert http.status_code==200
for row in json.loads(BINDINGS)['tasks']:assert sha(row['original_private_path'])==row['original_private_SHA']
v=os.statvfs(base)
print(json.dumps({'time':time.time(),'uid':os.getuid(),'site_containers':[
 {'id':r['Id'],'owner':r['Config']['Labels']['owner'],'running':r['State']['Running']}for r in rows],
 'site_HTTP':http.status_code,'site_lock_available':True,'previous_GUI_identities':previous,
 'original_task_source_SHAs_bound':True,'storage_free_bytes':v.f_bavail*v.f_frsize,
 'new_model_GUI_scorer_calls':0,'fixtures_or_database_reset':False}))
'''


def main(host):
    manifest = admitted()
    out = HERE / ('prelaunch-linked02-'+host+'-'+str(time.time_ns()))
    out.mkdir()
    code = COMMON
    if host == '3090':
        code = 'M='+repr(manifest)+'\nOUTPUT='+repr(OUTPUT)+'\nPACKAGE='+repr(REMOTE_PACKAGE)+'\n'+code+PRIMARY
    else:
        code = 'ROOT='+repr(GUIROOT)+'\nBINDINGS='+repr((PACKAGE/'native-bindings-public.json').read_text(encoding='utf8'))+'\n'+code+GUI
    raw, operation = remote(host, code, 'remaining28-approved-prelaunch-resources-linked02-'+host, timeout=55)
    result = json.loads(raw)
    save(out/'evidence.json', result)
    save(out/'receipt.json', dict(operation=str(operation), manifest_sha256=sha(PACKAGE/'manifest.json'),
        remote_evidence_sha256=sha(out/'evidence.json'), prior_read_only_failure_preservation='D:\\MultiModel\\jev-defense-four-gpu-20261106\\remaining28-source-reference-gui-20261110-40\\prelaunch-path-failure-preservation-1794313027568892700', prior_failure_seal_sha256='ec4600c831e9ea7d27e1e42343804eb0d93101b552457fea1ab46c8eade2b7b5', new_model_GPU_GUI_scorer_paid_calls=0))
    save(out/'seal.json', {p.name:sha(p)for p in out.iterdir()if p.is_file()})
    summary = dict(host=host, evidence=str(out), passed=True)
    if host == '3090':
        summary.update(holder=result['holder'], actual_held_locks=len(result['held_locks']),
            task_cards=[r for r in result['cards']if r['index']in[4,5,6,7]],
            available_RAM_bytes=result['RAM_available_bytes'], storage_free_bytes=result['storage_free_bytes'])
    else:
        summary.update(site_HTTP=result['site_HTTP'], site_lock_available=result['site_lock_available'])
    print(json.dumps(summary))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('host',choices=['3090','4090'])
    main(parser.parse_args().host)
