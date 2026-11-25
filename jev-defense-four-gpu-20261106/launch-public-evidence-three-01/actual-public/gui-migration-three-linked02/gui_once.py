"""New exact-three outer wrapper; no old queue/claim/terminal is reusable."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,traceback
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from native_environment import NATIVE_ENV

PLAN_SHA='838c63ac36560040df0c9257f4080d7c5ef33e7a0858f9b42bbdb73f486a2cef'
CAPACITY_SHA='fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
OLD_POLICY_SHA='3257dae74775d13adff6d8856785159608cf6570130b078339887664e3193c61'
TOKEN='/data/researcher/jev-defense-four-gpu-20261106/transport-online-three-01/private.token'
PYTHON='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
RUNTIME='/data/researcher/jev-defense-validation-20261103/runtime-stage-01'
TASK='/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
TEMPLATE='/data/researcher/jev-defense-validation-20261103/native-vwa-request.recovered.json'
PRIMARY_URL='http://127.0.0.1:28427'
OWN_FIELDS=('actual_uid_full_command_verified','all_inherited_locks_held',
    'no_foreign_compute_on_leased_GPUs','transport_ready','outer_launcher_rechecks_fresh')
THREE_RUN_IDS=['image-observer-v1--classifieds_112--clean--joint--observer',
    'image-observer-v1--classifieds_112--stale_replace--joint--no-observer',
    'image-observer-v1--classifieds_112--stale_replace--joint--observer']

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,obj):
    with Path(path).open('x',encoding='utf8')as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def bound(path,digest):
    p=Path(path);require(not p.is_symlink()and sha(p)==digest,'Bound source changed: '+str(p));return read(p)
def module(package):
    sys.path.insert(0,str(Path(package)/'release'))
    import migration_contract
    return migration_contract
def validate_package(package,seal_sha):
    package=Path(package).resolve();mapping=bound(package/'package-seal.json',seal_sha)
    require(isinstance(mapping,dict)and bool(mapping),'Package seal empty')
    for name,value in mapping.items():
        p=(package/name).resolve();require(p.is_relative_to(package)and not p.is_symlink()and sha(p)==value,'New source package differs: '+name)
    require(sha(package/'plan.json')==PLAN_SHA,'Wrong exact-three plan')
    original=bound(package/'frozen-original-policy-source-seal.json',OLD_POLICY_SHA)
    changed={'observer_launch_contract.py','run_image_observer_vwa_validation.py'}
    for name,value in original['release_sha256'].items():
        if name not in changed:require(sha(package/'release'/name)==value,'Old algorithm/prompt changed: '+name)
    module(package).validate_three_plan(read(package/'plan.json'))
    return read(package/'policy-source-seal.json')
def ownership(value,now=None):
    require(all(value.get(k)is True for k in OWN_FIELDS),'Ownership proof incomplete')
    require(value.get('three_unstarted_run_ids')==THREE_RUN_IDS,'Fresh ownership must bind exact three unstarted run IDs')
    cards=value.get('physical_gpu_uuids',{})
    require(set(map(str,cards))=={'4','5','6','7'}and len(set(cards.values()))==4,'Ownership UUID set differs')
    peers=value.get('actual_allowed_pids')
    require(isinstance(peers,list)and len(peers)==2 and len(set(peers))==2 and all(type(p)is int and p>0 for p in peers),'Two actual owned peers required')
    require(type(value.get('collected_time'))in(int,float),'Fresh collection time missing')
    if now is not None:require(0<=now-value['collected_time']<=120,'Ownership not fresh within120seconds')
    require(bool(value.get('source_evidence')),'Actual ownership sources missing')
    for item in value['source_evidence']:bound(item['path'],item['sha256'])
def validate_health(primary,observer,owner,plan):
    expected=[r['run_id']for r in plan['queue']]
    require(expected==THREE_RUN_IDS,'New health must bind exact three-run plan')
    for value,role in ((primary,'primary'),(observer,'pplx_flash')):
        require(value.get('role')==role and value.get('stage')=='online_ready'and value.get('phase')=='ready_gui'and
            value.get('exclusive_task_group')is True,'Both actual owned models must be ready')
        require(sorted(value.get('actual_allowed_pids',[]))==sorted(owner['actual_allowed_pids'])and
            {str(k):v for k,v in value.get('physical_gpu_uuids',{}).items()}==
            {str(k):v for k,v in owner['physical_gpu_uuids'].items()},'Fresh actual model peers/UUIDs differ from ownership')
        state=value.get('state',{})
        require(state.get('phase')=='ready'and state.get('active')is None and type(state.get('next_run_index'))is int and
            state['next_run_index']==0 and list(state.get('runs',{}))==expected,'An active/terminal or wrong-order group cannot be reused')
        for row in state['runs'].values():
            require(row.get('status')=='not_started'and type(row.get('last_decision_index'))is int and row['last_decision_index']==0 and
                json.dumps(row.get('calls'),sort_keys=True)==json.dumps({'actor':0,'judge':0,'observe':0},sort_keys=True),
                'Actual new group already spent a run budget')
def fetch_health(url):
    token=Path(TOKEN).read_text().strip()
    request=urllib.request.Request(url+'/health',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=15)as response:
        require(response.status==200,'Actual model health HTTP failed');value=json.loads(response.read())
    fields=('role','stage','phase','state','exclusive_task_group','actual_allowed_pids','physical_gpu_uuids')
    return {key:value[key]for key in fields if key in value}
def args_for(package,linked,batch):
    return SimpleNamespace(root=Path(batch),plan=Path(package)/'plan.json',token_file=Path(TOKEN),
        runtime=Path(RUNTIME),native_task=Path(TASK),actor_template=Path(TEMPLATE),
        auxiliary_config=Path(linked)/'auxiliary-config.json',readiness=Path(linked)/'readiness.json',model_url=PRIMARY_URL)
def native_validate(package,args):
    sys.path.insert(0,str(Path(package)/'release'))
    from observer_launch_contract import validate_launch_inputs
    validate_launch_inputs(args)
def prepare(a):
    package=a.package.resolve();output=a.output.resolve();batch=a.batch_root.resolve()
    require(not output.exists()and not batch.exists(),'New independent roots required')
    policy=validate_package(package,a.package_seal_sha256)
    bindings=bound(a.evidence_bindings,a.evidence_bindings_sha256)
    require(set(bindings)>={'three_trajectory_migration','resource_conditions','primary_full_input_capacity','ownership_transport','terminal_auditor'},'New pending proofs missing')
    require(bindings['primary_full_input_capacity']['sha256']==CAPACITY_SHA,'Only new21470/12image actual capacity audit is admitted')
    cap=bound(bindings['primary_full_input_capacity']['path'],CAPACITY_SHA)
    for key in ('capacity_passed','native_IDs_pixels_grid_exact_original_failed_CPU_proof','original_config_and_schema_exact',
        'original_native_generation_budget4096_preserved','BF16_SDPA_and_original_model_methods','natural_native_EOS','new_device_map_14_22_22_6_actual'):
        require(cap.get(key)is True,'Actual new full-input capacity proof incomplete: '+key)
    require(cap.get('input_tokens')==21470 and cap.get('original_images')==12 and cap.get('primary_calls')==1 and
        cap.get('helper_calls')==0 and cap.get('pending_requests')==0 and cap.get('primary_process_allocator_actual')=='expandable_segments:True',
        'Wrong finite full-input capacity or actual allocator')
    proof=bound(bindings['three_trajectory_migration']['path'],bindings['three_trajectory_migration']['sha256'])
    module(package).validate_migration_source(proof)
    runs=[r['run_id']for r in read(package/'plan.json')['queue']]
    owner=bound(bindings['ownership_transport']['path'],bindings['ownership_transport']['sha256']);ownership(owner,time.time())
    resource=bound(bindings['resource_conditions']['path'],bindings['resource_conditions']['sha256'])
    require(resource.get('decoder_layer_counts')==[14,22,22,6]and resource.get('allocator')=='expandable_segments:True','Actual new decoder placement/allocator not bound')
    require(resource.get('all_three_same_resource')is True,'All three must share new resource conditions')
    ready=read(package/'readiness.template.json');ready.update(launch_ready=True,plan_sha256=PLAN_SHA,
        release_sha256=policy['release_sha256'],evidence=bindings,deployment_applied=True)
    ready['unverified_required_evidence']={}
    config={'policy':ready['policy'],'model':'pplx_flash','revision':'9ff7cf9838e59df461c276b7699d56b244d2af58',
        'max_auxiliary_calls':60,'observer_contract_sha256':'98a3adb4ecb4939bb500603121e21587d454a99233ee14a32ddca8f68fa35054',
        'url':'http://127.0.0.1:28423','token_file':TOKEN,'deployment_applied':True,'token_created_by_this_package':False}
    require(Path(TOKEN).is_file(),'Root-provided new server token missing')
    output.mkdir(parents=True,exist_ok=False);save(output/'readiness.json',ready);save(output/'auxiliary-config.json',config)
    native_validate(package,args_for(package,output,batch))
    spec={'classification':'new_exact_original_three_unstarted_trajectories','launch_ready':True,
        'package':str(package),'package_seal_sha256':a.package_seal_sha256,'plan_sha256':PLAN_SHA,'linked':str(output),
        'batch_root':str(batch),'readiness_sha256':sha(output/'readiness.json'),'auxiliary_config_sha256':sha(output/'auxiliary-config.json'),
        'ownership_evidence':bindings['ownership_transport'],'migration_evidence':bindings['three_trajectory_migration'],
        'resource_evidence':bindings['resource_conditions'],'capacity_evidence':bindings['primary_full_input_capacity'],
        'native_env':NATIVE_ENV,'native_env_sha256':sha(Path(__file__).with_name('native_environment.py')),
        'token_file':TOKEN,'no_legacy_claim_or_root':True,'automatic_retry':False}
    save(output/'launch-spec.json',spec)
    save(output/'seal.json',{p.name:sha(p)for p in output.iterdir()if p.is_file()})
    return {'launch_spec':str(output/'launch-spec.json'),'launch_spec_sha256':sha(output/'launch-spec.json'),'GUI_model_calls':0}
def identity(pid):
    p=Path('/proc',str(pid));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'uid':p.stat().st_uid,'start_ticks':fields[19],'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()}
class ObserverFailureMonitor:
    """Preserve the original safe-boundary behavior on actual observer errors."""
    def __init__(self):self.states={}
    def scan(self,batch):
        for path in sorted(Path(batch).glob('runs/*/attempt-*/events.jsonl')):
            offset,pending,seq,previous=self.states.get(path,(0,b'',0,'0'*64))
            require(path.stat().st_size>=offset,'Running journal truncated')
            with path.open('rb')as f:f.seek(offset);fresh=f.read()
            offset+=len(fresh);lines=(pending+fresh).split(b'\n');pending=lines.pop()
            for line in lines:
                event=json.loads(line);expected=event.pop('sha256')
                raw=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                require(event.get('seq')==seq and event.get('previous')==previous and hashlib.sha256(raw).hexdigest()==expected,'Running event chain changed')
                seq+=1;previous=expected
                if event.get('kind')=='actor_observer_packet'and event['data'].get('status')in{'technical_failure','preserved_failure_no_retry'}:
                    return {'event_path':str(path),'seq':event['seq'],'event_sha256':expected,
                        'status':event['data']['status'],'request_safe_decision_boundary_stop':True,
                        'no_automatic_retry':True,'error_text_not_a_semantic_label':True}
            self.states[path]=(offset,pending,seq,previous)
        return None
def terminal_summary(batch,plan):
    status=read(batch/'status.json')if(batch/'status.json').exists()else{};rows=[];gap=False
    for item in plan['queue']:
        run=batch/'runs'/item['run_id'];attempts=list(run.glob('attempt-*'));require(len(attempts)<=1,'Repeated attempts')
        pointer=run/'complete.json'
        if pointer.exists():
            require(not gap and len(attempts)==1,'Trajectory order gap or missing attempt')
            target=read(pointer);attempt=attempts[0]
            require(Path(target['attempt']).resolve()==attempt.resolve()and target['sha256']==sha(attempt/'complete.json'),'Completion pointer differs')
            result=read(attempt/'complete.json')
            require(result['run']==item and result['semantic_mirage']is None,'Terminal condition or semantic substitution')
            require(result['actor_calls']<=70 and result['verifier_calls']<=140 and result['auxiliary_calls']<=(60 if item['observer_enabled']else 0),'Terminal caps exceeded')
            rows.append({'run_id':item['run_id'],'complete':True,'result':result})
        else:
            gap=True;rows.append({'run_id':item['run_id'],'complete':False,'status':'attempted_not_complete'if attempts else'not_attempted'})
    done=status.get('phase')=='completed'and status.get('completed')==3 and all(r['complete']for r in rows)
    failures=sum(r.get('result',{}).get('observer_technical_failures',0)for r in rows)
    return {'all_three_complete':done,'phase':status.get('phase'),'runs':rows,'observer_technical_failure_count':failures,
        'all_three_without_reported_observer_technical_failure':done and failures==0,
        'sealed04_missing_observer_packet_fallback_preserved':True,'defense_success_claim':False,
        'semantic_Mirage_review_pending':True,'service_wire_EOS_audit_pending':True,'no_automatic_retry':True}
def flat_manifest(root,path,expected):
    root=Path(root).resolve();path=Path(path).resolve();values=bound(path,expected)
    require(isinstance(values,dict)and bool(values),'Empty terminal map')
    for name,value in values.items():
        p=(root/name).resolve();require(p.is_relative_to(root)and not p.is_symlink()and sha(p)==value,'Terminal bytes differ: '+name)
    require({p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p.resolve()!=path}==set(values),'Terminal file inventory differs')
    return values
def audit_spec(a):
    spec=bound(a.launch_spec,a.launch_spec_sha256);package=Path(spec['package']);validate_package(package,spec['package_seal_sha256'])
    control=a.control_root.resolve();batch=Path(spec['batch_root']);service=a.service_root.resolve()
    cm=control/'postexit-sha256.json';bm=control/'batch-postexit-sha256.json';sm=service/'terminal-sha256.json'
    flat_manifest(control,cm,sha(cm));flat_manifest(batch,bm,sha(bm));flat_manifest(service,sm,a.service_manifest_sha256)
    requests=[]
    for role in ('primary','pplx_flash'):
        folder=service/role/'requests';require(folder.is_dir(),'Actual service request directory missing')
        for p in sorted(folder.iterdir()):
            if p.is_dir():requests.append({'path':str(p),'role':role,'seal_sha256':sha(p/'seal.json')})
    for p in sorted((service/'transitions').iterdir()):
        if p.is_dir():requests.append({'path':str(p),'role':'primary','seal_sha256':sha(p/'seal.json')})
    admission=service/'online-admission.json';policy=package/'policy-source-seal.json'
    obj={'batch_root':str(batch),'plan':{'path':str(package/'plan.json'),'sha256':PLAN_SHA},
        'policy_source_seal':{'path':str(policy),'sha256':sha(policy)},'release_root':str(package/'release'),
        'runtime_admission':{'path':str(admission),'sha256':sha(admission)},'three_trajectory_migration':spec['migration_evidence'],
        'terminal_manifests':[{'root':str(batch),'path':str(bm),'sha256':sha(bm),'exhaustive':True},
            {'root':str(service),'path':str(sm),'sha256':a.service_manifest_sha256,'exhaustive':True}],
        'service_requests':requests,'service_journals':[{'path':str(service/'journal.jsonl'),'sha256':sha(service/'journal.jsonl')}]}
    a.output.mkdir(parents=True,exist_ok=False);save(a.output/'audit-spec.json',obj)
    save(a.output/'seal.json',{'audit-spec.json':sha(a.output/'audit-spec.json')})
    return {'audit_spec':str(a.output/'audit-spec.json'),'audit_spec_sha256':sha(a.output/'audit-spec.json'),'actual_audit_still_required':True,'GUI_model_calls':0}
def run(a):
    spec=bound(a.launch_spec,a.launch_spec_sha256);require(spec.get('launch_ready')is True,'Gate closed')
    package=Path(spec['package']);linked=Path(spec['linked']);batch=Path(spec['batch_root'])
    validate_package(package,spec['package_seal_sha256'])
    bound(linked/'readiness.json',spec['readiness_sha256']);bound(linked/'auxiliary-config.json',spec['auxiliary_config_sha256'])
    require(spec['token_file']==TOKEN and spec['native_env']==NATIVE_ENV and
        spec['native_env_sha256']==sha(Path(__file__).with_name('native_environment.py')),'New transport/native environment changed')
    runs=[r['run_id']for r in read(package/'plan.json')['queue']]
    own=spec['ownership_evidence'];owner=bound(own['path'],own['sha256'])
    args=args_for(package,linked,batch);native_validate(package,args)
    require(not batch.exists()and not a.control_root.exists(),'New batch/control required')
    claim=a.launch_spec.with_name('launch-claimed.json');save(claim,{'launch_spec_sha256':a.launch_spec_sha256,'time':time.time(),'automatic_retry':False})
    control=a.control_root.resolve();control.mkdir(parents=True,exist_ok=False)
    save(control/'wrapper-process.json',identity(os.getpid()))
    argv=[PYTHON,'-u',str(package/'release/run_image_observer_vwa_validation.py')]
    for key in ('root','plan','token_file','runtime','native_task','actor_template','auxiliary_config','readiness','model_url'):
        argv+=['--'+key.replace('_','-'),str(getattr(args,key))]
    code=None;complete=False;child=None
    try:
        # Final freshness validation is immediately before creating the sole GUI child.
        primary=fetch_health(PRIMARY_URL);observer=fetch_health('http://127.0.0.1:28423')
        validate_health(primary,observer,owner,read(package/'plan.json'))
        ownership(owner,time.time())
        save(control/'fresh-health.json',{'primary':primary,'observer':observer,'ownership_receipt_sha256':own['sha256'],
            'new_model_calls':0,'time':time.time()})
        env={**os.environ,**NATIVE_ENV,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'}
        with(control/'runner.log').open('xb')as log:
            child=subprocess.Popen(argv,cwd=str(package/'release'),env=env,stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            child_identity=identity(child.pid);save(control/'runner-process.json',child_identity)
            monitor=ObserverFailureMonitor();stop_sent=False
            while child.poll()is None:
                if not stop_sent:
                    try:failure=monitor.scan(batch)
                    except Exception:failure={'event_chain_monitor_error':traceback.format_exc(),'request_safe_decision_boundary_stop':True,'no_automatic_retry':True}
                    if failure is not None:
                        save(control/'safe-boundary-stop-request.json',failure)
                        if child.poll()is None:
                            require(identity(child.pid)==child_identity,'Owned child identity changed; refuse signal')
                            try:os.kill(child.pid,signal.SIGUSR1)
                            except ProcessLookupError:require(child.poll()is not None,'Child disappeared without exit')
                        stop_sent=True
                time.sleep(0.5)
            code=child.wait()
        summary=terminal_summary(batch,read(package/'plan.json'))
        complete=code==0 and summary['all_three_without_reported_observer_technical_failure']
    except BaseException:
        save(control/'wrapper-failure.json',{'error':traceback.format_exc(),'time':time.time()});raise
    finally:
        if child is not None and child.poll()is None:
            save(control/'unsealed-live-child.json',{'runner':identity(child.pid),'postexit_seal_written':False,
                'automatic_retry':False,'reason':'wrapper exception while actual child still live; root must inspect','time':time.time()})
        else:
            save(control/'finalization.json',{**(summary if 'summary'in locals()else{}),'runner_exit_code':code,
                'execution_completed':complete,'automatic_retry':False,'service_and_semantic_audits_pending':True,'time':time.time()})
            if batch.exists():save(control/'batch-postexit-sha256.json',{p.relative_to(batch).as_posix():sha(p)for p in batch.rglob('*')if p.is_file()})
            save(control/'postexit-sha256.json',{p.relative_to(control).as_posix():sha(p)for p in control.rglob('*')if p.is_file()})
    return {'runner_exit_code':code,'all_three_complete':complete,'execution_completed':complete,'automatic_retry':False}
def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    prep=s.add_parser('prepare')
    for key in ('package','evidence-bindings','batch-root','output'):prep.add_argument('--'+key,type=Path,required=True)
    for key in ('package-seal-sha256','evidence-bindings-sha256'):prep.add_argument('--'+key,required=True)
    execute=s.add_parser('run')
    for key in ('launch-spec','control-root'):execute.add_argument('--'+key,type=Path,required=True)
    execute.add_argument('--launch-spec-sha256',required=True)
    audit=s.add_parser('audit-spec')
    for key in ('launch-spec','control-root','service-root','output'):audit.add_argument('--'+key,type=Path,required=True)
    for key in ('launch-spec-sha256','service-manifest-sha256'):audit.add_argument('--'+key,required=True)
    a=p.parse_args();print(json.dumps({'prepare':prepare,'run':run,'audit-spec':audit_spec}[a.mode](a)))
if __name__=='__main__':main()
