"""New group source/load/resource audit. Optional once-only GET after all checks.

No model imports, launches, inference POST, browser or scorer. This auditor binds
the worker's actual CUDA audit to the completed exact-input capacity evidence;
it does not attach to live tensor values or claim numerical equivalence.
"""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')
GROUP=BASE/'online-three-service-group-1793985778592347799'
PREP=BASE/'online-three-source-preparation/1793985778592347799'
SOURCE=BASE/'runtime-preparation/gui-three-linked02-1793985778592347799'
CAPACITY=BASE/'failed-input-capacity-group-1793984469336572715'
SPEC_SHA='233850b6bf6ecac89fbd18452c592a5b2481eeee9f5eaf6eea8b9af23c083e8c'
ROOT=BASE/'online-three-independent-audits'/str(time.time_ns())
ROOT.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
http_counts={'primary':0,'pplx_flash':0}
bindings=[]


def save(name,value):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as f:json.dump(value,f,indent=2)


def copy(path,name):
    path=Path(path);before=(path.stat().st_size,path.stat().st_mtime_ns,path.stat().st_ino)
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb')as f:f.write(raw)
    assert before==(path.stat().st_size,path.stat().st_mtime_ns,path.stat().st_ino)
    assert sha(path)==digest and sha(target)==digest
    bindings.append({'source':str(path),'copy':name,'sha256':digest})
    return digest


def identity(pid):
    path=Path('/proc')/str(pid);parts=(path/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':int(pid),'uid':path.stat().st_uid,'command':(path/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),
        'start_ticks':parts[19],'state':parts[0]}


def matches(actual,expected):return all(str(actual[k])==str(expected[k])for k in('pid','uid','command','start_ticks'))


def locks(actual,lease):
    result=[]
    for record in lease['lock_records']:
        fd=Path('/proc',str(actual['pid']),'fd',str(record['fd']))
        info=Path('/proc',str(actual['pid']),'fdinfo',str(record['fd'])).read_text()
        assert os.readlink(fd)==record['path']and fd.stat().st_ino==record['inode']and'lock:'in info
        result.append({**record,'actual_fdinfo':info})
    assert len(result)==9
    return result


def resources(lease,allowed):
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],universal_newlines=True)
    allcards={}
    for line in raw.splitlines():
        if line.strip():
            index,uuid,free=[x.strip()for x in line.split(',')];allcards[int(index)]={'uuid':uuid,'free_mib':int(free)}
    cards={str(r['index']):allcards[r['index']]for r in lease['gpu']}
    assert set(cards)=={'4','5','6','7'}
    assert all(cards[str(r['index'])]['uuid']==r['uuid']for r in lease['gpu'])
    target={r['uuid']for r in lease['gpu']}
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],universal_newlines=True)
    compute=[]
    for line in raw.splitlines():
        if line.strip():
            uuid,pid,memory=[x.strip()for x in line.split(',')]
            if uuid in target:
                actual=identity(int(pid));assert int(pid)in allowed and matches(actual,allowed[int(pid)])
                compute.append({'uuid':uuid,'pid':int(pid),'used_mib':memory,'identity':actual})
    return {'time':time.time(),'gpu':cards,'compute':compute,'foreign_target_compute_count':0}


def zero_state(state,run_ids):
    assert state['phase']=='ready'and state['active']is None and state['next_run_index']==0
    assert list(state['runs'])==run_ids
    assert all(r['status']=='not_started'and r['last_decision_index']==0 and r['calls']=={'actor':0,'judge':0,'observe':0}for r in state['runs'].values())


try:
    for name,encoded in AUDITOR_SOURCES.items():
        path=ROOT/'auditor-source'/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb')as f:f.write(base64.b64decode(encoded))
    specpath=PREP/'launch-specification.reviewed.json';assert sha(specpath)==SPEC_SHA
    spec=read(specpath);copy(specpath,'specification.reviewed.json')
    leasepath=BASE/'resource-attempt-20261106-01/lease.json';lease=read(leasepath)
    holder=identity(lease['holder']['pid']);assert matches(holder,lease['holder'])and holder['uid']==1033
    save('holder-identity-locks.json',{'identity':holder,'locks':locks(holder,lease)})
    copy(leasepath,'lease.json')
    if not GROUP.exists():
        save('receipt.json',{'status':'not_started','group':str(GROUP),'health_GET_POST_model_GUI_calls':0})
    else:
        config=read(GROUP/'runtime-config.json');assert all(config[k]==v for k,v in spec.items())
        assert config['group_root']==str(GROUP)
        copy(GROUP/'runtime-config.json','runtime-config.json');copy(GROUP/'launch-specification.json','launch-specification.json')
        assert read(GROUP/'launch-specification.json')==spec
        for namespace,path,records in [('online',SOURCE,spec['online_source_sha256']),('native',Path(spec['preflight_source_root']),spec['preflight_source_sha256'])]:
            for name,expected in records.items():assert copy(path/name,'sources/'+namespace+'/'+name)==expected
        sys.path.insert(0,str(SOURCE))
        from online_gate import validate_static,validate_capacity
        from online_contract import validate_plan,canonical,digest
        validate_static(spec,SOURCE)
        assert spec['layer_counts']==[14,22,22,6]and spec['primary_allocator']=='expandable_segments:True'
        plan=read(spec['online_plan']);run_ids=list(validate_plan(plan))
        for key in('online_launch_gate','online_plan','layout','primary_native_layout_receipt','primary_dependency_receipt'):
            path=Path(spec[key]);assert copy(path,'bound/'+path.name)==spec[key+'_sha256']
        capacity_path=BASE/'single-capacity-independent-audits/1793985058235255298/receipt.json'
        assert copy(capacity_path,'capacity-audit-receipt.json')=='fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
        validate_capacity(read(capacity_path))
        workers={};allowed={};complete=True
        for role in('primary','pplx_flash'):
            registration=GROUP/'processes'/(role+'.json')
            if not registration.exists():workers[role]={'stage':'not_registered'};complete=False;continue
            recorded=read(registration);actual=identity(recorded['identity']['pid'])
            assert matches(actual,recorded['identity'])and actual['uid']==1033 and actual['state']not in{'Z','X'}
            assert actual['command']==' '.join(config['commands'][role]);allowed[actual['pid']]=actual
            actual_locks=locks(actual,lease)
            copy(registration,'workers/'+role+'/registration.json')
            launch=read(GROUP/(role+'-launch.json'));assert matches(actual,launch['identity'])
            copy(GROUP/(role+'-launch.json'),'workers/'+role+'/launch.json')
            env={}
            for field in(Path('/proc',str(actual['pid']),'environ').read_bytes().split(b'\0')):
                if b'='in field:
                    name,value=field.split(b'=',1)
                    if name in{b'CUDA_VISIBLE_DEVICES',b'PYTORCH_CUDA_ALLOC_CONF'}:env[name.decode()]=value.decode()
            expected_visible='4,5,6,7'if role=='primary'else'7'
            assert env.get('CUDA_VISIBLE_DEVICES')==expected_visible
            assert env.get('PYTORCH_CUDA_ALLOC_CONF')==('expandable_segments:True'if role=='primary'else None)
            assert launch.get('PYTORCH_CUDA_ALLOC_CONF')==env.get('PYTORCH_CUDA_ALLOC_CONF')
            assert not list((GROUP/role/'requests').glob('*'))
            loaded_path=GROUP/role/'loaded.json';ready_path=GROUP/role/'ready.json'
            row={'identity':actual,'locks':actual_locks,'actual_environment_whitelist':env,'requests':0,
                'loaded':loaded_path.exists(),'ready':ready_path.exists()}
            if row['loaded']:
                loaded=read(loaded_path);previous=read(CAPACITY/role/'loaded.json')
                keys=['devices','tensor_count','tensor_bytes_by_device','dtype_elements']
                if role=='primary':keys+=['actual_state_tensor_count','actual_state_total_bytes','actual_native_state_layout_sha256',
                    'primary_native_class_source_sha256','device_map','placement','dtype','backend']
                assert all(loaded[k]==previous[k]for k in keys)
                assert loaded['online_plan_sha256']==spec['online_plan_sha256']
                row.update(loaded_sha256=copy(loaded_path,'workers/'+role+'/loaded.json'),
                    tensor_count=loaded['tensor_count'],tensor_bytes_by_device=loaded['tensor_bytes_by_device'],dtype_elements=loaded['dtype_elements'])
                if role=='primary':
                    assert loaded['placement']=='explicit_asymmetric_14_22_22_6'
                    assert loaded['generate_and_judge_inherited_unchanged']is True and loaded['native_MTP_not_instantiated']is True
                    runtime=read(GROUP/role/'runtime.json');expected=read(spec['primary_expected_runtime'])
                    assert runtime['history_truncation']is False and runtime['image_preprocessing_changes']is False
                    assert runtime['dtype']=='torch.bfloat16'and runtime['backend']=='sdpa'
                    assert runtime['metadata_sha256']==expected['metadata_sha256']
                    assert runtime['torch']==expected['torch']and runtime['transformers']==expected['transformers']
                    assert all(sha(Path(spec['primary_model'])/name)==value for name,value in runtime['metadata_sha256'].items())
                    assert copy(Path(spec['primary_release'])/'defense/qwen_backend.py','bound/primary-qwen_backend.py')==spec['primary_backend_sha256']
                    copy(GROUP/role/'runtime.json','workers/'+role+'/runtime.json')
                else:
                    assert loaded['revision']=='9ff7cf9838e59df461c276b7699d56b244d2af58'
                    assert loaded['fast']is False and loaded['native_decider']is True and loaded['questions_per_request']==3
                    assert loaded['image_only_neutral_joint_observer']is True and loaded['noncausal_full_attention']is True
                    assert loaded['checkpoint_identity']['stable_identity_sha256']==spec['flash_stable_identity_receipt_sha256']
                    for name,value in loaded['checkpoint_identity']['source_sha256'].items():assert copy(Path(spec['flash_model'])/name,'sources/flash/'+name)==value
            if row['ready']:
                ready=read(ready_path);assert ready['stage']=='online_ready'and ready['loaded_sha256']==sha(loaded_path)
                assert ready['online_plan_sha256']==spec['online_plan_sha256']
                copy(ready_path,'workers/'+role+'/ready.json')
            complete=complete and row['loaded']and row['ready'];workers[role]=row
        before=resources(lease,allowed);save('resources-before.json',before)
        state=read(GROUP/'online-state.json');zero_state(state,run_ids)
        assert not list((GROUP/'transitions').iterdir())
        save('workers-identity-locks-load.json',workers)
        if complete:
            assert len(allowed)==2
            assert read(GROUP/'primary/loaded.json')['tensor_count']==1187 and read(GROUP/'pplx_flash/loaded.json')['tensor_count']==728
            previous=None;events=[]
            for i,line in enumerate((GROUP/'journal.jsonl').read_bytes().splitlines()):
                row=json.loads(line);content={k:v for k,v in row.items()if k!='sha256'}
                assert row['index']==i and row['previous_sha256']==previous and row['sha256']==digest(canonical(content))
                previous=row['sha256'];events.append(row)
            assert len(events)==2 and {r['payload']['role']for r in events}=={'primary','pplx_flash'}and all(r['event']=='worker_loaded'for r in events)
            copy(GROUP/'journal.jsonl','journal.jsonl')
            dependency=read(spec['primary_dependency_receipt']);deps=Path(dependency['dependency_root'])
            actual={str(p.relative_to(deps)):sha(p)for p in deps.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
            assert actual==dependency['dependency_files'];save('dependency-byte-checks.json',actual)
            for key in('flash_identity_receipt','flash_stable_identity_receipt'):
                assert copy(Path(spec[key]),'bound/'+Path(spec[key]).name)==spec[key+'_sha256']
        if ALLOW_HEALTH:
            assert complete,'No GET until both exact workers loaded/ready and zero model requests'
            claim=BASE/'online-three-readiness-control'/('health-once-'+GROUP.name+'.json');claim.parent.mkdir(exist_ok=True)
            with claim.open('x')as f:json.dump({'audit_root':str(ROOT),'time':time.time(),'maximum_GETs':2,'POST_model_GUI_calls':0},f)
            copy(claim,'health-once-claim.json')
            token=Path(spec['token_file']).read_text().strip()
            for role in('primary','pplx_flash'):
                connection=http.client.HTTPConnection('127.0.0.1',spec['roles'][role]['port'],timeout=30)
                try:
                    http_counts[role]+=1;connection.request('GET','/health',headers={'Authorization':'Bearer '+token})
                    response=connection.getresponse();raw=response.read();assert response.status==200
                finally:connection.close()
                value=json.loads(raw);assert value['phase']=='ready_gui'and value['stage']=='online_ready'
                zero_state(value['state'],run_ids)
                assert set(value['actual_allowed_pids'])==set(allowed)
                with(ROOT/(role+'-health.json')).open('xb')as f:f.write(raw)
            del token
        assert not(GROUP/'launcher-failure.json').exists()
        assert all(not list((GROUP/role/'requests').glob('*'))for role in('primary','pplx_flash'))
        zero_state(read(GROUP/'online-state.json'),run_ids);copy(GROUP/'online-state.json','online-state.json')
        after=resources(lease,allowed);save('resources-after.json',after)
        assert matches(identity(holder['pid']),holder);locks(holder,lease)
        for row in workers.values():
            if 'identity'in row:assert matches(identity(row['identity']['pid']),row['identity']);locks(row['identity'],lease)
        receipt={'status':'passed'if complete and ALLOW_HEALTH else'loaded_nohealth'if complete else'loading',
            'group':str(GROUP),'specification_sha256':SPEC_SHA,'runtime_config_sha256':sha(GROUP/'runtime-config.json'),
            'actual_uid_full_command_verified':True,'all_inherited_locks_held':True,'no_foreign_compute_on_leased_GPUs':True,
            'both_native_CUDA_load_audits_bound':complete,'native_tensor_values_not_independently_attached':True,
            'actual_decoder_layer_counts':[14,22,22,6],'primary_process_allocator_actual':'expandable_segments:True',
            'decoder_layer_counts':[14,22,22,6],'allocator':'expandable_segments:True',
            'decoder_layers14_22_22_6':True,'allocator_expandable_segments':True,
            'new_capacity_not_old15720':True,'all_three_same_resource':True,
            'actual_allowed_pids':sorted(allowed),'physical_gpu_uuids':{str(r['index']):r['uuid']for r in lease['gpu']},
            'collected_time':time.time(),'actual_source_bindings':bindings,
            'all_three_unstarted':True,'three_run_ids':run_ids,'primary_requests':0,'helper_requests':0,'transitions':0,
            'authenticated_GET_counts':http_counts,'both_authenticated_health_ready':ALLOW_HEALTH and complete,
            'POST_model_GUI_scorer_calls':0,'private_tokens_exported':False,'original_files_changed':False,
            'workers':{role:{k:v for k,v in row.items()if k!='locks'}for role,row in workers.items()},
            'capacity_only_known_input_future_fit_not_guaranteed':True,'Mirage_or_GUI_success_claim':False}
        save('receipt.json',receipt)
    save('copied-file-bindings.json',bindings)
    save('seal.json',{str(p.relative_to(ROOT)):sha(p)for p in ROOT.rglob('*')if p.is_file()})
    print(json.dumps({'receipt':str(ROOT/'receipt.json'),'receipt_sha256':sha(ROOT/'receipt.json'),
        'seal_sha256':sha(ROOT/'seal.json'),**read(ROOT/'receipt.json')}))
except BaseException:
    save('audit-failure.json',{'error':traceback.format_exc(),'authenticated_GET_counts':http_counts,
        'POST_model_GUI_scorer_calls':0,'original_live_files_changed':False,'no_automatic_retry':True})
    save('copied-file-bindings.json',bindings)
    save('seal.json',{str(p.relative_to(ROOT)):sha(p)for p in ROOT.rglob('*')if p.is_file()})
    print(json.dumps({'status':'audit_failure_preserved','audit_root':str(ROOT),'error':read(ROOT/'audit-failure.json')}))
    raise
