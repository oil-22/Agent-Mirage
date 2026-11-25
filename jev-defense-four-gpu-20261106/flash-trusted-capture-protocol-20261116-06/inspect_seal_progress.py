"""Read actual launcher I/O progress without interrupting final sealing."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import json,os,time
from pathlib import Path
o=Path(O);saved=json.loads((o/'launcher-process.json').read_bytes());p=Path('/proc',str(saved['pid']))
actual=None;files=[]
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 actual={'pid':saved['pid'],'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 assert all(actual[k]==saved[k]for k in['uid','command','start_ticks'])
 for f in(p/'fd').iterdir():
  try:
   target=os.readlink(f)
   if target.startswith(O):
    files.append({'fd':f.name,'path':target,'fdinfo':(p/'fdinfo'/f.name).read_text(),'size':Path(target).stat().st_size})
  except FileNotFoundError:pass
 io=(p/'io').read_text();wait=(p/'wchan').read_text()
else:io=None;wait=None
released=json.loads((o/'released.json').read_bytes())if(o/'released.json').exists()else None
exit=json.loads((o/'exit.json').read_bytes())if(o/'exit.json').exists()else None
space=os.statvfs(o)
print(json.dumps({'time':time.time(),'identity':actual,'IO':io,'wait_channel':wait,'open_output_files':files,'released':released,'exit':exit,'postexit_seal_exists':(o/'postexit-seal.json').exists(),'free_bytes':space.f_bavail*space.f_frsize,'read_only_no_inference_or_interruption':True}))
'''

m = manifest()
raw, operation = remote('3090', 'O=' + repr(m['output3090']) + '\n' + CODE, 'read-only-actual-final-sealer-IO')
root = HERE / ('seal-progress-' + str(time.time_ns()))
root.mkdir()
save(root / 'result.json', {'operation': str(operation), **json.loads(raw)})
save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
print(json.dumps({'root': str(root), **json.loads(raw)}))
