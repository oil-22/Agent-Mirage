
import ast,base64,hashlib,json,os,time
from pathlib import Path
BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
PACKAGE=BASE/'gui-migration-three-linked02'
LINKED=BASE/'gui-final-readiness-three-01';CONTROL=BASE/'gui-outer-control-three-01'
BACKGROUND=BASE/'gui-outer-background-three-01';BINDING=BASE/'gui-three-evidence-binding-01'
OWNER_ROOT=BASE/'ownership-transport-proof-1793987232101616600'
SPEC_SHA='506eda3ea06600c6a3ca8baecc6f88e1310e910b24efb1dcd769b58d2602e252'
OWNER_SHA='50c3437b8a88985da1fceae194404513218bbe7f13d50b9cea0a3f8f24995042'
PACKAGE_SHA='1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44'
WRAPPER_SHA='e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d'
CONTROL_SHA='db723d2f2b4b24c1dd2085d40fe3f56db8f61f9b411a4791ea1d95a72764956a'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
assert sha(LINKED/'launch-spec.json')==SPEC_SHA
assert sha(OWNER_ROOT/'ownership-transport-proof.json')==OWNER_SHA
assert sha(PACKAGE/'package-seal.json')==PACKAGE_SHA and sha(PACKAGE/'gui_once.py')==WRAPPER_SHA
spec=read(LINKED/'launch-spec.json');owner=read(OWNER_ROOT/'ownership-transport-proof.json')
assert spec['ownership_evidence']=={'path':str(OWNER_ROOT/'ownership-transport-proof.json'),'sha256':OWNER_SHA}
assert spec['package']==str(PACKAGE)and spec['package_seal_sha256']==PACKAGE_SHA
assert spec['launch_ready']is True and spec['batch_root']==str(BASE/'gui-batch-image-observer-three-01')
assert spec['token_file']==str(BASE/'transport-online-three-01/private.token')
assert sha(LINKED/'readiness.json')==spec['readiness_sha256']
assert sha(LINKED/'auxiliary-config.json')==spec['auxiliary_config_sha256']
assert read(LINKED/'auxiliary-config.json')['token_file']==spec['token_file']
assert read(LINKED/'launch-claimed.json')['launch_spec_sha256']==SPEC_SHA
source_map=read(PACKAGE/'package-seal.json')
assert all(sha(PACKAGE/name)==value for name,value in source_map.items())
control_sources=BASE/'gui-three-control-preparation-01'
assert sha(control_sources/'seal.json')==CONTROL_SHA
assert all(sha(control_sources/name)==value for name,value in read(control_sources/'seal.json').items())
for root in (LINKED,BINDING):
    assert all(sha(root/name)==value for name,value in read(root/'seal.json').items())
bindings=read(BINDING/'evidence-bindings.json')
assert bindings['ownership_transport']==spec['ownership_evidence']
assert bindings['resource_conditions']==spec['resource_evidence']
resource=Path(spec['resource_evidence']['path'])
assert resource.name=='resource-conditions.json'and resource.resolve().is_relative_to(BASE)
assert sha(resource)==spec['resource_evidence']['sha256']
# Read the actual existing health record only; never request health while pending.
fresh=read(CONTROL/'fresh-health.json');plan=read(PACKAGE/'plan.json');run_ids=[row['run_id']for row in plan['queue']]
assert run_ids==owner['three_unstarted_run_ids']and len(run_ids)==3
for key,role in [('primary','primary'),('observer','pplx_flash')]:
    value=fresh[key]
    assert value['role']==role and value['stage']=='online_ready'and value['phase']=='ready_gui'and value['exclusive_task_group']is True
    assert sorted(value['actual_allowed_pids'])==sorted(owner['actual_allowed_pids'])
    assert {str(k):v for k,v in value['physical_gpu_uuids'].items()}=={str(k):v for k,v in owner['physical_gpu_uuids'].items()}
    state=value['state'];assert state['phase']=='ready'and state['active']is None and state['next_run_index']==0 and list(state['runs'])==run_ids
    assert all(row=={'status':'not_started','last_decision_index':0,'calls':{'actor':0,'judge':0,'observe':0}}for row in state['runs'].values())
assert fresh['ownership_receipt_sha256']==OWNER_SHA and 0<=fresh['time']-owner['collected_time']<=120
tree=ast.parse((PACKAGE/'gui_once.py').read_text(encoding='utf8'))
run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
calls={name:[n for n in ast.walk(run)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id==name]
    for name in ('fetch_health','validate_health','ownership')}
popen=[n for n in ast.walk(run)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='Popen']
assert len(popen)==1 and len(calls['fetch_health'])==2 and len(calls['validate_health'])==len(calls['ownership'])==1
assert all(n.lineno<popen[0].lineno for nodes in calls.values()for n in nodes)
native_tree=ast.parse((PACKAGE/'native_environment.py').read_text(encoding='utf8'))
native=next(ast.literal_eval(n.value)for n in native_tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='NATIVE_ENV'for t in n.targets))
assert len(native)==14 and spec['native_env']==native and sha(PACKAGE/'native_environment.py')==spec['native_env_sha256']
def actual(expected):
    root=Path('/proc',str(expected['pid']))
    if not root.exists():return {'expected':expected,'actual':None,'identity_matches':False,'phase':'pid_absent'}
    fields=(root/'stat').read_text().rsplit(')',1)[1].split()
    now={'pid':expected['pid'],'uid':root.stat().st_uid,'start_ticks':fields[19],
        'command':(root/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'state':fields[0]}
    match=all(str(now[key])==str(expected[key])for key in ('pid','uid','start_ticks','command'))
    result={'expected':expected,'actual':now,'identity_matches':match,'phase':'live'if match and now['state']not in('Z','X')else'zombie_or_mismatch'}
    if match and now['state']not in('Z','X'):
        # Whitelist static native fields only. Do not return any other environ.
        env=dict(item.split('=',1)for item in (root/'environ').read_bytes().decode().split('\0')if '='in item)
        selected={key:env.get(key)for key in native}
        result['whitelisted_native_environment']=selected;result['native_environment14_exact']=selected==native
    return result
wrapper_expected=read(CONTROL/'wrapper-process.json');runner_expected=read(CONTROL/'runner-process.json')
assert wrapper_expected['uid']==runner_expected['uid']==1015
assert wrapper_expected['pid']==3551891 and runner_expected['pid']==3551893
background=read(BACKGROUND/'actualprocess.json')
assert background['identity']==wrapper_expected and background['spec_sha256']==SPEC_SHA
processes={'wrapper':actual(wrapper_expected),'runner':actual(runner_expected)}
boot=int(next(line.split()[1]for line in Path('/proc/stat').read_text().splitlines()if line.startswith('btime ')))
ticks=os.sysconf('SC_CLK_TCK')
startup_time={'saved_fresh_health_time':fresh['time'],'saved_ownership_time':owner['collected_time'],
    'saved_health_after_ownership_seconds':fresh['time']-owner['collected_time'],
    'runner_start_epoch_from_btime_diagnostic':boot+int(runner_expected['start_ticks'])/ticks,
    'proc_btime_rounding_caveat_seconds':1,'sole_Popen_before_health_prohibited_by_exact_source_AST':True}
allowed=[]
for root,names in [(BINDING,('evidence-bindings.json','preparation-claim.json','result.json','seal.json')),
    (LINKED,('readiness.json','auxiliary-config.json','launch-spec.json','seal.json','launch-claimed.json')),
    (BACKGROUND,('once-only-launch.json','actualprocess.json')),
    (CONTROL,('wrapper-process.json','runner-process.json','fresh-health.json')),
    (PACKAGE,('package-seal.json','policy-source-seal.json','gui_once.py','native_environment.py')),
    (control_sources,('seal.json','receipt.json'))]:
    allowed.extend(root/name for name in names)
allowed.extend([OWNER_ROOT/'ownership-transport-proof.json',resource])
expected_owner_names={'3090-ownership-inspection.json','bridge-inspect.json','bridge-process-identity.json','4090-authenticated-health.json','wrapper-source-binding.json'}
assert {Path(item['path']).name for item in owner['source_evidence']}==expected_owner_names
for item in owner['source_evidence']:
    p=Path(item['path']);assert p.parent==OWNER_ROOT and sha(p)==item['sha256'];allowed.append(p)
public={}
for p in allowed:
    assert p.resolve().is_relative_to(BASE)and not p.is_symlink()
    raw=p.read_bytes();public[p.relative_to(BASE).as_posix()]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
receipt={'stage':'actual_three_GUI_startup_public_readonly_snapshot','time':time.time(),
    'launch_spec_sha256':SPEC_SHA,'fresh_owner_sha256':OWNER_SHA,'source_package_sha256':PACKAGE_SHA,
    'source_wrapper_sha256':WRAPPER_SHA,'all125_source_files_verified':len(source_map),
    'actual_saved_dual_authenticated_health_precedes_sole_GUI_Popen_source_bound':True,
    'saved_both_health_exact_three_zero_budget_states':True,'startup_time':startup_time,'actual_processes':processes,
    'source_call_lines':{name:[n.lineno for n in nodes]for name,nodes in calls.items()},'sole_GUI_Popen_line':popen[0].lineno,
    'public_files_copied':len(public),'native_environment_from_exact_source_and_spec':native,
    'current_3090_service_health_or_resource_rechecked':False,
    'candidate_events_screenshots_private_task_config_token_read_or_exported':False,
    'HTTP_POST_health_model_GUI_scorer_signal_calls':0,'progress_and_semantic_outcomes_not_inferred':True,
    'remote_files_written':0}
print(json.dumps({'receipt':receipt,'public':public}))
