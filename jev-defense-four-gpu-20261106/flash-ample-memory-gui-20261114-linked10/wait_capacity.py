"""Bounded read-only capacity wait; never launches or retries anything."""
import json,time
from control import HERE,OUT,remote,save
code='ROOT='+repr(OUT)+'\n'+r'''
import json,time
from pathlib import Path
r=Path(ROOT);deadline=time.monotonic()+40
while not(r/'primary/ready.json').exists()and not(r/'primary/terminal.json').exists()and time.monotonic()<deadline:time.sleep(2)
out={'time':time.time(),'ready_file_exists':(r/'primary/ready.json').exists(),'terminal_file_exists':(r/'primary/terminal.json').exists(),'new_model_GUI_calls':0,'files':{}}
for n in ['primary/status.json','primary/failure.json','capacity/lifetime-validation/result.json','capacity/lifetime-validation/mlp-memory-proof.json','capacity/50-image-source-bound-stress/result.json']:
 if(r/n).exists():out['files'][n]=json.loads((r/n).read_bytes())
print(json.dumps(out))
'''
raw,op=remote('3090',code,'bounded-read-only-capacity-wait',timeout=55);value=json.loads(raw);save(HERE/('capacity-wait-'+str(time.time_ns())+'.json'),{'result':value,'operation':str(op)});print(json.dumps(value))
