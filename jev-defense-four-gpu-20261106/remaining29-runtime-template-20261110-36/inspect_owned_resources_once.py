"""Fresh read-only evidence for the authorized 3090 GPU4-7; never allocate."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote


CODE = r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
leasepath=base/'resource-attempt-20261106-01/lease.json'
assert os.getuid()==1033
raw=leasepath.read_bytes();lease=json.loads(raw)
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
expected=lease['holder'];actual=identity(expected['pid'])
holder_ok=not actual.get('absent') and all(str(actual[k])==str(expected[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
locks=[]
if holder_ok:
 for row in lease['lock_records']:
  proc=Path('/proc',str(expected['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
  locks.append({'fd':row['fd'],'path':row['path'],'inode':fd.stat().st_ino,
   'matches_expected':os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(expected['pid'])in info})
cards={}
for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
 index,uuid,free=[x.strip()for x in line.split(',')]
 if int(index)in[4,5,6,7]:cards[int(index)]={'index':int(index),'uuid':uuid,'free_MiB':int(free)}
expected_cards={r['uuid']for r in lease['gpu']}
assert {r['index']for r in lease['gpu']}=={4,5,6,7}
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True).splitlines():
 if not line.strip():continue
 uuid,pid=[x.strip()for x in line.split(',')]
 if uuid not in expected_cards:continue
 process=identity(int(pid))
 if process.get('uid')!=1033 and not process.get('absent'):
  command=process.pop('command');process['command_sha256']=hashlib.sha256(command.encode()).hexdigest()
 compute.append({'gpu_uuid':uuid,'process':process})
uuid_ok=all(cards.get(r['index'],{}).get('uuid')==r['uuid']for r in lease['gpu'])
empty=not compute
headroom=uuid_ok and all(cards[i]['free_MiB']>=23000for i in [4,5,6,7])
ports=subprocess.check_output(['ss','-H','-ltnp'],text=True)
listeners=[x for x in ports.splitlines()if any(':'+str(p)+' 'in x for p in [19141,19142])]
ram=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
storage=Path('/data/researcher/jev-defense-four-gpu-20261106');v=os.statvfs(storage)
old={}
for name,pid,start in [('closed_worker',32383,'1187155095'),('closed_launcher',32101,'1187151974')]:
 process=identity(pid)
 old[name]={'observed':process,'same_closed_identity_live':not process.get('absent')and process.get('start_ticks')==start and process.get('state')not in['Z','X']}
assert leasepath.read_bytes()==raw
print(json.dumps({'captured_unix':time.time(),'observer_uid':os.getuid(),'lease_sha256':hashlib.sha256(raw).hexdigest(),
 'expected_holder':expected,'actual_holder':actual,'holder_full_identity_matches':holder_ok,'actual_lock_records':locks,
 'nine_original_locks_actually_held':len(locks)==9 and all(x['matches_expected']for x in locks),
 'GPU4_7':cards,'UUIDs_match':uuid_ok,'target_compute':compute,'target_GPUs_empty':empty,'headroom_at_least23000MiB':headroom,
 'available_RAM_bytes':ram,'owned_data_volume_free_bytes':v.f_bavail*v.f_frsize,'prospective_port_listeners':listeners,
 'closed_process_identities':old,'read_only':True,'new_allocations_locks_signals_or_services':0,
 'new_model_GUI_scorer_paid_calls':0,'source_choice_still_required':True,'all_future_full_history_capacity_or_efficacy_proven':False},ensure_ascii=True))
'''


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    root = HERE / ('resource-evidence-' + str(time.time_ns()))
    root.mkdir()
    shutil.copyfile(__file__, root / 'inspect_owned_resources_once.py')
    (root / 'remote-source.py').write_text(CODE, encoding='utf-8')
    save(root / 'intent.json', {'time': time.time(), 'read_only': True, 'target': '3090 physical4-7',
                              'new_model_GPU_GUI_scorer_paid_calls': 0})
    try:
        output, operation = remote('3090', CODE, 'remaining29-readonly-fresh-owned4-7-evidence', timeout=55)
        (root / 'raw-output.txt').write_text(output, encoding='utf-8')
        result = json.loads(output)
        save(root / 'evidence.json', result)
        save(root / 'receipt.json', {'remote_operation': str(operation), 'read_only': True,
                                    'actual_UID_full_command_UUID_locks_compute_checked': True,
                                    'new_model_GPU_GUI_scorer_paid_calls': 0})
    except BaseException:
        import traceback
        (root / 'observer-failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
    finally:
        save(root / 'seal.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(root.iterdir()) if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': hashlib.sha256((root / 'seal.json').read_bytes()).hexdigest(),
               'evidence_sha256': hashlib.sha256((root / 'evidence.json').read_bytes()).hexdigest()}
    save(HERE / ('resource-evidence-' + root.name.split('-')[-1] + '-created.json'), pointer)
    print(json.dumps({**pointer, **{k: result[k] for k in ['holder_full_identity_matches',
         'nine_original_locks_actually_held', 'target_GPUs_empty', 'headroom_at_least23000MiB',
         'prospective_port_listeners', 'new_model_GUI_scorer_paid_calls']}}, ensure_ascii=True))


if __name__ == '__main__':
    main()
