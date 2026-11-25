from remote_control import remote,ROOT4090
code='ROOT='+repr(ROOT4090)+'\n'+r'''
from pathlib import Path
import json,os,subprocess,time
r=Path(ROOT);out={'time':time.time(),'read_only':True,'models_GUI_scorer':0,'preflight_exists':(r/'environment-preflight').exists(),
 'preflight_names':[str(p.relative_to(r))for p in (r/'environment-preflight').rglob('*')if p.is_file()and'.auth'not in p.parts]}
out['owned_GUI_python_processes']=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()
  if '/runtime-stage-01/env/bin/python'in cmd:
   stat=(p/'stat').read_text().rsplit(')',1)[1].split()
   out['owned_GUI_python_processes'].append({'pid':int(p.name),'uid':p.stat().st_uid,'full_command':cmd,'start_ticks':stat[19],'state':stat[0],
      'wait_channel':(p/'wchan').read_text(),'cwd':os.readlink(p/'cwd'),'children':(p/'task'/p.name/'children').read_text()})
 except(OSError,UnicodeError):pass
out['site_container_running']=subprocess.check_output(['docker','ps','--filter','id=de6f56798c3c','--format','{{.ID}} {{.Status}} {{.Names}}'],text=True)
out['public_catalog_names_only']={}
for p in [Path('/data/researcher/vwa100-2026-10-09/classifieds')]:
 if p.is_dir():out['public_catalog_names_only'][str(p)]=sorted(x.name for x in p.iterdir())[:80]
print(json.dumps(out,ensure_ascii=False))
'''
out,path=remote('4090',code,'diagnose-GUI-environment-timeout-readonly',timeout=45);print(out)
