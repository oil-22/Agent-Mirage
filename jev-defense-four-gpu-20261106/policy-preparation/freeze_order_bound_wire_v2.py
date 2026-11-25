"""Linked stronger transport binding: exact bytes preserve native option order."""
import json
from pathlib import Path

from defense.core import canonical, digest
from flash_policy import REVISION

BASE=Path(__file__).resolve().parent


def checked(root):
    entries=json.loads((root/'seal.json').read_bytes())
    for name,expected in entries.items():assert digest((root/name).read_bytes())==expected,name


def finish(root):
    (root/'seal.json').write_text(json.dumps({str(p.relative_to(root)).replace('\\','/'):digest(p.read_bytes())
        for p in root.rglob('*')if p.is_file()},indent=2),encoding='utf8')


def main():
    prior=BASE/'flash-preflight-frozen-01';checked(prior)
    root=BASE/'flash-preflight-frozen-02';root.mkdir(exist_ok=False);(root/'wire').mkdir();(root/'images').mkdir()
    plan=json.loads((prior/'plan.json').read_bytes());admission=[]
    for row in plan['requests']:
        body=json.loads((prior/row['request']).read_bytes())
        assert digest(canonical(body))==row['fingerprint_excluding_request_id']
        body={'request_id':digest(canonical([REVISION,row['case_id'],row['fingerprint_excluding_request_id']]))[:32],**body}
        raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        name='wire/'+row['case_id']+'.json';(root/name).write_bytes(raw)
        row['wire']=name;row['wire_sha256']=digest(raw);row['native_option_order']=list(body['options'])
        row['source_request_file']=row.pop('request')
        admission.append({'case_id':row['case_id'],'fingerprint':row['fingerprint_excluding_request_id'],
                          'wire_sha256':digest(raw)})
    for path in (prior/'images').iterdir():(root/'images'/path.name).write_bytes(path.read_bytes())
    plan['linked_parent_seal_sha256']=digest((prior/'seal.json').read_bytes())
    plan['transport_binding']='exact raw bytes, including fixed request ID and native option order'
    (root/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    (root/'server-admission.json').write_text(json.dumps({'mode':'preflight','max_new_calls':19,
        'GUI_actions':0,'requests':admission},indent=2),encoding='utf8')
    for name in ['active-prompt-disclosure.json','gui-single-flash-config.proposed.json']:
        (root/name).write_bytes((prior/name).read_bytes())
    finish(root)
    prior_primary=BASE/'primary-capacity-frozen-01';checked(prior_primary)
    primary=BASE/'primary-capacity-frozen-02';primary.mkdir(exist_ok=False)
    raw=(prior_primary/'request.json').read_bytes();body=json.loads(raw)
    (primary/'request.json').write_bytes(raw)
    plan=json.loads((prior_primary/'plan.json').read_bytes())
    plan.update(linked_parent_seal_sha256=digest((prior_primary/'seal.json').read_bytes()),
                request_wire_sha256=digest(raw),transport_binding='exact raw bytes')
    (primary/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    (primary/'server-admission.json').write_text(json.dumps({'mode':'capacity_preflight','max_new_calls':1,
        'GUI_actions':0,'requests':[{'case_id':'w08-full-input-new-layout-capacity',
         'fingerprint':digest(canonical(body)),'wire_sha256':digest(raw)}]},indent=2),encoding='utf8')
    finish(primary)
    print(json.dumps({'Flash':str(root),'primary':str(primary),'Flash_call_cap':19,
        'primary_call_cap':1,'primary_wire_sha256':digest(raw),'model_calls':0}))


if __name__=='__main__':main()
