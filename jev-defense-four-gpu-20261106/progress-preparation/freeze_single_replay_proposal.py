import base64
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
base=Path(__file__).resolve().parents[1]
files={name:base64.b64encode((base/'capacity-replay-proposal-01'/name).read_bytes()).decode()
       for name in('README.md','replay_contract.py')}
code='FILES='+repr(files)+'\n'+'''
import base64,copy,hashlib,importlib.util,json,time
from pathlib import Path
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
root=base/'capacity-replay-proposals'/str(time.time_ns());root.mkdir(parents=True)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
 with(root/name).open('x')as handle:json.dump(value,handle,indent=2)
for name,encoded in FILES.items():
 with(root/name).open('xb')as handle:handle.write(base64.b64decode(encoded))
preservation=base/'failed-gui-service-preservation/1793982653388639508'
cpu=base/'failed-input-CPU-layout-audits/1793982908234148012'
assert sha(preservation/'receipt.json')=='d78feb1d58d452c5218663bd41afe155e35825efddff0300ef0f5ff2c9c7e976'
assert sha(cpu/'receipt.json')=='acb9b2fb465bb2763a696c83599d5b50f1aa61f5de78393b244084d5db02a6e9'
source=preservation/'service-group/primary/requests/bd7ed2f4753b00594cb626a4cad3b740c0f95d91128547da69404254a2559841'
raw=(source/'request.json').read_bytes();envelope=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()=='170e61a801551d69aa4b6aeb6b2f5f3dbfa03e9e3352f00034f35b9df635ef7d'
payload=envelope['payload']
native_wire=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
(root/'original-failed-online-envelope.json').write_bytes(raw)
(root/'frozen-judge-payload-wire.json').write_bytes(native_wire)
canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
canonical_sha=hashlib.sha256(canonical).hexdigest()
assert canonical_sha=='688585e446fcf5994ec2c711061d033f72ddff80c78aa8057a9dd222d95a29a7'
save('primary-admission.json',{'mode':'capacity_preflight','max_new_calls':1,'GUI_actions':0,
 'requests':[{'operation':'judge','fingerprint':canonical_sha,
 'wire_sha256':hashlib.sha256(native_wire).hexdigest(),'wire':'frozen-judge-payload-wire.json'}]})
save('helper-admission.json',{'mode':'resident_only','max_new_calls':0,'requests':[],'GUI_actions':0})
for name in('candidate-device-map.json','native-state-placement-comparison.json',
 'original-native-generation-config.reconstructed.json','original-judge-call-schema-and-messages.reconstructed.json'):
 (root/name).write_bytes((cpu/name).read_bytes())
plan={'stage':'one_failed_judge_capacity_technical_replay',
 'budgets':{'judge':1,'actor':0,'helper':0,'GUI':0,'scorer':0,'format_retries':0,'output_tokens':4096},
 'original_failed_external_wire_sha256':hashlib.sha256(raw).hexdigest(),
 'original_failed_canonical_payload_sha256':canonical_sha,
 'new_frozen_payload_wire_sha256':hashlib.sha256(native_wire).hexdigest(),
 'transport_outer_envelope_differs_but_native_payload_order_and_model_inputs_preserved':True,
 'CPU_input_binding_proof_sha256':sha(cpu/'receipt.json'),
 'preservation_proof_sha256':sha(preservation/'receipt.json'),
 'input_tokens':21470,'original_images':12,'physical_gpus':[4,5,6,7],'helper_physical_gpu':7,
 'candidate_decoder_layer_counts':[14,22,22,6],
 'model_conditions':{'primary_dtype':'bfloat16','primary_attention':'sdpa','seed':42,
 'original_images':True,'complete_history':True,'native_processor_generation_grammar':True,'helper_fast':False},
 'primary_process_environment':{'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},
 'helper_mode':'resident_only','automatic_retry':False,'launch_ready':False,
 'GUI_release_after_capacity':False,'old_GUI_budget_reset_or_resume_allowed':False,
 'old72EOSplus1prefillfailure_preserved':True,
 'new_GPU_request_or_weight_load_during_preparation':0}
save('plan.json',plan)
spec=importlib.util.spec_from_file_location('replay_proposal_contract',root/'replay_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
assert contract.validate_plan(plan,envelope)==json.loads((root/'candidate-device-map.json').read_bytes())
negative=[]
for name,mutate in [('second_judge',lambda x:x['budgets'].update(judge=2)),
 ('helper_call',lambda x:x['budgets'].update(helper=1)),
 ('GUI_call',lambda x:x['budgets'].update(GUI=1)),
 ('output_shortening',lambda x:x['budgets'].update(output_tokens=2048)),
 ('old_layout',lambda x:x.update(candidate_decoder_layer_counts=[18,20,20,6])),
 ('automatic_retry',lambda x:x.update(automatic_retry=True))]:
 value=copy.deepcopy(plan);mutate(value)
 try:contract.validate_plan(value,envelope)
 except AssertionError:negative.append(name)
 else:raise AssertionError('Unsafe plan boundary accepted: '+name)
changed=copy.deepcopy(envelope);changed['payload']['system']+=' extra input'
try:contract.validate_plan(plan,changed)
except AssertionError:negative.append('changed_system_input')
else:raise AssertionError('Changed native input accepted')
try:contract.validate_future_launch_evidence({})
except AssertionError:negative.append('missing_actual_launch_gate')
else:raise AssertionError('Missing real stop/resource evidence accepted')
save('CPU-finite-admission-checks.json',{'valid_plan_passed':True,'rejected_boundaries':negative,
 'actual_model_GPU_GUI_calls':0,'original_failed_source_envelope_verified':True})
save('receipt.json',{'status':'prepared_CPU_only','root':str(root),'launch_ready':False,
 'plan_sha256':sha(root/'plan.json'),'contract_sha256':sha(root/'replay_contract.py'),
 'frozen_payload_wire_sha256':sha(root/'frozen-judge-payload-wire.json'),
 'primary_calls_planned':1,'helper_calls_planned':0,'actor_GUI_scorer_calls_planned':0,
 'output_budget':4096,'CPU_rejected_boundaries':negative,
 'original_failed_request_forward_inputs_bound_by_CPU_proof':True,
 'needs_root_review_exact_new_worker_launcher_source_and_old_stop_terminal_evidence':True,
 'no_launcher_no_claim_no_models':True,'actual_model_GPU_GUI_calls':0})
save('seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
print(json.dumps({'receipt':str(root/'receipt.json'),'receipt_sha256':sha(root/'receipt.json'),
 'seal_sha256':sha(root/'seal.json'),'plan_sha256':sha(root/'plan.json'),
 'contract_sha256':sha(root/'replay_contract.py'),'frozen_payload_wire_sha256':sha(root/'frozen-judge-payload-wire.json'),
 'CPU_negative_boundaries_rejected':len(negative),'launch_ready':False,'actual_model_GPU_GUI_calls':0}))
'''
print(remote(code,timeout=90))
