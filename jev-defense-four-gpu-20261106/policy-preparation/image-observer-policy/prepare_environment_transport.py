"""Create a linked real native scorer-transport source without running it here."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parent=ROOT/'environment_preflight_refresh.py'
text=parent.read_text(encoding='utf8')
text=text.replace('No task action or scorer execution.','One actual native initial-state scorer transport check, no model/task-agent action.')
before="""        # Resume only these exact owned containers; never initialize/reset/import fixtures.
        if not rows[1]['State']['Running']:subprocess.run(['docker', 'start', identities[1]], check=True, capture_output=True)
        if not rows[0]['State']['Running']:subprocess.run(['docker', 'start', identities[0]], check=True, capture_output=True)
"""
assert text.count(before)==1
text=text.replace(before,"""        # This linked check is read-only against already-running exact owned sites.
        assert all(c['State']['Running'] for c in rows), 'Owned source sites are stopped; no automatic restart in this check'
""")
text=text.replace("        from browser_env import ScriptBrowserEnv\n", "        from browser_env import ScriptBrowserEnv\n        from browser_env.actions import create_stop_action\n")
block="""        # Original parser and native action constructors, CPU only. None is passed
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
"""
needle="        # Same historical navigation timeout, no change to task actions or observations.\n"
assert text.count(needle)==1;text=text.replace(needle,block+needle)
needle="""            scorer = evaluator_router(config)
            result.update(phase='environment_preflight_complete', actual_url=env.page.url,
"""
replacement="""            scorer = evaluator_router(config)
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
"""
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="""        result.update(phase='technical_failure', error=type(error).__name__ + ': ' + str(error))
        (root / 'traceback.txt').write_text(traceback.format_exc())
    (root / 'receipt.json').write_text(json.dumps(result, indent=2))
    (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
        for p in root.rglob('*') if p.is_file() and '.auth' not in p.parts}, indent=2))
    print(json.dumps({'root': str(root), 'phase': result['phase'], 'error': result.get('error'),
                      'model_calls': 0, 'task_actions': 0}))
"""
replacement="""        result.update(phase='technical_failure', error_type=type(error).__name__,
                      error='See preserved remote traceback.PRIVATE.txt; no automatic retry')
        (root / 'traceback.PRIVATE.txt').write_text(traceback.format_exc())
    result['not_a_formal_defense_result']=True
    result['linked_parent_source_sha256']='PARENT_SOURCE_SHA'
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
""".replace('PARENT_SOURCE_SHA',hashlib.sha256(parent.read_bytes()).hexdigest())
assert text.count(needle)==1;text=text.replace(needle,replacement)
text=text.replace("'environment-preflight-' + str(time.time_ns())", "'environment-transport-preflight-' + str(time.time_ns())")
target=ROOT/'environment_transport_preflight.py'
with target.open('x',encoding='utf8')as f:f.write(text)
compile(text,str(target),'exec')
receipt={'source':str(target),'source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'parent_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),'expected_scorer_calls':1,
    'model_calls':0,'task_agent_actions':0,'private_config_auth_exported':False}
with (ROOT/'environment-transport-preparation.json').open('x',encoding='utf8')as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
