"""Seal current linked GUI source and exact disclosed prompts, no launch."""
import json
from pathlib import Path
from image_observer import digest,contract,wire,SHARED_ACTOR_INSTRUCTIONS
from defense import prompts
BASE=Path(__file__).resolve().parent
release=BASE/'gui-release-04'
receipt=BASE/'cpu-evidence'/'1793974822119208200'/'receipt.json'
cpu=json.loads(receipt.read_bytes());assert cpu['tests_passed']and cpu['test_count']==23
for name,sha in cpu['source_sha256'].items():assert digest((BASE/name).read_bytes())==sha,name
old=json.loads((BASE.parent/'flash-preflight-frozen-02'/'active-prompt-disclosure.json').read_bytes())
for name,row in old['potentially_active_unbound_prompts'].items():
    assert getattr(prompts,name)==row['current_text']
    assert digest(row['current_text'].encode())==row['sha256']
old.update(current_exact_texts_and_hashes_frozen=True,historical_binding_not_claimed=True,
    current_prompts_source_sha256=digest((release/'defense/prompts.py').read_bytes()),
    condition_disclosure='New linked GUI pilot uses the exact disclosed recovered current bytes; no historical identity or invented historical difference is claimed.',
    original_primary_validator_unchanged=True)
with (BASE/'current-prompt-disclosure-04.json').open('x',encoding='utf8')as f:json.dump(old,f,ensure_ascii=False,indent=2)
files={str(p.relative_to(release)).replace('\\','/'):digest(p.read_bytes())for p in release.rglob('*.py')if '__pycache__'not in p.parts}
obj={'active_gui_release':str(release),'release_sha256':files,
     'plan_sha256':digest((BASE/'gui-plan.json').read_bytes()),
     'observer_contract_sha256':digest(wire(contract())),
     'shared_actor_instructions_sha256':digest(SHARED_ACTOR_INSTRUCTIONS.encode()),
     'cpu_receipt':str(receipt),'cpu_receipt_sha256':digest(receipt.read_bytes()),
     'current_prompt_disclosure_sha256':digest((BASE/'current-prompt-disclosure-04.json').read_bytes()),
     'new_model_GUI_calls':0,'launch_ready':False,
     'inactive_drafts':['gui-release','gui-release-02','gui-release-03'],
     'actual_runtime_gate_requires_real_preflight_and_parent_review':True}
with (BASE/'policy-source-seal-04.json').open('x',encoding='utf8')as f:json.dump(obj,f,indent=2)
print(json.dumps({'release':str(release),'source_files':len(files),
    'source_seal_sha256':digest((BASE/'policy-source-seal-04.json').read_bytes()),
    'plan_sha256':obj['plan_sha256'],'model_calls':0}))
