from remote_control import remote

code=r'''
from pathlib import Path
import json,os,time
p=Path('/proc/2357272');out={'time':time.time(),'read_only':True}
if p.exists():
 assert p.stat().st_uid==1015 and(p/'stat').read_text().rsplit(')',1)[1].split()[19]=='118648434'
 out['cmd']=(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()
 out['fds']={}
 for fd in(p/'fd').iterdir():
  try:out['fds'][fd.name]=os.readlink(fd)
  except OSError:pass
 for n in ['io','wchan','syscall','stack']:
  try:out[n]=(p/n).read_text()
  except OSError as e:out[n]={'error':str(e)}
else:out['absent']=True
print(json.dumps(out))
'''
out,path=remote('4090',code,'inspect-exact-preflight-I-O',timeout=45);print(out)
