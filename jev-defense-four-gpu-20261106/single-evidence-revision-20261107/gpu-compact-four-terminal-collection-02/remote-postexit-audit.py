import hashlib,json,pathlib,time
root=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-compact-four-first-attempts-02')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as stream:
  while True:
   raw=stream.read(16*1024*1024)
   if not raw:break
   h.update(raw)
 return h.hexdigest()
manifest=json.loads((root/'terminal-manifest.json').read_bytes())
assert all(sha(root/name)==h for name,h in manifest.items())
exit_record=json.loads((root/'exit.json').read_bytes())
actual_processes={}
for role in ['launcher_identity','worker_identity']:
 expected=exit_record.get(role)
 if expected is None:continue
 p=pathlib.Path('/proc')/str(expected['pid'])
 if p.exists():
  tail=(p/'stat').read_text().rsplit(')',1)[1].split()
  actual={'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
  actual_processes[role]=actual
  assert not(all(str(actual[k])==str(expected[k])for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X'])
 else:actual_processes[role]=None
print(json.dumps({'status':'postexit_remote_terminal_manifest_all_files_verified','files':len(manifest),
 'terminal_manifest_sha256':sha(root/'terminal-manifest.json'),'exit':exit_record,
 'actual_original_processes':actual_processes,'read_only':True,'new_model_GUI_calls':0,'time_unix':time.time()}))
