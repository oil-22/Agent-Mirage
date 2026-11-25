"""Freeze four distinct archived full images for a bounded new image-only stage."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'four-image-inputs-01'
OUT.mkdir(exist_ok=False)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

spec=importlib.util.spec_from_file_location('image_contract',ROOT/'evidence-contract/image_evidence.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
source=ROOT/'source-discovery-linked03'
inventory=json.loads((source/'inventory.json').read_text(encoding='utf-8'))
selected=['S01','S07','S13','S25']
records=[]
for item in inventory:
    if item['id']not in selected: continue
    image=source/item['image_path']
    assert sha(image)==item['image_sha256']
    assert sha(source/item['source_path'])==item['original_source_artifact_sha256']
    request=contract.build_image_only_request(image.read_bytes(),'Qwen/Qwen3.5-9B',
        'c202236235762e1c871ad0ccb60c8ee5ba337b9a')
    request_path=OUT/(item['id']+'-request.json');write(request_path,request)
    records.append(dict(item,request_path=request_path.name,request_sha256=sha(request_path),
        native_model_receives_only=['original_full_image','fixed_generic_visual_prompt']))
assert [r['id']for r in records]==selected
write(OUT/'source-bindings.json',records)
protocol={
 'stage':'four_new_original_images_native_auxiliary_development',
 'status':'inputs_frozen_not_GPU_admitted',
 'selection':'first archived early original image per Chrome, GIMP, Calc, Writer in source inventory order; no new output-based selection',
 'source_episodes':4,'image_count':4,'image_ids':selected,
 'prior_attention_archived_images':True,
 'new_auxiliary_prompt_and_contract':True,
 'not_repeating_completed_Flash_or_JEV_controls':True,
 'old_control_hash_search_scope':['jev-defense-local-20261102','jev-defense-validation-20261103',
   'policy-preparation','observer-source-controls-1793973885537637041',
   'observer-server-requests-20261106-01','observer-real-preflight-20261106-01'],
 'old_control_image_hash_matches_in_searched_JSON':0,
 'actual_auxiliary_model':{'repo':'Qwen/Qwen3.5-9B','revision':'c202236235762e1c871ad0ccb60c8ee5ba337b9a',
   'JEV_package':'autotrust/JEV-9B','JEV_revision':'7ac669b8fb476ba926491e3d1c39f9330d68dbed',
   'native_JEV_relationship':'S2 shared original base without decision adapter',
   'decision_adapter_loaded':False,'decision_head_OCR_claim':False},
 'runtime_condition':{'planned_class':'Qwen3_5ForConditionalGeneration',
   'planned_backend':'Transformers native BF16/SDPA, distinct from official JEV vLLM S2 serving',
   'vLLM_bitwise_equivalence_claimed':False,'image_processing':'native AutoProcessor defaults; internal resizing retained',
   'enable_thinking':False,'greedy':True,'aux_output_cap':2048,
   'effective_EOS_pending_native_CPU_mapping':True},
 'budget':{'auxiliary_requests_max':8,'per_image_requests_max':2,
   'first_attempts':4,'format_retries_per_image_max':1,'semantic_resampling':False,
   'retry_completed_terminal':False,'inherited_unused_old_budget':False,
   'actor':0,'primary_judge':0,'GUI_actions':0,'scorer':0,'paid_API':0},
 'relationship_to_12_image_proposal':'First capability stage within its 24 auxiliary request cap; not replacement or completion of the critical 12-slot validation plan',
 'all_four_originals_and_source_bindings_frozen_before_prediction':True,
 'independent_image_labels_required_before_GPU_prediction':True,
 'critical_loading_footer_no_results_and_history_controls_completed':False,
 'four_card_joint_capacity_proven':False,
 'formal_GUI_launch_ready':False,'GPU_launch_ready':False,
 'GPU_gates_pending':['native_CPU_input_proof','independent_source_labels',
   'actual_fresh_ownership_and_all_inherited_locks','new_once_only_GPU_worker_and_launcher',
   'effective_generation_and_stop_rules_freeze','current_weight_identity_admission'],
 'source_bindings_sha256':sha(OUT/'source-bindings.json'),
 'evidence_contract_source_sha256':sha(ROOT/'evidence-contract/image_evidence.py'),
 'fixed_prompt_sha256':hashlib.sha256(contract.FIXED_PROMPT.encode('utf-8')).hexdigest(),
 'known_limit':'Four readable original frames test basic literal visual reading, not all critical negative/WAIT controls or Mirage reduction.'}
write(OUT/'protocol.json',protocol)
write(OUT/'seal.json',{p.name:sha(p)for p in OUT.iterdir()if p.is_file()})
print(json.dumps({'status':protocol['status'],'images':len(records),'protocol_sha256':sha(OUT/'protocol.json'),
                  'seal_sha256':sha(OUT/'seal.json')}))
