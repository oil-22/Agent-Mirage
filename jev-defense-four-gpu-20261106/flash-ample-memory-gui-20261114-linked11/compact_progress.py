"""Bounded actual process/evidence inspection; cannot launch or retry jobs."""
import json
import sys
import time
from control import HERE, OUT, R3090, R4090, remote, save

pause = 40 if '--wait' in sys.argv else 0
code = 'ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\nWAIT=' + repr(pause) + '\n' + r'''
import json,time
from pathlib import Path
r=Path(ROOT);p=Path(PACKAGE)
def load(f):return json.loads(f.read_bytes())if f.exists()else None
deadline=time.monotonic()+WAIT
while time.monotonic()<deadline and not(r/'primary/terminal.json').exists():time.sleep(2)
def identity(record):
 q=Path('/proc',str(record['pid']))
 if not q.exists():return{'record':record,'same_live_process':False}
 s=(q/'stat').read_text().rsplit(')',1)[1].split()
 actual={'pid':record['pid'],'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 return{'actual':actual,'same_live_process':all(record[k]==actual[k]for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X']}
last=[]
for d in sorted((r/'primary/requests').glob('*'),reverse=True):
 if not(d/'seal.json').exists():continue
 wire=load(d/'wire-request.bin');generated=load(d/'actual-generation.json')
 last.append({'directory':str(d),'run_id':wire['run_id'],'decision':wire['decision_index'],'input_tokens':generated['input_tokens']if generated else None,'output_tokens':generated['output_tokens']if generated else None,'natural_EOS':generated['natural_EOS']if generated else None,'technical_failure':(d/'failure.json').exists()})
 if len(last)==3:break
out={'time':time.time(),'primary':load(r/'primary/status.json'),'terminal':load(r/'primary/terminal.json'),'last_sealed_requests':last,'sealed_Flash_replies':len(list((p/'flash/service/requests').glob('*/seal.json'))),'actual_processes':{str(f):identity(load(f))for f in [r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']if f.exists()},'new_model_GUI_calls':0}
print(json.dumps(out))
'''
raw, operation = remote('3090', code, 'bounded-actual-GUI-progress', timeout=55)
main = {'result': json.loads(raw), 'operation': str(operation)}
code = 'ROOT=' + repr(R4090) + '\n' + r'''
import json,time
from pathlib import Path
r=Path(ROOT)
out={'time':time.time(),'batch_status':json.loads((r/'batch/status.json').read_bytes()),'sealed_terminals':len(list((r/'batch/runs').glob('*/attempt-*/seal.json'))),'control_exit':json.loads((r/'control/exit.json').read_bytes())if(r/'control/exit.json').exists()else None,'new_model_GUI_calls':0}
print(json.dumps(out))
'''
raw, operation = remote('4090', code, 'actual-GUI-batch-status')
gui = {'result': json.loads(raw), 'operation': str(operation)}
receipt = HERE / ('compact-progress-' + str(time.time_ns()) + '.json')
save(receipt, {'3090': main, '4090': gui})
print(json.dumps({'receipt': str(receipt), 'main': main['result'], 'GUI': gui['result']}))
