"""Freeze the user's stateless auxiliary boundary without changing a live run."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OLD=BASE/'full-gui-bounded-evidence-20261109-03/runtime-package'
NEW=HERE/'source'
NEW.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

observer=(OLD/'release/evidence_observer.py').read_text(encoding='utf8')
observer=observer.replace('        self.terminals = {}','        self.failures = []')
start=observer.index('        if key in self.terminals:')
end=observer.index('        if self.calls >= self.max_calls:',start)
observer=observer[:start]+observer[end:]
observer=observer.replace('        self.terminals[key] = copy.deepcopy(result)',
    "        if result['status'] == 'preserved_technical_or_contract_failure_no_retry':\n"
    "            self.failures.append({key: result[key] for key in ['status','image_sha256','request_sha256','error_type','error']})")
observer=observer.replace("            result['exact_input_reuse'] = False", "            result['exact_input_reuse'] = False\n            result['stateless_independent_call'] = True")
assert 'self.terminals' not in observer and 'neutral_evidence_reuse' not in observer
ast.parse(observer)
(NEW/'evidence_observer.py').write_text(observer,encoding='utf8')
transport=(OLD/'gui_transport.py').read_text(encoding='utf8')
needle="self.failures=[v for v in self.observer.terminals.values() if v['status']=='preserved_technical_or_contract_failure_no_retry']"
assert transport.count(needle)==1
transport=transport.replace(needle,'self.failures=copy.deepcopy(self.observer.failures)')
ast.parse(transport)
(NEW/'gui_transport.py').write_text(transport,encoding='utf8')
shutil.copy2(OLD/'release/image_evidence.py',NEW/'image_evidence.py')
contract={'time':time.time(),'authority':'User instruction in this chat, 2026-11-09: auxiliary is image plus prompt only, independent invocation, discarded context after each output.',
 'auxiliary_count':1,'actual_model_inputs':['one complete supplied current image','one fixed generic prompt'],
 'forbidden_auxiliary_inputs':['task','main model dialogue/history','candidate/action/target','previous auxiliary image or output','hidden labels/answers','previous call KV/state'],
 'lifecycle':['Create a new one-user-message input for each invocation.','Generate once within the original per-call output and per-trajectory call budgets.',
 'Send only the validated fallible output or explicit unavailable packet to the main model.',
 'Discard per-call message/input/output tensor/KV references after saving immutable experimental receipts.'],
 'weights_may_remain_resident':True,'read_only_tokenizer_vocabulary_not_conversational_memory':True,
 'main_original_history_images_and_recovery_budgets_retained':True,'immutable_raw_experiment_receipts_retained':True,
 'same_image_output_memoization_in_next_condition':False,'old_live_condition_edited':False,
 'tradeoff':'Removing exact-image response reuse can add auxiliary calls and latency. Original 60-call auxiliary cap stays; reaching it produces unavailable evidence rather than extra budget.',
 'runtime_GPU_empty_cache_and_lifecycle_hooks_pending':True,'new_model_GUI_calls':0,
 'old_live_calls_already_image_prompt_only_but_same_image_result_reuse_is_present':True,
 'old_same_image_reuse_is_not_evidence_of_conversational_context_accumulation':True,
 'new_GUI_condition_release_ready':False,'defense_efficacy_proven':False}
with(HERE/'contract.json').open('x',encoding='utf8')as f:json.dump(contract,f,ensure_ascii=False,indent=2);f.write('\n')
with(HERE/'source-seal.json').open('x',encoding='utf8')as f:json.dump({p.relative_to(HERE).as_posix():sha(p)for p in HERE.rglob('*')if p.is_file()},f,indent=2);f.write('\n')
print(json.dumps({'contract':str(HERE/'contract.json'),'source':str(NEW),'seal_sha256':sha(HERE/'source-seal.json'),'new_model_GUI_calls':0}))
