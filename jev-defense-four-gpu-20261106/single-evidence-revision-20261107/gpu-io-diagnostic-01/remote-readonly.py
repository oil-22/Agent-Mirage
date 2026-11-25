import json,os,pathlib,time
p=pathlib.Path('/proc/3148034');out={'time':time.time()}
for name in ['wchan','io','status','syscall']:
 try:out[name]=(p/name).read_text()
 except Exception as e:out[name]=str(e)
out['fds']=[]
for f in(p/'fd').iterdir():
 try:out['fds'].append({'fd':f.name,'target':os.readlink(f)})
 except Exception:pass
r=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01/worker')
out['files']=[{'name':str(f.relative_to(r)),'bytes':f.stat().st_size}for f in r.rglob('*')if f.is_file()]
print(json.dumps(out))
