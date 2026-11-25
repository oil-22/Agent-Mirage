"""New same-live native environment validation; no model, GUI-agent or scorer calls."""
import hashlib,io,json,os,subprocess,sys,time,traceback
from pathlib import Path
from native_environment import NATIVE_ENV

HERE=Path(__file__).resolve().parent
BASE=Path('/data/researcher/jev-defense-validation-20261103')
RUNTIME=BASE/'runtime-stage-01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert os.getuid()==1015
    target=HERE/'environment-preflight';target.mkdir(exist_ok=False)
    os.environ.update(NATIVE_ENV)
    result={'time_unix':time.time(),'model_calls':0,'task_agent_actions':0,'scorer_calls':0,'site_reset':False}
    try:
        contract=json.loads((BASE/'historical-gui-contract.json').read_bytes())['fields']['runtime_source_bindings']
        for old,expected in contract.items():
            if '/upstream/visualwebarena-main/' in old:actual=RUNTIME/'upstream'/old.split('/upstream/visualwebarena-main/')[1]
            elif old.endswith('run_reddit_internvl_smoke.py'):actual=RUNTIME/'native/run_reddit_internvl_smoke.py'
            else:actual=BASE/'task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
            assert sha(actual)==expected,old
        result['native_source_binding_matches']=True
        ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
        rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
        assert all(v['Id']==i and v['Config']['Labels']['owner']=='whz-qwen27-vwa' and v['State']['Running'] for v,i in zip(rows,ids))
        assert any(m.get('Name')=='qwen27_vwa_db_data' for m in rows[1]['Mounts'])
        assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
        result['site_identities']=ids
        sys.path[:0]=[str(RUNTIME/'native'),str(RUNTIME/'upstream')]
        from browser_env import ScriptBrowserEnv
        from browser_env.auto_login import renew_comb
        from evaluation_harness.evaluators import evaluator_router
        from run_reddit_internvl_smoke import png
        from PIL import Image
        auth=target/'.auth';auth.mkdir();renew_comb(['classifieds'],str(auth))
        original=BASE/'task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
        cfg=json.loads(original.read_text().replace('192.0.2.10:19980','192.0.2.10:29980'))
        assert cfg['require_reset'] is False and cfg['eval']['eval_types']==['url_match']
        cfg['storage_state']=str(auth/'classifieds_state.json')
        p=target/'official_config.PRIVATE.json';p.write_text(json.dumps(cfg));p.chmod(0o600)
        evaluator_router(p)
        env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
        try:
            obs,info=env.reset(seed=20261011,options={'config_file':str(p)})
            first=png(obs);second=png(env._get_obs())
            assert Image.open(io.BytesIO(first)).size==(1280,720)
            (target/'initial.png').write_bytes(first);(target/'same-live-recapture.png').write_bytes(second)
            result.update(status='passed',native_scorer_loaded_not_invoked=True,same_live_recapture=True,
                first_image_sha256=hashlib.sha256(first).hexdigest(),recapture_sha256=hashlib.sha256(second).hexdigest(),
                native_task_sha256=sha(original),native_actor_template_sha256=sha(BASE/'native-vwa-request.recovered.json'))
        finally:env.close()
    except BaseException:
        result.update(status='failed',traceback=traceback.format_exc())
    (target/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result));return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
