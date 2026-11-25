"""Bounded read-only monitoring within this chat; no launch or model endpoint."""
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


def main():
    target=int(sys.argv[1]);deadline=time.monotonic()+1200;m=manifest()
    root=HERE/('terminal-wait-'+str(time.time_ns()));root.mkdir();(root/'source.py').write_bytes(Path(__file__).read_bytes())
    last=None;count=0;reason='bounded_wait_elapsed'
    while time.monotonic()<deadline:
        code='O='+repr(m['output3090'])+'\n'+r'''
import json,time
from pathlib import Path
o=Path(O);status=json.loads((o/'primary/status.json').read_bytes());saved=json.loads((o/'primary/process.json').read_bytes());q=Path('/proc',str(saved['pid']));actual=None
if q.exists():
 stat=(q/'stat').read_text().rsplit(')',1)[1].split();actual={'pid':saved['pid'],'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':stat[19],'state':stat[0]}
same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
exit=json.loads((o/'exit.json').read_bytes())if(o/'exit.json').exists()else None
print(json.dumps({'time':time.time(),'status':status,'saved':saved,'actual':actual,'same_live_identity':same,'exit':exit,'new_model_GUI_calls':0}))
'''
        raw,op=remote('3090',code,'late-corruption-bounded-current-thread-wait',timeout=35)
        result=json.loads(raw);save(root/('%04d.json'%count),{'operation':str(op),'result':result});count+=1
        s=result['status'];state=(s.get('done'),s.get('active'),s.get('complete_actor_replies'),s.get('phase'))
        if state!=last:
            print(json.dumps({'done':state[0],'active':state[1],'complete_replies':state[2],'phase':state[3],'same_live_identity':result['same_live_identity']}),flush=True);last=state
        if s.get('done',0)>=target:reason='next_logical_terminal_observed';break
        if not result['same_live_identity']:reason='actual_worker_exited_requires_inspection';break
        time.sleep(25)
    save(root/'summary.json',{'target_terminal_count':target,'reason':reason,'snapshots':count,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    print(json.dumps({'wait_receipt':str(root),'reason':reason,'new_model_GUI_calls':0}),flush=True)


if __name__=='__main__':main()
