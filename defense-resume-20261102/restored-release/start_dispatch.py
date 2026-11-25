import json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent
assert not (R/'dispatch-launch.json').exists(),'Inspect existing job before starting again'
log=R/('dispatch-'+str(time.time_ns())+'.log')
with log.open('xb')as out:
 p=subprocess.Popen([os.sys.executable,'-u',str(R/'gated_dispatch.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
receipt={'pid':p.pid,'log':str(log),'time':time.time(),'scope':'one finite launch job; not hourly automation'}
(R/'dispatch-launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
