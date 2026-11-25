"""Gracefully release only the verified idle task broker after both full audits."""
import json
import time
from pathlib import Path
from remote_util import HERE, remote, save, sha

CODE = r'''
import hashlib,json,os,subprocess,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 q=Path('/proc',str(pid))
 try:
  s=(q/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':int(pid),'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 except FileNotFoundError:return None
def same(a,b):return a is not None and a['state']not in ['Z','X']and all(a[k]==b[k]for k in ['pid','uid','command','start_ticks'])
assert os.getuid()==1033
proof=[];original=None
for g in GROUPS:
 p=Path(g['package']);o=Path(g['output'])
 assert sha(p/'manifest.json')==g['manifest_sha256']
 assert json.loads((o/'exit.json').read_bytes())['exit_code']==0
 for f in [o/'launcher-process.json',o/'primary/process.json',p/'flash/service/process.json']:
  saved=json.loads(f.read_bytes());actual=identity(saved['pid']);assert not same(actual,saved)
  proof.append({'saved':saved,'actual':actual,'verified_exited':True})
 expanded=json.loads((o/'expanded-lease.json').read_bytes())
 current=(expanded['original_lease'],expanded['original_lease_sha256'])
 assert original is None or original==current
 original=current
leasepath=Path(original[0]);assert sha(leasepath)==original[1]
lease=json.loads(leasepath.read_bytes());holder=lease['holder'];actual=identity(holder['pid']);assert same(actual,holder)
held=[]
for row in lease['lock_records']:
 q=Path('/proc',str(holder['pid']));fd=q/'fd'/str(row['fd']);info=(q/'fdinfo'/str(row['fd'])).read_text()
 assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and'WRITE '+str(holder['pid'])in info
 held.append({**row,'fdinfo':info})
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
uuids={r['uuid']for r in lease['gpu']}
assert not any(line.split(',')[0].strip()in uuids for line in compute.splitlines()if line.strip())
commands=leasepath.parent/'commands'
assert all(p.with_suffix('.claimed').exists()for p in commands.glob('*.json'))
assert not(leasepath.parent/'released.json').exists()
record={'saved_holder':holder,'actual_holder':actual,'actual_held_locks':held,'groups_verified_exited':proof,'compute_before':compute,'lease_sha256':sha(leasepath),'time':time.time()}
command=commands/'zz-release-four-mode-campaign-20261116.json'
with command.open('x')as f:json.dump({'action':'release','reason':'Both authorized batches completed/audited; await new protocol decision without idle task reservations'},f,indent=2);f.flush();os.fsync(f.fileno())
deadline=time.monotonic()+15
while time.monotonic()<deadline:
 if(leasepath.parent/'released.json').exists()and not same(identity(holder['pid']),holder):break
 time.sleep(.2)
else:raise RuntimeError('Release not yet verified; inspect existing release command, do not duplicate')
record.update(command=str(command),command_sha256=sha(command),released=json.loads((leasepath.parent/'released.json').read_bytes()),released_sha256=sha(leasepath.parent/'released.json'),actual_holder_after=identity(holder['pid']),compute_after=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True),time_after=time.time(),no_signals_or_foreign_process_changes=True,new_model_GUI_calls=0)
print(json.dumps(record))
'''


def main():
    assert not(HERE/'resource-release-current.json').exists()
    groups=[];bindings=[]
    for study in [HERE,HERE.parent/'buttons-native-trigger-supplement-20261116-05']:
        item=json.loads((study/'completed-group-audit-current.json').read_bytes());root=Path(item['root'])
        assert sha(root/'seal.json')==item['seal_sha256']
        for n,h in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/n)==h
        summary=json.loads((root/'summary.json').read_bytes());assert summary['all_model_GUI_launcher_processes_verified_exited']
        prepared=json.loads((study/'preparation-current.json').read_bytes());m=json.loads((Path(prepared['package'])/'manifest.json').read_bytes())
        groups.append({'package':m['package3090'],'output':m['output3090'],'manifest_sha256':prepared['manifest_sha256']})
        bindings.append({'root':str(root),'seal_sha256':item['seal_sha256']})
    root=HERE/('resource-release-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes());save(root/'group-bindings.json',bindings)
    raw,op=remote('3090','GROUPS='+repr(groups)+'\n'+CODE,'release-only-idle-verified-campaign-broker')
    result={'operation':str(op),**json.loads(raw)};save(root/'result.json',result)
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    save(HERE/'resource-release-current.json',{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'root':str(root),'original_holder_verified_exited':True,'compute_after':result['compute_after'],'no_foreign_process_changes':True,'new_model_GUI_calls':0}))


if __name__=='__main__':main()
