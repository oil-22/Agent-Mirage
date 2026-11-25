"""Read-only current UID, full command, UUID, memory and held lock inspection."""
import json
import sys
import time
from remote_util import HERE, remote, save, sha

CODE = r'''
import hashlib,json,os,subprocess,time
from pathlib import Path
def identity(pid):
 p=Path('/proc',str(pid))
 try:
  s=(p/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':int(pid),'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 except FileNotFoundError:return None
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
compute=[]
for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
 if not line.strip():continue
 uuid,pid,used=[v.strip()for v in line.split(',')]
 compute.append({'uuid':uuid,'used_MiB':used,'identity':identity(pid)})
leases=[]
for path in [Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')]:
 if not path.exists():continue
 raw=path.read_bytes();value=json.loads(raw);holder=value.get('holder',{});actual=identity(holder.get('pid',0));held=[]
 if actual and all(actual.get(k)==holder.get(k)for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']:
  for row in value.get('lock_records',[]):
   fd=Path('/proc',str(actual['pid']),'fd',str(row['fd']));info=fd.parent.parent/'fdinfo'/str(row['fd'])
   held.append({'record':row,'current_inode':fd.stat().st_ino,'current_path':os.readlink(fd),'fdinfo':info.read_text()})
 leases.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'saved_holder':holder,'actual_holder':actual,'actual_held_locks':held})
owned=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  if any(x in command for x in ['jev-defense-four-gpu-20261106','flash-four-injection','inference_server.py']):owned.append(identity(p.name))
 except (FileNotFoundError,PermissionError):pass
print(json.dumps({'time':time.time(),'uid':os.getuid(),'GPU_csv':gpu,'compute_actual_UID_full_command':compute,'leases':leases,'matching_owned_processes':owned,'new_model_GUI_calls':0}))
'''


def main():
    host = sys.argv[1]
    raw, operation = remote(host, CODE, 'four-injection-resource-readonly-' + host)
    value = json.loads(raw)
    receipt = HERE / ('resource-' + host + '-' + str(time.time_ns()) + '.json')
    save(receipt, {'operation': str(operation), 'operation_seal_sha256': sha(operation / 'seal.json'), 'result': value})
    print(json.dumps({'receipt': str(receipt), 'result': value}))


if __name__ == '__main__':
    main()
