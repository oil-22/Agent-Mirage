"""Copy only sealed first observer/actor/judge public receipts. No pending reads/locks."""
import base64,hashlib,json,os
from pathlib import Path
import time

B=Path('/home/researcher/jev-defense-four-gpu-20261106')
G=B/'online-three-service-group-1793985778592347799'
ROOT=B/'first-online-observer-engineering'/str(time.time_ns());ROOT.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
bindings=[]


def copy(p,name):
    before=(p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ino);digest=sha(p)
    target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb')as f:f.write(p.read_bytes())
    assert before==(p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ino)and sha(p)==digest==sha(target)
    bindings.append({'source':str(p),'copy':name,'sha256':digest})


def sealed(request,prefix):
    mapping=read(request/'seal.json')
    assert 'seal.json'not in mapping
    assert set(mapping)=={p.name for p in request.iterdir()if p.is_file()and p.name!='seal.json'}
    for name,expected in mapping.items():assert sha(request/name)==expected;copy(request/name,prefix+'/'+name)
    copy(request/'seal.json',prefix+'/seal.json')


try:
    choices=[]
    for p in(G/'pplx_flash/requests').iterdir():
        if not(p/'seal.json').exists():continue
        body=read(p/'request.json')
        if body['attempt_index']==1:choices.append((p,body))
    assert len(choices)==1
    request,envelope=choices[0];assert envelope['decision_index']==1
    assert envelope['trajectory_id']=='image-observer-v1--classifieds_112--clean--joint--observer'
    payload=envelope['payload'];assert set(payload)=={'request_id','image_base64','image_sha256','state','questions','provenance'}
    assert set(payload['provenance'])=={'observation_id','image_sha256'}
    sealed(request,'observer-request');response=read(request/'response.json')
    assert response['status']=='ok'and response['request_id']==envelope['request_id']
    assert response['external_wire_sha256']==sha(request/'request.json')
    assert response['payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest()
    actors=[];judges=[]
    for p in(G/'primary/requests').iterdir():
        if not(p/'seal.json').exists():continue  # Never read current pending request contents.
        body=read(p/'request.json')
        if body['decision_index']!=1 or body['trajectory_id']!=envelope['trajectory_id']:continue
        if body['payload']['operation']=='actor'and body['attempt_index']==1:actors.append((p,body))
        if body['payload']['operation']=='judge':judges.append((p,body))
    assert len(actors)==1 and judges
    actor,actor_envelope=actors[0];sealed(actor,'actor-request')
    for p,body in sorted(judges,key=lambda x:x[1]['attempt_index']):sealed(p,'judge-requests/'+str(body['attempt_index']))
    config=read(G/'runtime-config.json')
    copy(G/'runtime-config.json','runtime-config.json')
    for role in('primary','pplx_flash'):copy(G/role/'loaded.json','load/'+role+'.json')
    copy(Path(config['flash_observer_contract']),'observer-contract.json')
    for name,raw in AUDIT_SOURCES.items():
        path=ROOT/'auditor-source'/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb')as f:f.write(base64.b64decode(raw))
    snapshot=(G/'journal.jsonl').read_bytes();lines=snapshot.splitlines()
    if snapshot and not snapshot.endswith(b'\n'):lines=lines[:-1]
    previous=None;events=[]
    for i,line in enumerate(lines):
        row=json.loads(line);content={k:v for k,v in row.items()if k!='sha256'}
        assert row['index']==i and row['previous_sha256']==previous and row['sha256']==hashlib.sha256(canonical(content)).hexdigest()
        previous=row['sha256'];events.append(row)
    with(ROOT/'service-journal-prefix.jsonl').open('xb')as f:f.write(b'\n'.join(lines)+b'\n')
    proof={'status':'sealed_first_request_collected','group':str(G),'root':str(ROOT),
        'observer_request':str(request),'observer_request_seal_sha256':sha(request/'seal.json'),
        'actor_request':str(actor),'actor_request_seal_sha256':sha(actor/'seal.json'),
        'judge_request_count_decision1_sealed':len(judges),'observer_external_wire_sha256':sha(request/'request.json'),
        'observer_response_canonical_sha256':hashlib.sha256(canonical(response)).hexdigest(),
        'actor_external_wire_sha256':sha(actor/'request.json'),'service_journal_prefix_events':len(events),
        'service_journal_head':previous,'pending_requests_not_read':True,
        'no_inference_mutex_acquired':True,'model_health_GUI_POST_PRIVATE_reads':0,'bindings':bindings}
    with(ROOT/'collection.json').open('x')as f:json.dump(proof,f,indent=2)
    print(json.dumps(proof))
except BaseException:
    import traceback
    with(ROOT/'collection-failure.json').open('x')as f:json.dump({'error':traceback.format_exc(),'no_model_health_GUI_POST_calls':True},f,indent=2)
    raise
