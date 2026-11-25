"""Create separate once-only orchestration; importing templates launches nothing."""
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'full-gui-bounded-evidence-20261109-03'

STAGE = r'''
def stage():
    assert not (RUNTIME/'manifest.json').exists()
    inputs=json.loads((HERE/'stage-inputs.json').read_bytes())
    review=Path(inputs['semantic_review']);audit=Path(inputs['technical_audit'])
    cpu=Path(inputs['CPU_integration'])
    reviewed=json.loads(review.read_bytes());audited=json.loads(audit.read_bytes())
    assert audited['passed'] and audited['fresh_auxiliary_calls']==0 and audited['actual_main_model_calls']<=28
    assert reviewed['all_actual_replies_reviewed'] and reviewed['allow_new_GUI_development']
    assert reviewed['trajectory_reduction_established'] is False
    assert json.loads(cpu.read_bytes())['passed']
    for name,h in json.loads((HERE/'source-seal.json').read_bytes()).items():assert sha(RUNTIME/name)==h,name
    expected=json.loads((RUNTIME/'auxiliary-identity-reference.json').read_bytes())['expected_holder']
    token=secrets.token_urlsafe(48).encode()
    with (RUNTIME/'private.token').open('xb')as stream:stream.write(token)
    admission={'admit_new_GUI_development':True,'formal_release_or_semantic_pass':False,
       'known_semantic_failures_not_relabelled_as_passes':True,
       'full_history_capacity_beyond_actual_inputs_not_established':True,
       'technical_audit_sha256':sha(audit),'semantic_review_sha256':sha(review),'CPU_integration_sha256':sha(cpu),
       'exact_tradeoff':json.loads((RUNTIME/'plan.json').read_bytes())['source_condition_tradeoff'],
       'authorization':'Existing sustained user goal; new finite matched GUI development, original per-track budgets'}
    save(RUNTIME/'admission.json',admission)
    lease=BASE/'resource-attempt-20261106-01/lease.json'
    m={'schema':'complete-main-history-32-track-GUI-development-v1','authorized_finite_joint_development':True,
       'expected_holder':expected,'lease_sha256':sha(lease),'outputs':ROOT3090,'GUI_output':ROOT4090+'/batch',
       'model_url':'http://192.0.2.11:19138','auth_token_sha256':hashlib.sha256(token).hexdigest(),
       'native_bindings_sha256':sha(RUNTIME/'native-bindings-public.json'),
       'source_condition_tradeoffs':admission['exact_tradeoff'],'technical_audit_sha256':sha(audit),
       'semantic_review_sha256':sha(review),'CPU_integration_sha256':sha(cpu),
       'actual_auxiliary':'Qwen/Qwen3.5-9B','decision_adapter_loaded':False,
       'tracks':32,'per_trajectory_caps':{'steps':50,'actor':70,'judge':140,'auxiliary':60},
       'worker_source_sha256':sha(RUNTIME/'gpu_server.py'),
       'files':{p.relative_to(RUNTIME).as_posix():sha(p)for p in sorted(RUNTIME.rglob('*'))if p.is_file()and p.name!='private.token'}}
    save(RUNTIME/'manifest.json',m)
    encoded=payload(RUNTIME)
    for host,path,interpreter in [('3090',REMOTE_PACKAGE,'/opt/whz/conda-envs/webmall-vlm/bin/python'),
                                ('4090',ROOT4090,'/data/researcher/venvs/qwen35-9b-full-20261019/bin/python')]:
        code='TARGET='+repr(path)+'\nMANIFEST_SHA='+repr(sha(RUNTIME/'manifest.json'))+'\n'+r"""
from pathlib import Path
import base64,hashlib,io,json,os,zipfile
r=Path(TARGET);assert not r.exists();r.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for name in archive.namelist():assert(r/name).resolve().is_relative_to(r.resolve())
 archive.extractall(r)
(r/'private.token').chmod(0o600)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'manifest.json')==MANIFEST_SHA
m=json.loads((r/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(r/name)==h,name
assert sha(r/'private.token')==m['auth_token_sha256']
for p in r.rglob('*.py'):compile(p.read_text(),str(p),'exec')
print(json.dumps({'root':str(r),'uid':os.getuid(),'manifest_sha256':MANIFEST_SHA,'files_verified':len(m['files']),'new_model_GUI_scorer_calls':0}))
"""
        out,op=remote(host,code,'stage-new-package-'+host,timeout=55,interpreter=interpreter,private_prefix='PAYLOAD='+repr(encoded)+'\n')
        save(HERE/('stage-'+host+'.json'),{'result':json.loads(out),'operation':str(op)})
    save(HERE/'freeze.json',{'manifest_sha256':sha(RUNTIME/'manifest.json'),'plan_sha256':sha(RUNTIME/'plan.json'),
       'new_GUI_tracks':32,'tasks':8,'paired_comparisons':16,'old_queues_or_completed_controls_resumed':False,
       'per_track_steps_actor_judge_auxiliary':[50,70,140,60],'formal_efficacy_established':False})
    print(json.dumps({'staged_both_hosts':True,'manifest_sha256':sha(RUNTIME/'manifest.json'),'new_model_GUI_calls':0}))

'''


def main():
    for filename in ['remote_control.py', 'orchestrate.py']:
        assert not (HERE / filename).exists()
    remote = (OLD / 'remote_control.py').read_text(encoding='utf8')
    remote = remote.replace(OLD.name, HERE.name)
    (HERE / 'remote_control.py').write_text(remote, encoding='utf8', newline='\n')
    text = (OLD / 'stage_and_launch.py').read_text(encoding='utf8').replace(OLD.name, HERE.name)
    start, end = text.index('def stage():'), text.index('def preflight():')
    text = text[:start] + STAGE + '\n' + text[end:]
    text = text.replace("    assert not (HERE/'service-submission.json').exists()",
        "    assert not (HERE/'service-submission.json').exists() and not (HERE/'service-submission-intent.json').exists()\n"
        "    assert json.loads((RUNTIME/'admission.json').read_bytes())['admit_new_GUI_development']\n"
        "    assert json.loads((HERE/'environment-admission.json').read_bytes())['passed']")
    text = text.replace("    out,target=remote('3090',code,'submit-service-once',timeout=55)",
        "    save(HERE/'service-submission-intent.json',{'manifest_sha256':msha,'time':time.time(),'no_duplicate_after_observation_timeout':True})\n"
        "    out,target=remote('3090',code,'submit-service-once',timeout=55)")
    text = text.replace("    assert not (HERE/'GUI-submission.json').exists()",
        "    assert not (HERE/'GUI-submission.json').exists() and not (HERE/'GUI-submission-intent.json').exists()")
    text = text.replace("    out,target=remote('4090',code,'submit-full-GUI-once',timeout=55,",
        "    save(HERE/'GUI-submission-intent.json',{'manifest_sha256':msha,'time':time.time(),'no_duplicate_after_observation_timeout':True})\n"
        "    out,target=remote('4090',code,'submit-full-GUI-once',timeout=55,")
    # The completed 19 initialization is not rerun: this is one fresh first-task
    # same-live setup, with site ownership and native scorer import checked.
    text = text.replace("    print(out)\n\ndef service():",
        "    value=json.loads(out);assert value['status']=='passed'\n"
        "    save(HERE/'environment-admission.json',{'passed':True,'result':value,'operation':str(target),'new_model_GUI_scorer_calls':0})\n"
        "    print(out)\n\ndef service():")
    for name in ['service-submission-intent.json', 'GUI-submission-intent.json', 'environment-admission.json']:
        assert name in text, name
    ast.parse(text)
    (HERE / 'orchestrate.py').write_text(text, encoding='utf8', newline='\n')
    print('Prepared separate orchestration source; no staging, launches or model calls performed.')


if __name__ == '__main__':
    main()
