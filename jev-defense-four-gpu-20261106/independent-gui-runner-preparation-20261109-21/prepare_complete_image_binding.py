"""Link complete accepted image history to unchanged strict judge transport."""
import ast
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
source=HERE/'prepared-source-linked02';target=HERE/'prepared-source-linked03'
assert not target.exists()
for name,expected in read(source/'seal.json').items():assert sha(source/name)==expected,name
helper=(source/'complete_actor_history.py').read_text(encoding='utf8')
assert helper.count('import copy\n')==1
helper=helper.replace('import copy\n','import base64\nimport copy\n')
method='''
    def reference_image_bytes(self, current_raw=None):
        """Return full past supplied bytes for strict image-index binding only.

        All original blocks, including duplicates, remain in actor messages.
        Duplicate byte-identities share an index in the verifier's image list.
        Current-image equality does not turn a prior frame into a fresh capture.
        """
        seen = set() if current_raw is None else {hashlib.sha256(current_raw).hexdigest()}
        references = []
        for message in self.messages:
            if not isinstance(message.get('content'), list):
                continue
            for block in message['content']:
                if block.get('type') != 'image_url':
                    continue
                url = block['image_url']
                url = url['url'] if isinstance(url, dict) else url
                if not isinstance(url, str) or not url.startswith('data:image/png;base64,'):
                    raise HistoryBindingError('Only the original embedded PNG history is accepted')
                raw = base64.b64decode(url.split(',', 1)[1], validate=True)
                identity = hashlib.sha256(raw).hexdigest()
                if identity not in seen:
                    references.append(raw)
                    seen.add(identity)
        return references

'''
needle='    def record_actual_reply(self, body, reply):\n'
assert helper.count(needle)==1
helper=helper.replace(needle,method+needle)
runner=(source/'run_independent_gui.py').read_text(encoding='utf8')
old="     return PublicView(f'{step:03}-obs{sequence:03}',msgs,()if raw is None else(VisibleImage(raw),),json.dumps(previous)if previous else'',execution_feedback)"
new="     references=tuple(VisibleImage(past,'reference')for past in transcript.reference_image_bytes(raw))\n     current=()if raw is None else(VisibleImage(raw,'current'),)\n     return PublicView(f'{step:03}-obs{sequence:03}',msgs,current+references,json.dumps(previous)if previous else'',execution_feedback)"
assert runner.count(old)==1
runner=runner.replace(old,new)
ast.parse(helper);ast.parse(runner)
target.mkdir()
for p in source.iterdir():
    if p.is_file()and p.name not in ['seal.json','preparation-receipt.json','run_independent_gui.py','complete_actor_history.py']:
        (target/p.name).write_bytes(p.read_bytes())
(target/'complete_actor_history.py').write_text(helper,encoding='utf8')
(target/'run_independent_gui.py').write_text(runner,encoding='utf8')
result={'time':time.time(),'source_preparation_only':True,'launch_ready':False,
        'parent_preparation_receipt_sha256':sha(source/'preparation-receipt.json'),
        'new_helper_sha256':sha(target/'complete_actor_history.py'),
        'new_runner_sha256':sha(target/'run_independent_gui.py'),
        'additional_binding':'Every accepted historical PNG message is bound to current or chronological historical-reference bytes for unchanged LocalQwen.judge image-index transport. Actor blocks are never dropped, resized or deduplicated.',
        'current_versus_reference_roles_preserved':True,'history_does_not_prove_current_state':True,
        'all_historical_original_message_characters_unchanged':True,
        'strict_validator_and_backend_not_modified':True,
        'new_GPU_model_GUI_scorer_calls':0,
        'full_native_CPU_wire_replay_and_GPU_capacity_still_required':True}
(target/'preparation-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(target/'seal.json').write_text(json.dumps({p.name:sha(p)for p in target.iterdir()if p.is_file()},indent=2)+'\n',encoding='utf8')
print(json.dumps({'prepared':str(target),'receipt_sha256':sha(target/'preparation-receipt.json'),'launch_ready':False}))
