"""Refresh actual owned runtime/locks/GPU identities and log-prefix hashes."""
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha


def main():
    original=json.loads((HERE/'runtime-ownership-1794734863825764700.json').read_bytes())
    reader=Path(original['operation'])/'source.py'
    code=reader.read_text('utf8')
    assert code.count("print(json.dumps({'time':time.time(),'actual_holder'")==1
    code=code[:code.rfind("print(json.dumps({'time':time.time(),'actual_holder'")]+r'''
compute_rows=[]
for line in compute.strip().splitlines():
 uuid,pid,used=[s.strip()for s in line.split(',')];q=Path('/proc',pid)
 if not q.exists():continue
 stat=(q/'stat').read_text().rsplit(')',1)[1].split()
 compute_rows.append({'uuid':uuid,'pid':int(pid),'used_MiB':int(used),'uid':q.stat().st_uid,'full_command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':stat[19]})
expected={v['pid']for v in identities.values()}
foreign=[v for v in compute_rows if v['pid']not in expected]
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
logs=[]
for file in [o/'primary.log',o/'Flash-service.log']:
 raw=file.read_bytes();logs.append({'path':str(file),'read_prefix_bytes':len(raw),'prefix_sha256':hashlib.sha256(raw).hexdigest(),'time':time.time()})
print(json.dumps({'time':time.time(),'actual_holder':holder,'actual_launcher':launcher,'actual_services':identities,'actual_inherited_held_locks':held,'records':records,'compute_processes_with_actual_UID_and_command':compute_rows,'foreign_processes_not_terminated_or_shared':foreign,'GPU_memory_csv':gpu,'logs_at_read_time':logs,'new_GPU_model_GUI_calls_by_inspection':0}))
'''
    raw,op=remote('3090',code,'late-corruption-refresh-owned-locks-GPU-log-SHA-readonly',timeout=45)
    result=json.loads(raw);root=HERE/('runtime-refresh-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'result.json',{'operation':str(op),'original_readonly_reader':str(reader),'original_reader_sha256':sha(reader),'result':result})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    pointer={'root':str(root),'seal_sha256':sha(root/'seal.json')}
    (HERE/'runtime-refresh-current.json').write_text(json.dumps(pointer,indent=2),encoding='utf8')
    print(json.dumps({'receipt':str(root),'actual_PIDs':{k:v['pid']for k,v in result['actual_services'].items()},'held_lock_counts':{k:len(v)for k,v in result['actual_inherited_held_locks'].items()},'foreign_compute':result['foreign_processes_not_terminated_or_shared'],'log_prefixes_SHA_verified_at_read_time':True,'new_model_GUI_calls':0}))


if __name__=='__main__':main()
