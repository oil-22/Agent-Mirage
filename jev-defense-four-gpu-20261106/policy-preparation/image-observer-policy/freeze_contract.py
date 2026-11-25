"""Freeze the neutral observer constants without any model or GUI operation."""
import json
from pathlib import Path
from image_observer import contract, wire, digest, SHARED_ACTOR_INSTRUCTIONS, POLICY, MODEL, REVISION

root=Path(__file__).resolve().parent
for name,raw in [('observer-contract.json',wire(contract())),
                 ('shared-actor-instructions.txt',SHARED_ACTOR_INSTRUCTIONS.encode())]:
    path=root/name
    if path.exists():
        assert path.read_bytes()==raw,'Refuse to replace frozen constants'
    else:path.write_bytes(raw)
receipt={'policy':POLICY,'model':MODEL,'revision':REVISION,
    'observer_contract_sha256':digest(wire(contract())),
    'shared_actor_instructions_sha256':digest(SHARED_ACTOR_INSTRUCTIONS.encode()),
    'question_order':list(contract()['questions']),
    'option_order':{k:list(v['criteria'])for k,v in contract()['questions'].items()},
    'observer_inputs':'one received screenshot plus constant state/questions only',
    'all_other_context_excluded':True,'joint_questions_per_forward':3,
    'native_decider':True,'free_caption_generation':False,'max_auxiliary_calls_per_trajectory':60,
    'baseline_same_shared_instructions':True,'judge_and_public_view_unchanged':True,
    'new_model_GUI_scorer_calls':0,'old_task_specific19_requests':'superseded_UNSENT',
    'model_probabilities_are_not_truth':True,'screenshot_cannot_establish_freshness':True}
path=root/'contract-receipt.json'
if path.exists():assert json.loads(path.read_bytes())==receipt
else:path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(receipt,ensure_ascii=False))
