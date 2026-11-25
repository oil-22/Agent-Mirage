import pathlib
import subprocess
import time
import json

here = pathlib.Path(__file__).resolve().parent
log = (here / 'model-transfer.log').open('w',encoding='utf-8')
models = ['Qwen3.5-9B','GLM-4.6V-Flash-411bb4d77144']
state=[]
for model in models:
    started=time.time()
    subprocess.run(['ssh','-o','BatchMode=yes','3090','mkdir -p /home/researcher/models'],check=True,stdout=log,stderr=log)
    src=subprocess.Popen(['ssh','-o','BatchMode=yes','4090',f'tar -cf - -C /data/researcher/models --exclude=.cache {model}'],stdout=subprocess.PIPE,stderr=log)
    dst=subprocess.Popen(['ssh','-o','BatchMode=yes','3090','tar -xf - -C /home/researcher/models'],stdin=src.stdout,stdout=log,stderr=log)
    src.stdout.close()
    rc_dst=dst.wait()
    rc_src=src.wait()
    state.append(dict(model=model,source_exit=rc_src,destination_exit=rc_dst,seconds=round(time.time()-started)))
    (here/'model-transfer.json').write_text(json.dumps(state,indent=2))
    if rc_src or rc_dst:
        raise SystemExit('transfer failed')
