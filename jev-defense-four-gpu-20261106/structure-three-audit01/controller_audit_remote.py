"""New read-only split audit, using original auditor function bodies unchanged.

The service side has already exhaustively verified every native request seal,
input/forward and native answer. Here exact Controller wires and raw responses
crossjoin those immutable service certificates. No native forwards are rerun.
"""
import base64,hashlib,importlib.util,json,sys,time,traceback
from pathlib import Path

B=Path('/data/researcher/jev-defense-four-gpu-20261106')
P=B/'gui-migration-three-linked02';C=B/'gui-outer-control-three-01'
G=B/'gui-batch-image-observer-three-01'
O=B/('three-controller-structural-audit-'+str(time.time_ns()))
O.mkdir(mode=0o700,exist_ok=False)
S=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,obj):
    with path.open('x',encoding='utf8')as f:json.dump(obj,f,ensure_ascii=False,indent=2)

try:
    audit_source=P/'terminal-auditor/audit_gui_terminals.py'
    assert S(audit_source)=='a93e4422dfecb0a48f855c0db2c8bdc9e0414b5624e840acc127864acb8905d7'
    spec=importlib.util.spec_from_file_location('bound_native_terminal_auditor',audit_source)
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    inputs=json.loads(base64.b64decode(INPUTS_BASE64))
    for label,src in inputs.items():
        (O/(label+'.json')).write_bytes(base64.b64decode(src))
    service=a.read(O/'service-receipt.json');cert=a.read(O/'request-certificates.json')
    rows=a.read(O/'request-audits.json');post=a.read(O/'postexit-report.json')
    terminal=a.read(O/'service-terminal-manifest.json')
    assert S(O/'service-receipt.json')=='ed32b419a92d671ffe2aebec0a69150ad8cf20b02bef407aa365bf78fcfcbff0'
    assert S(O/'postexit-report.json')=='d90bb52aec860bcc3ca418537543fe58fa50df795a7347995698a7ed92a666b2'
    assert S(O/'service-terminal-manifest.json')=='0f84fcfe8a7d51d899f5d73966bf6bcff799c4507cb10f890304a960f2795a17'
    assert post['all_actual_terminal_manifest_entries_verified']==len(terminal)==848
    assert post['original_request_and_transition_files_unchanged']is True
    assert post['actual_original_exit_codes']=={'primary':0,'pplx_flash':0}
    assert service['request_count']==len(cert)==len(rows)==119
    assert service['request_totals']=={'actor':24,'judge':73,'observer':20,'lifecycle':2}
    for name,h in a.read(O/'service-public-seal.json').items():
        local={'receipt.json':'service-receipt.json','request-certificates.json':'request-certificates.json','request-audits.json':'request-audits.json','service-journal.jsonl':'service-journal.json','online-state.json':'online-state.json','loaded.json':'loaded.json'}.get(name)
        if local:assert S(O/local)==h
    plan_path=P/'plan.json';plan=a.read(plan_path)
    assert S(plan_path)=='838c63ac36560040df0c9257f4080d7c5ef33e7a0858f9b42bbdb73f486a2cef'
    a.validate_three_plan(plan)
    migration=P/'three-trajectory-migration-source.json'
    assert S(migration)=='443c8570927e996779c08eaf91d124da48c54866bc06b9d2035f42281b65dd8a'
    a.validate_migration_source(a.read(migration))
    source=a.read(P/'policy-source-seal.json')
    assert source['plan_sha256']==S(plan_path)
    for name,h in source['release_sha256'].items():assert S(a.under(P/'release',name))==h
    launch=a.read(B/'gui-final-readiness-three-01/launch-spec.json')
    assert S(B/'gui-final-readiness-three-01/launch-spec.json')=='506eda3ea06600c6a3ca8baecc6f88e1310e910b24efb1dcd769b58d2602e252'
    sealed=[]
    for root,path,h in [(C,C/'postexit-sha256.json','8769e439de67ae3896e95b4f0668cd608c6a361d8ed2be516505e91bd9b1b623'),(G,C/'batch-postexit-sha256.json','27fbebad64fca197259eae133a72c76e2dba934997472cd4242ca88a7db7fa80')]:
        m=a.manifest(root,path,h,True);sealed.append({'root':str(root),'files':len(m),'manifest_sha256':h})
    admission=a.read(O/'online-admission.json')
    assert admission['plan_sha256']==S(plan_path)
    assert admission['run_order']==[q['run_id']for q in plan['queue']]
    assert set(admission['per_run_caps'])==set(admission['run_order'])
    for item in plan['queue']:
        assert admission['per_run_caps'][item['run_id']]=={'actor':70,'judge':140,'observer':60 if item['observer_enabled']else 0,'steps':50}
    index={};index_by_name={};runs=[]
    # Original Controller event chains are read directly; certificate stubs live
    # only inside this NEW audit output and retain original response/seal bytes.
    for item in plan['queue']:
        run=G/'runs'/item['run_id'];attempts=list(run.glob('attempt-*'))
        assert len(attempts)<=1
        for attempt in attempts:
            events,head=a.chain(attempt/'events.jsonl')
            for event in events:
                if event['kind']not in {'actual_primary_wire_request','actual_observer_wire','online_run_begin_request','online_run_end_request'}:continue
                d=event['data'];raw=d['wire_utf8'].encode();wire=a.sha(raw)
                assert wire in cert and wire not in index
                c=cert[wire];envelope=json.loads(raw)
                assert wire==c['request_sha256']
                if'payload'in envelope:assert a.sha(a.canonical(envelope['payload']))==c['payload_sha256']
                path=O/'service-certificate-stubs'/c['request_name'];path.mkdir(parents=True,exist_ok=False)
                (path/'seal.json').write_bytes(base64.b64decode(c['request_seal_raw_base64']))
                (path/'response.json').write_bytes(base64.b64decode(c['response_raw_base64']))
                response=a.read(path/'response.json');assert response['external_wire_sha256']==wire
                original=next(r for r in rows if r['wire_sha256']==wire)
                assert S(path/'seal.json')==original['request_seal_sha256']and S(path/'response.json')==original['response_file_sha256']
                # Bind exact stub hashes to the actual original terminal map.
                rel=original['path'].split('/online-three-service-group-1793985778592347799/',1)[1]
                assert terminal[rel+'/seal.json']==S(path/'seal.json')
                assert terminal[rel+'/response.json']==S(path/'response.json')
                assert terminal[rel+'/request.json']==wire
                index[wire]={'path':path,'raw':raw,'envelope':envelope,'response':response,'role':c['role'],'used':False}
                index_by_name[path.name]=c
    assert set(index)==set(cert)
    def certificate_native_forward(request,payload,response,role):
        c=index_by_name[request.name]
        assert c['role']==role
        assert a.sha(a.canonical(payload))==c['payload_sha256']
        assert response==a.read(request/'response.json')
        assert c['native_forward_audit']is not None
        return c['native_forward_audit']
    a.native_forward=certificate_native_forward
    # Invoke the unchanged original audit_attempt body and original journal join.
    for item in plan['queue']:
        run=G/'runs'/item['run_id'];attempts=list(run.glob('attempt-*'))
        if not attempts:
            runs.append({'run_id':item['run_id'],'status':'not_attempted','actual_calls':0});continue
        attempt=attempts[0];r=a.audit_attempt(attempt,item,index)
        r.update(run_id=item['run_id'],attempt=str(attempt));runs.append(r)
        assert not r['complete']
        failure=attempt/'technical-failure.json';f=a.read(failure)
        assert S(failure)=='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
        assert f['actor_calls']==r['counts']['actor']==24
        assert f['verifier_calls']==r['counts']['judge']==73
        assert f['auxiliary_calls']==r['counts']['observer']==20
        assert f['environment_actions']==r['actual_execution_log_count']==19
        assert f['run']==item and f['observer_enabled']==item['observer_enabled']
        assert f['semantic_mirage']is None and f.get('repair_success')is None
        assert f['step_cap']==50
        save(O/'technical-terminal-original.json',f)
        events,head=a.chain(attempt/'events.jsonl')
        packets=[e for e in events if e['kind']=='actor_observer_packet']
        assert len(packets)==24
        r['observer_packets']=len(packets);r['same_response_reuses']=len(packets)-len({e['data']['response_sha256']for e in packets if e['data'].get('observations')})
        assert r['same_response_reuses']==4
        assert r['event_count']==1103 and r['event_chain_head']=='c120b3b6ea1a739a91b29726628995a0a35703ed6b8514b55fe7a7c8a6748b20'
    assert all(r['used']for r in index.values())
    service_journal=O/'service-journal.json';jr,jh=a.service_chain(service_journal)
    assert S(service_journal)==service['service_journal_file_sha256']
    assert terminal['journal.jsonl']==S(service_journal)
    join=a.join_service_journal(jr,index)
    state=a.read(O/'online-state.json')
    assert terminal['online-state.json']==S(O/'online-state.json')
    assert state['phase']=='terminal_failure'and state['active']is None
    for item in plan['queue'][1:]:
        s=state['runs'][item['run_id']]
        assert s['status']=='not_started'and all(v==0 for v in s['calls'].values())and s['last_decision_index']==0
    result={'integrity_audit_passed':True,'audit_mode':'split native service verification then unchanged original Controller audit_attempt and join_service_journal using exact-wire certificates','original_auditor_source_sha256':S(audit_source),'source_manifest_verified':True,'sealed_roots':sealed,'original_service_terminal_manifest_sha256':S(O/'service-terminal-manifest.json'),'original_service_terminal_files':len(terminal),'runs':runs,'service_request_count':len(index),'service_journal_event_count':len(jr),'service_journal_chain_head':jh,'service_journal_actual_request_terminal_join':join,'technical_terminal_counters_original_budget_verified':True,'two_stale_runs_zero_calls_unstarted':True,'all_three_trajectories_complete':False,'semantic_labels_inferred':False,'Mirage_trigger_rate_or_defense_success_claim':False,'new_model_GPU_GUI_health_scorer_calls':0,'original_terminal_not_modified':True,'scope':'actual pixel tensor shape/hash and original image/message bindings, no independent pixel processor reencoding'}
    save(O/'audit.json',result)
    (O/'controller_audit_remote.py').write_bytes(Path(__file__).read_bytes())
    save(O/'seal.json',{p.relative_to(O).as_posix():S(p)for p in O.rglob('*')if p.is_file()})
    names=['audit.json','seal.json','technical-terminal-original.json']
    print(json.dumps({'root':str(O),'audit_sha256':S(O/'audit.json'),'seal_sha256':S(O/'seal.json'),'files':{n:base64.b64encode((O/n).read_bytes()).decode()for n in names}}))
except BaseException:
    save(O/'failure.json',{'error':traceback.format_exc(),'new_model_GPU_GUI_health_calls':0})
    print(json.dumps({'root':str(O),'failure':a.read(O/'failure.json')if'a'in globals()else(O/'failure.json').read_text()}))
    raise
