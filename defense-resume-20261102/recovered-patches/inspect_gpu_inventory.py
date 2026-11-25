"""Read GPU/process ownership before using newly authorized idle cards."""
import json
from pathlib import Path
from remote import remote

code = '''import subprocess,json,pathlib,pwd,time
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.used,memory.free,utilization.gpu','--format=csv'],text=True)
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
processes=[]
for line in apps.splitlines():
 parts=[x.strip()for x in line.split(',')]
 if len(parts)!=3:continue
 uuid,pid,mem=parts;p=pathlib.Path('/proc')/pid
 try:owner=pwd.getpwuid(p.stat().st_uid).pw_name;executable=str((p/'exe').resolve());command=(p/'comm').read_text().strip()
 except(FileNotFoundError,PermissionError):owner='unavailable';executable='';command=''
 processes.append({'gpu_uuid':uuid,'pid':int(pid),'memory_mib':mem,'owner':owner,'executable':executable,'command_name':command})
print(json.dumps({'time':time.time(),'gpu':gpu,'processes':processes}))
'''
data = json.loads(remote(code, host='3090'))
out = Path(__file__).resolve().parent / 'latest-3090-gpu-inventory.json'
out.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data))
