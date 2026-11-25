"""Actual installed character parser controls, no model or GPU access."""
import sys,json
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);sys.path.insert(1,'/home/researcher/mirage-defense-pilot-20261023/repair-deps-v2')
from lmformatenforcer import JsonSchemaParser
from defense.schema import judge_schema
view=SimpleNamespace(observation_id='fixture',images=[],messages=[{'role':'user','content':'Task'},{'role':'assistant','content':'Prior record'}])
schema=judge_schema(view,'query',phase='history_report')
def accepts(value):
    parser=JsonSchemaParser(schema)
    for char in value:
        if char not in parser.get_allowed_characters():return False
        parser=parser.add_character(char)
    return parser.can_end()
controls={}
valid={'status':'supported','reason':'record relation','evidence':[{'message_index':1,'span_id':'full'}]}
controls['supported_actor_source']=accepts(json.dumps(valid))
for status in ['insufficient','uncertain','contradicted']:
    controls[status+'_available']=accepts(json.dumps({**valid,'status':status}))
controls['unknown_without_evidence']=accepts(json.dumps({'status':'insufficient','reason':'unknown','evidence':[]}))
controls['candidate_cannot_self_prove']=not accepts(json.dumps({**valid,'evidence':[{'source':'candidate','span_id':'full'}]}))
controls['task_cannot_prove_record']=not accepts(json.dumps({**valid,'evidence':[{'message_index':0,'span_id':'full'}]}))
controls['no_gui_claims']=not accepts(json.dumps({**valid,'claims':['invented']}))
controls['no_wait_flag']=not accepts(json.dumps({**valid,'pure_wait':False}))
print(json.dumps({'passed':all(controls.values()),'controls':controls,'scope':'Installed grammar syntax/source controls only, no semantic inference'}))
assert all(controls.values())
