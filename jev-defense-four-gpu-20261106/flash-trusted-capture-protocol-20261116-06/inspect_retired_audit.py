"""Read-only identification of any abandoned read-only SSH auditor."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import json,os,time
from pathlib import Path
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit()or int(p.name)==os.getpid():continue
 try:
  if p.stat().st_uid!=1033:continue
  command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
  if command!='/opt/whz/conda-envs/webmall-vlm/bin/python -B -':continue
  stat=(p/'stat').read_text().rsplit(')',1)[1].split();opened=[]
  for f in(p/'fd').iterdir():
   try:
    target=os.readlink(f)
    if target.startswith(O):opened.append({'fd':f.name,'target':target,'fdinfo':(p/'fdinfo'/f.name).read_text()})
   except FileNotFoundError:pass
  rows.append({'pid':int(p.name),'uid':1033,'command':command,'start_ticks':stat[19],'parent_pid':int(stat[1]),'state':stat[0],'output_fds':opened,'IO':(p/'io').read_text(),'wait_channel':(p/'wchan').read_text()})
 except FileNotFoundError:pass
print(json.dumps({'time':time.time(),'possible_readers':rows,'read_only_no_signal_or_allocation':True}))
'''

raw, operation = remote('3090', 'O=' + repr(manifest()['output3090']) + '\n' + CODE, 'identify-retired-read-only-auditor-without-signals')
root = HERE / ('retired-audit-inspection-' + str(time.time_ns()))
root.mkdir()
save(root / 'result.json', {'operation': str(operation), **json.loads(raw)})
save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
print(json.dumps({'root': str(root), **json.loads(raw)}))
