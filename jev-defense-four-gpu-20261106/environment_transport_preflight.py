"""New zero-model live-environment preflight. One actual native initial-state scorer transport check, no model/task-agent action."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import urllib.request

BASE = Path('/data/researcher/jev-defense-validation-20261103')
RUNTIME = BASE / 'runtime-stage-01'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(root):
    assert os.getuid() == 1015
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)
    result = {'time': time.time(), 'model_calls': 0, 'actor_calls': 0, 'task_actions': 0,
              'scorer_calls': 0, 'site_reset': False, 'runtime': str(RUNTIME)}
    try:
        os.environ.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
            DATASET='visualwebarena', CLASSIFIEDS='http://192.0.2.10:29980',
            REDDIT='http://192.0.2.10:29999', SHOPPING='http://127.0.0.1:1',
            WIKIPEDIA='http://127.0.0.1:1', HOMEPAGE='http://127.0.0.1:1',
            CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset', REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',
            OPENAI_API_KEY='unused-local-url-evaluator', OPENAI_BASE_URL='http://127.0.0.1:1/v1',
            PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers')
        sys.path[:0] = [str(RUNTIME / 'native'), str(RUNTIME / 'upstream')]
        contract = json.loads((BASE / 'historical-gui-contract.json').read_bytes())['fields']['runtime_source_bindings']
        for old, expected in contract.items():
            if '/upstream/visualwebarena-main/' in old:
                actual = RUNTIME / 'upstream' / old.split('/upstream/visualwebarena-main/')[1]
            elif old.endswith('run_reddit_internvl_smoke.py'):
                actual = RUNTIME / 'native/run_reddit_internvl_smoke.py'
            else:
                actual = BASE / 'task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
            assert sha(actual) == expected, old
        from run_reddit_internvl_smoke import SYSTEM, parse, action, png
        from browser_env import ScriptBrowserEnv
        from browser_env.actions import create_stop_action
        from browser_env.auto_login import renew_comb
        from evaluation_harness.evaluators import evaluator_router
        from playwright.sync_api import sync_playwright, Page
        result['imports_passed'] = True
        result['packages'] = {n: importlib.metadata.version(n) for n in
            ['playwright', 'gymnasium', 'numpy', 'Pillow', 'beartype', 'evaluate', 'transformers']}
        template = json.loads((BASE / 'native-vwa-request.recovered.json').read_bytes())
        assert template['messages'][0]['content'] == SYSTEM + '\nYou may switch browser tabs using {"type":"tab","index":0}; indices start at 0. No URLs or tab titles are supplied.'
        with sync_playwright() as p:
            executable = Path(p.chromium.executable_path)
            result['browser_executable'] = str(executable)
            assert executable.exists(), 'Required native browser executable is unavailable'
            result['browser_sha256'] = sha(executable)
        identities = ['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd',
                      'e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
        rows = json.loads(subprocess.check_output(['docker', 'inspect', *identities], text=True))
        assert all(c['Id'] == expected and c['Config']['Labels']['owner'] == 'whz-qwen27-vwa'
                   for c, expected in zip(rows, identities))
        assert any(m.get('Name') == 'qwen27_vwa_db_data' for m in rows[1]['Mounts'])
        assert rows[0]['HostConfig']['PortBindings'] == {'9980/tcp': [{'HostIp': '192.0.2.10', 'HostPort': '29980'}]}
        result['site_before'] = [{'id': c['Id'], 'running': c['State']['Running'], 'mounts': c['Mounts']} for c in rows]
        # This linked check is read-only against already-running exact owned sites.
        assert all(c['State']['Running'] for c in rows), 'Owned source sites are stopped; no automatic restart in this check'
        result['site_resumed'] = any(not c['State']['Running'] for c in rows)
        result['linked_predecessor'] = '/data/researcher/jev-defense-validation-20261103/environment-preflight-1793684288933578077'
        result['preflight_source_sha256'] = sha(Path(__file__))
        # Docker running does not establish that PHP is accepting HTTP connections.
        attempts = []
        for _ in range(30):
            try:
                with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login', timeout=2) as response:
                    attempts.append({'time': time.time(), 'http_status': response.status})
                    if response.status == 200:break
            except OSError as error:
                attempts.append({'time': time.time(), 'error': type(error).__name__ + ': ' + str(error)})
            time.sleep(1)
        else:raise RuntimeError('Owned site did not become HTTP ready within bounded startup check')
        result['site_http_readiness'] = attempts
        auth = root / '.auth';auth.mkdir()
        renew_comb(['classifieds'], str(auth))
        private = json.loads((BASE / 'task-restore-1793683370167273452/classifieds_112.PRIVATE.json').read_bytes())
        assert private['require_reset'] is False and private['eval']['eval_types'] == ['url_match']
        private = json.loads(json.dumps(private).replace('192.0.2.10:19980', '192.0.2.10:29980'))
        private['storage_state'] = str(auth / 'classifieds_state.json')
        config = root / 'official_config.PRIVATE.json';config.write_text(json.dumps(private, indent=2))
        # Original parser and native action constructors, CPU only. None is passed
        # to env.step or a browser input method; malformed inputs remain rejected.
        native_cases = [
            {'type':'click','x':100,'y':200}, {'type':'type','text':'CPU contract only'},
            {'type':'press','key':'Enter'}, {'type':'scroll','direction':'up'},
            {'type':'scroll','direction':'down'}, {'type':'back'}, {'type':'wait'},
            {'type':'stop','answer':'Preflight transport only'}]
        parser_checks=[]
        for payload in native_cases:
            parsed=parse('<action>'+json.dumps(payload)+'</action>')
            assert parsed==payload
            native=action(parsed)
            assert isinstance(native,dict)
            parser_checks.append({'type':payload['type'],'passed':True,'environment_execution':False})
        for payload in [{'type':'click','x':0,'y':200},{'type':'scroll','direction':'left'}, {'type':'unbound'}]:
            try: action(payload)
            except (ValueError,KeyError): pass
            else: raise AssertionError('Original native action rejected boundary was relaxed')
        try: parse('<action>{}</action><action>{}</action>')
        except ValueError: pass
        else: raise AssertionError('Original parser must reject two action blocks')
        result['native_parser_action_checks']={'positive_cases':parser_checks,'negative_boundaries_passed':4,
                                               'executed_as_GUI_actions':0}
        result['native_parser_passed']=True
        # Same historical navigation timeout, no change to task actions or observations.
        original_goto = Page.goto
        def goto(page, url, **kwargs):
            if kwargs.get('timeout') is None:kwargs['timeout'] = 120000
            return original_goto(page, url, **kwargs)
        Page.goto = goto
        env = ScriptBrowserEnv(headless=True, observation_type='image', current_viewport_only=True,
            viewport_size={'width': 1280, 'height': 720}, save_trace_enabled=True, sleep_after_execution=0.5)
        try:
            obs, info = env.reset(seed=20261011, options={'config_file': str(config)})
            first = png(obs);second = png(env._get_obs())
            (root / 'initial.png').write_bytes(first);(root / 'same-live-recapture.png').write_bytes(second)
            scorer = evaluator_router(config)
            # Real official URL scorer call on this exact native initial page.
            # STOP is a test trajectory entry only; no env.step/agent action occurs.
            transport_trajectory=[{'observation':obs,'info':info},create_stop_action('Preflight transport only')]
            result['scorer_calls']=1
            observed_reward=float(scorer(transport_trajectory,config,env.page))
            result['scorer_transport_test']={'purpose':'initial-page URL scorer transport only, not a formal task result',
                'trajectory_entries':2,'expected_initial_reward':0.0,'observed_reward':observed_reward,
                'stop_was_not_environment_action':True,'PRIVATE_answers_delivered_to_model':False}
            assert observed_reward==0.0,'Unexpected initial-page URL score; preserve and inspect without retry'
            result['same_live_recapture_passed']=True
            result['official_scorer_transport_passed']=True
            result['no_site_reset']=True
            result['source_browser_operations']=['native renew_comb authentication','native env.reset(require_reset=false) startup navigation','initial native screenshot','same-live env._get_obs recapture','one official URL-scorer read with STOP test trajectory']
            result['formal_task_actions']=0
            result.update(phase='environment_transport_preflight_complete', actual_url=env.page.url,
                same_live_recapture=True, initial_sha256=sha(root / 'initial.png'),
                recapture_sha256=sha(root / 'same-live-recapture.png'), scorer_class=type(scorer).__name__)
        finally:
            env.close();Page.goto = original_goto
    except Exception as error:
        result.update(phase='technical_failure', error_type=type(error).__name__,
                      error='See preserved remote traceback.PRIVATE.txt; no automatic retry')
        (root / 'traceback.PRIVATE.txt').write_text(traceback.format_exc())
    result['not_a_formal_defense_result']=True
    result['linked_parent_source_sha256']='ade1c09f0ef0c70bd8f1426a111e108e99682d94810ee0cb8d16a0523092d81b'
    public=root/'public';public.mkdir()
    for name in ['initial.png','same-live-recapture.png']:
        if(root/name).exists():(public/name).write_bytes((root/name).read_bytes())
    (public/'receipt.json').write_text(json.dumps(result, indent=2))
    (public/'seal.json').write_text(json.dumps({p.name:sha(p)for p in public.iterdir()if p.is_file()},indent=2))
    # Preserve all private config/auth/log evidence on the server only.
    (root/'preservation-seal.PRIVATE.json').write_text(json.dumps({str(p.relative_to(root)):sha(p)
        for p in root.rglob('*')if p.is_file()},indent=2))
    print(json.dumps({'root':str(root),'public':str(public),'phase':result['phase'],
        'model_calls':0,'task_actions':0,'scorer_transport_test_calls':result['scorer_calls']}))


if __name__ == '__main__':main(Path('/data/researcher/jev-defense-four-gpu-20261106') / ('environment-transport-preflight-' + str(time.time_ns())))
