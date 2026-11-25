"""New sources and native processor admission; no model inference or old retries."""
import hashlib,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'compact-four-image-inputs-02'
CPU=ROOT/'native-auxiliary-admission-compact02'
IDS=['S04','S10','S16','S19']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

OUT.mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('compact',ROOT/'compact-evidence-02/image_evidence.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
assert sha(ROOT/'compact-evidence-02/image_evidence.py')=='081caa2595440dd1f813efaa4f960a78cd095b8448353d65a11f464593140676'
source=ROOT/'source-discovery-linked03'
inventory=json.loads((source/'inventory.json').read_bytes())
rows=[]
for item in inventory:
    if item['id']not in IDS:continue
    image=source/item['image_path']
    assert sha(image)==item['image_sha256']
    assert sha(source/item['source_path'])==item['original_source_artifact_sha256']
    request=c.build_image_only_request(image.read_bytes(),'Qwen/Qwen3.5-9B','c202236235762e1c871ad0ccb60c8ee5ba337b9a')
    path=OUT/(item['id']+'-request.json');write(path,request)
    rows.append(dict(item,request_path=path.name,request_sha256=sha(path),native_model_receives_only=['original_full_image','fixed_generic_visual_prompt']))
assert [r['id']for r in rows]==IDS
assert len({r['image_sha256']for r in rows})==4
write(OUT/'source-bindings.json',rows)
write(OUT/'protocol.json',{
    'stage':'new_compact_image_evidence_development_02','status':'inputs_frozen_before_new_prediction',
    'image_ids':IDS,'image_count':4,'selection':'Different archived early original per Chrome, Writer options, Calc and Impress; fixed before compact outputs; source-first notes separately sealed.',
    'not_random_or_blind':True,'source_export_not_claimed_full_wire':True,
    'old_first_four_terminal_preserved_not_rerun':True,
    'source_bindings_sha256':sha(OUT/'source-bindings.json'),
    'evidence_contract_source_sha256':sha(ROOT/'compact-evidence-02/image_evidence.py'),
    'fixed_prompt_sha256':hashlib.sha256(c.FIXED_PROMPT.encode()).hexdigest(),
    'runtime_condition':{'model':'Qwen/Qwen3.5-9B','revision':'c202236235762e1c871ad0ccb60c8ee5ba337b9a',
        'JEV_relationship':'S2-shared-base-without-decision-adapter','BF16':True,'backend':'SDPA',
        'enable_thinking':False,'max_new_tokens':2048,'eos_token_id':[248044,248046],'seed':0,'greedy':True},
    'budget':{'first_attempts':4,'format_retries':0,'prior_phase_actual_aux_calls':4,'cumulative_if_complete':8,
        'parent_auxiliary_cap':24,'actor':0,'judge':0,'GUI':0,'scorer':0,'paid_API':0},
    'changed_conditions':['bounded compact output 6 texts/6 elements/2 uncertain regions','single lossless explicit JSON fence accepted'],
    'tradeoff':'Lower coverage; omitted items never prove absence. No semantic fields edited or partial nonEOS accepted.',
    'full_critical_controls_completed':False,'formal_GUI_launch_ready':False})
write(OUT/'seal.json',{p.name:sha(p)for p in OUT.iterdir()if p.is_file()})
CPU.mkdir(exist_ok=False)
old=ROOT/'native-auxiliary-admission-01'
worker=(old/'native_image_admission.py').read_text(encoding='utf8')
worker=worker.replace("VERSION='native-image-admission-staged-20261107-01'","VERSION='native-image-admission-compact-20261107-02'")
worker=worker.replace("CONTRACT_SHA256='91422a0ac55e6cdd972580dc57424bef0c7f25cefc59885389aa7df48c0c549d'","CONTRACT_SHA256='081caa2595440dd1f813efaa4f960a78cd095b8448353d65a11f464593140676'")
(CPU/'native_image_admission.py').write_text(worker,encoding='utf8',newline='\n')
helper=(old/'prepare_and_run_four_cpu_linked02.py').read_text(encoding='utf8')
helper=helper.replace("LOCAL=HERE/'cpu-native-four-linked02'","LOCAL=HERE/'cpu-native-compact-four-02'")
helper=helper.replace('single-evidence-native-auxiliary-01','single-evidence-compact-native-02')
helper=helper.replace("REVISION/'four-image-inputs-01'","REVISION/'compact-four-image-inputs-02'")
helper=helper.replace('e3d639011de4cda5598be09645e377d7c2dd5220ec185835348044a08b6f6d12',sha(OUT/'protocol.json'))
helper=helper.replace("REVISION/'evidence-contract/image_evidence.py'","REVISION/'compact-evidence-02/image_evidence.py'")
helper=helper.replace("['S01','S07','S13','S25']",repr(IDS))
helper=helper.replace('native-aux-four-cpu-linked02','native-aux-compact-four-cpu-02')
(CPU/'prepare_and_run_compact_cpu.py').write_text(helper,encoding='utf8',newline='\n')
write(CPU/'source-change-receipt.json',{'old_worker_sha256':sha(old/'native_image_admission.py'),
    'new_worker_sha256':sha(CPU/'native_image_admission.py'),
    'worker_changes_only':['VERSION','CONTRACT_SHA256'],'helper_new_namespace_and_four_sources':True,
    'input_package_seal_sha256':sha(OUT/'seal.json'),'no_model_or_GPU_calls':True})
print(json.dumps({'new_input_seal_sha256':sha(OUT/'seal.json'),'CPU_source':str(CPU)}))
