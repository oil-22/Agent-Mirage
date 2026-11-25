"""Compare a failed CPU token path with original schema; no generation or repair."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(PREVIOUS))
from orchestrate import remote, save, OUTPUT


SOURCE = r'''
from pathlib import Path
import copy,hashlib,json,os,sys
from types import SimpleNamespace
os.environ['CUDA_VISIBLE_DEVICES']=''
root=Path(ROOT);reference=json.loads((root/'primary-reference.json').read_bytes())
proof_path=Path(reference['primary_dependency_receipt'])
assert hashlib.sha256(proof_path.read_bytes()).hexdigest()==reference['primary_dependency_receipt_sha256']
proof=json.loads(proof_path.read_bytes());deps=Path(proof['dependency_root'])
actual={str(p.relative_to(deps)):hashlib.sha256(p.read_bytes()).hexdigest()for p in deps.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
assert actual==proof['dependency_files']
sys.path[:0]=[str(deps),str(root/'proposed-release')]
from defense.schema import judge_schema
from source_quote_references import source_index
from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data,build_transformers_prefix_allowed_tokens_fn
from transformers import AutoTokenizer
import torch
p=Path(ORIGINAL)/'worker/requests/0074'
payload=json.loads((p/'payload.json').read_bytes());native=json.loads((p/'native-call.json').read_bytes())
view=SimpleNamespace(**{k:payload['view'][k]for k in['messages','images','observation_id']})
candidate=payload['candidate'];rows=source_index(candidate)['rows']
new_schema=judge_schema(view,candidate,phase='exact_source_reference');old_schema=native['verifier_grammar']['schema']
tokenizer=AutoTokenizer.from_pretrained(reference['primary_model'],local_files_only=True,trust_remote_code=True)
data=build_token_enforcer_tokenizer_data(tokenizer)
value=dict(claims=[dict(id='c1',kind='gui_fact',quote_id=rows[0]['quote_id'],status='uncertain',evidence=[],reason='Source ID is not truth proof.',dependent_decisions=['completion'])],action=dict(status='insufficient',target_kind='not_applicable',reason='No completion approval in this CPU control.',evidence=[]),acknowledges_visual_deficit=False,pure_wait=False)
reports=[]
for label,branch,schema in[('new',copy.deepcopy(value),new_schema),('old',copy.deepcopy(value),old_schema)]:
 if label=='old':branch['claims'][0]['text']=rows[0]['text'];del branch['claims'][0]['quote_id']
 for encoding in['compact','spaced','character_tokens']:
  text=json.dumps(branch,separators=(',',':'))if encoding!='spaced'else json.dumps(branch)
  ids=tokenizer.encode(text,add_special_tokens=False)if encoding!='character_tokens'else sum([tokenizer.encode(c,add_special_tokens=False)for c in text],[])
  assert tokenizer.decode(ids,skip_special_tokens=True)==text
  prefix=list(native['input_ids']);constrain=build_transformers_prefix_allowed_tokens_fn(data,JsonSchemaParser(schema))
  failure=None
  for index,token in enumerate(ids):
   allowed=constrain(0,torch.tensor(prefix,dtype=torch.long))
   if token not in allowed:
    decoded=tokenizer.decode(ids[:index],skip_special_tokens=True)
    state=JsonSchemaParser(schema)
    for char in decoded:
     assert char in state.get_allowed_characters(),('prior-prefix-character-invalid',char)
     state=state.add_character(char)
    failure=dict(index=index,token=token,token_text=tokenizer.decode([token]),vocab=tokenizer.convert_ids_to_tokens(token),prefix_tail=decoded[-120:],character_parser_allowed=state.get_allowed_characters(),allowed_token_count=len(allowed),allowed_sample=[dict(id=x,text=tokenizer.decode([x]))for x in allowed[:12]])
    break
   prefix.append(token)
  reports.append(dict(label=label,encoding=encoding,accepted=failure is None,token_count=len(ids),failure=failure))
assert not torch.cuda.is_initialized()
print(json.dumps(dict(results=reports,no_weights_CUDA_model_GUI_or_scorer=True),ensure_ascii=True))
'''


def main():
    assert not (HERE / 'native-token-path-diagnostic.json').exists()
    source = json.loads((HERE / 'native-CPU-submission.json').read_bytes())
    code = 'ROOT=' + repr(source['remote_root']) + '\nORIGINAL=' + repr(OUTPUT) + '\n' + SOURCE
    output, operation = remote('3090', code, 'diagnose-native-reference-and-original-token-paths-CPU-only', timeout=55)
    value = json.loads(output)
    save(HERE / 'native-token-path-diagnostic.json', dict(value=value, operation=str(operation)))
    print(json.dumps(value))


if __name__ == '__main__':
    main()
