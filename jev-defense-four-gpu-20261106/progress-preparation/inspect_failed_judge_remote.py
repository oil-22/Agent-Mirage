import hashlib
import json
from pathlib import Path
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
group=base/'online-service-group-1793978182501156243'
request=group/'primary/requests/bd7ed2f4753b00594cb626a4cad3b740c0f95d91128547da69404254a2559841'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(request/'seal.json')=='2524d02f7c18dd662794122701648e92c7b5729b9ae7c386b13c23ffbe4dcec7'
seal=json.loads((request/'seal.json').read_bytes())
for name,expected in seal.items():assert sha(request/name)==expected
failure=json.loads((request/'failure.json').read_bytes())
wire=json.loads((request/'request.json').read_bytes())
generation=json.loads((request/'generation.json').read_bytes()) if(request/'generation.json').exists()else None
trace=json.loads((request/'forward-trace.json').read_bytes())
print(json.dumps({'failure':failure,'request_envelope':{key:wire[key]for key in
    ('trajectory_id','decision_index','attempt_index','request_id')},
    'payload_operation':wire['payload']['operation'],'payload_keys':list(wire['payload']),
    'request_files':seal,'generation_summary':None if generation is None else
       {key:generation[key]for key in('hit_output_cap','seconds','generation_config','verifier_grammar')if key in generation},
    'input_ids_count':None if generation is None else len(generation['input_ids']),
    'output_ids_count':None if generation is None else len(generation['generated_ids']),
    'forward_trace_records':len(trace),'forward_trace_sha256':sha(request/'forward-trace.json'),
    'online_state':json.loads((group/'online-state.json').read_bytes()),'model_HTTP_GUI_calls':0}))
