"""Read-only bounded wait for real launcher exit and its immutable final seal."""
import json
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


def main():
    root = HERE/('postexit-wait-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    m = manifest()
    code = 'O='+repr(m['output3090'])+'\nP='+repr(m['package3090'])+'\n'+r'''
import json,time
from pathlib import Path
o=Path(O);p=Path(P);rows=[]
for file in [o/'launcher-process.json',o/'primary/process.json',p/'flash/service/process.json']:
 saved=json.loads(file.read_bytes());q=Path('/proc',str(saved['pid']));actual=None
 if q.exists():
  s=(q/'stat').read_text().rsplit(')',1)[1].split()
  actual={'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 same=actual is not None and actual['state']not in ['Z','X'] and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
 rows.append({'saved':saved,'actual':actual,'same_live':same})
receipts={n:(o/n).exists()for n in ['exit.json','postexit-seal.json']}
print(json.dumps({'time':time.time(),'identities':rows,'receipts':receipts,'ready':not any(r['same_live']for r in rows)and all(receipts.values()),'new_model_GUI_calls':0}))
'''
    deadline = time.monotonic()+1200
    last = None
    for i in range(100):
        raw, operation = remote('3090',code,'read-only-real-postexit-receipt-wait',timeout=35)
        result = json.loads(raw)
        save(root/(f'{i:04d}.json'),{'operation':str(operation),'result':result})
        state = (tuple(r['same_live'] for r in result['identities']),result['receipts'],result['ready'])
        if state != last:
            print(json.dumps({'same_live':state[0],'receipts':state[1],'ready':state[2]}),flush=True)
            last = state
        if result['ready'] or time.monotonic() >= deadline:
            save(root/'summary.json',{'ready':result['ready'],'snapshots':i+1,'new_model_GUI_calls':0})
            save(root/'seal.json',{q.name:sha(q) for q in root.iterdir() if q.is_file()})
            print(json.dumps({'postexit_wait_receipt':str(root),'ready':result['ready']}),flush=True)
            return
        time.sleep(20)


if __name__ == '__main__':
    main()
