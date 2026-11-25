"""Reconcile sealed browser operations and the private original URL scorer config."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

from collect import HERE, control, manifest_for, read, save, sha
from extract_on_host import canonical, hx
from link import verify


def specs(ledger):
    work = {}
    for row in ledger['rows']:
        tape = row['evidence']
        if tape is None:
            continue
        run = row['slot']['run_id']
        stage = row['stage_id']
        if stage not in work:
            ptr, manifest, _ = manifest_for(stage)
            keys = ('gui_experiment.py', 'capture_client.py', 'capture_source.py', 'native-sources.json',
                    'native-bindings-public.json', 'plan.json')
            work[stage] = {'package': manifest['package4090'], 'manifest_sha256': ptr['manifest_sha256'],
                           'files': {k: manifest['files'][k] for k in keys}, 'runs': {}}
        stage_runs = work[stage]['runs']
        assert run not in stage_runs and row['status'] == 'verified_terminal'
        stage_runs[run] = {'slot': row['slot'], 'attempt': tape['gui_attempt'],
                           'terminal_sha256': tape['terminal_sha256'], 'controller_head': tape['controller_head'],
                           'source_head': tape['source_head'], 'score_bound': tape['official_score_bound'],
                           'official_score': tape['terminal']['official_reward'],
                           'infra': tape['terminal']['infrastructure_failure'],
                           'outcome': tape['terminal']['outcome'],
                           'observed_native_actions': [s['executed'] for s in tape['steps'] if s['executed']]}
    return work


# Executed on the 4090 filesystem against immutable, owned browser archives.
# It does not open a browser, call the evaluator, or export the private task/trace contents.
EXECUTION = r'''
import ast, math, os, struct, zipfile
assert __name__=='evidence_library' and os.getuid()==1015
os.nice(10)

_SCROLL = {
    '(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop - window.innerHeight;': 'up',
    '(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop + window.innerHeight;': 'down',
}

def maps(native_files):
    path, = (Path(p) for p in native_files if Path(p).name == 'actions.py')
    assert sha(path)==native_files[str(path)]
    tree=ast.parse(path.read_bytes())
    assert any(isinstance(n,ast.ImportFrom) and n.module=='browser_env.constants' and
               any(a.name=='SPECIAL_KEY_MAPPINGS' and a.asname is None for a in n.names) for n in tree.body)
    alias_source=path.with_name('constants.py')
    raw=alias_source.read_bytes()
    tree=ast.parse(raw)
    mapping, = (n for n in tree.body if (
        isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id=='SPECIAL_KEY_MAPPINGS') or (
        isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='SPECIAL_KEY_MAPPINGS' for t in n.targets)))
    return ast.literal_eval(mapping.value),hx(raw)

def trace_primitives(path, start_url):
    calls=[]; end={}; initial_focus=False; starts=[]; viewport=None
    with zipfile.ZipFile(path) as z:
        assert [i.filename for i in z.infolist() if i.filename.endswith('.trace')]==['trace.trace']
        with z.open('trace.trace') as r:
            for line in r:
                x=json.loads(line); t=x['type']
                if t=='context-options':
                    viewport=x.get('options',{}).get('viewport')
                    assert viewport is None or (viewport['width'],viewport['height'])==(1280,720)
                elif t=='before':
                    method=x['method']; params=x.get('params',{}); payload=None
                    if method=='goto' and x['class']=='Frame':
                        starts.append(params['url'])
                    elif method=='mouseClick':
                        payload={'type':'click','x':params['x'],'y':params['y']}
                    elif method=='keyboardType':
                        payload={'type':'type','text':params['text']}
                    elif method=='keyboardPress':
                        payload={'type':'press','key':params['key']}
                    elif method=='goBack':
                        payload={'type':'back'}
                    elif method=='bringToFront':
                        if initial_focus:
                            payload={'type':'tab'}
                        else:
                            assert not calls and starts
                            initial_focus=True
                    elif method=='waitForTimeout' and params['timeout']==1000:
                        payload={'type':'wait'}
                    elif method=='evaluateExpression':
                        scroll=_SCROLL.get(params.get('expression','').strip())
                        if scroll is not None:
                            payload={'type':'scroll','direction':scroll}
                    if payload:
                        assert initial_focus
                        calls.append((x['callId'],method,x['startTime'],payload))
                elif t=='after':
                    assert x['callId'] not in end
                    end[x['callId']]=(x['endTime'], x.get('error'))
    assert starts==[start_url] and initial_focus, 'Trace startup not the frozen native page'
    assert len({cid for cid, _, _, _ in calls})==len(calls)
    return calls,end,viewport

def check_payload(raw, trace, aliases):
    kind=raw['type']
    assert trace['type']==kind
    if kind=='click':
        # Native helper casts normalized coordinates to float32 before viewport scaling.
        for key, scale in (('x',1280),('y',720)):
            normalized=struct.unpack('<f',struct.pack('<f',float(raw[key])/1000))[0]
            assert math.isclose(trace[key],normalized*scale,rel_tol=0,abs_tol=1e-7)
    elif kind=='press':
        mapped='+'.join(aliases.get(k.lower(),k) for k in str(raw['key']).split('+'))
        assert trace['key'] in (mapped,mapped.replace('Meta','Control'))
    elif kind in ('scroll','type'):
        name='direction' if kind=='scroll' else 'text'
        assert trace[name]==raw[name], (kind,'browser parameter disagrees with the native proposal')
    elif kind=='tab':
        # One Chromium focus call is visible, but v6 does not carry the controller's tab index.
        return 'operation_only_tab_index_not_in_trace'
    else:
        assert kind in ('back','wait')
    return 'native_parameter_bound'

def checked_run(p, sources, tasks, bindings, run, s, aliases):
    attempt=Path(s['attempt']); slot=s['slot']
    assert run==slot['run_id'] and attempt.parent==p/'batch/runs'/run
    assert not attempt.is_symlink() and not attempt.parent.is_symlink()
    seal=read(attempt/'seal.json')
    t=read(sealed(attempt,seal,'terminal.json'))
    assert seal['terminal.json']==s['terminal_sha256'] and t['run']==slot and t['outcome']==s['outcome']
    assert t.get('official_reward')==s['official_score'] and t['infrastructure_failure']==s['infra']
    assert (t.get('scoring_status')=='complete')==s['score_bound']
    protocol=read(sealed(attempt,seal,'protocol.json'))
    assert protocol=={'run':slot, 'seed':20261011, 'actor_seed':42, 'actor_max_tokens':2048,
        'max_steps':50, 'max_actor_calls':70, 'auxiliary_call_cap':None if slot['gate_enabled'] else 0,
        'max_recaptures':None if slot['gate_enabled'] else 0, 'full_main_history':True,
        'native_parser_and_executor_unchanged':True, 'same_live_recap':True,'no_contextual_judge':True}
    config=read(sealed(attempt,seal,'PRIVATE-official-config.json'))
    task=tasks[slot['task_id']]; b=bindings[slot['task_id']]
    original=Path(b['original_private_path']).read_bytes()
    assert hx(original)==b['original_private_SHA']==task['source_config_sha256']
    expected=json.loads(original.decode().replace('192.0.2.10:19980','192.0.2.10:29980'))
    expected['storage_state']=str(p/'batch/.auth/classifieds_state.json')
    assert config==expected and config['task_id']==task['task_id'] and config['intent']==task['intent']
    assert config['sites']==['classifieds'] and not config['require_reset']
    assert config['eval']['eval_types']==['url_match']

    controller, head=journal(sealed(attempt,seal,'controller/events.jsonl'))
    assert head==s['controller_head']
    emitted=data(controller,'native_environment_action')
    assert emitted==s['observed_native_actions']
    source, source_head=(journal(sealed(attempt,seal,'trusted-source/events.jsonl'),source=True)
                         if 'trusted-source/events.jsonl' in seal else ([],None))
    assert source_head==s['source_head']
    records=[x for x in source if x['kind']=='native_action_executed']
    assert [x['data']['sequence'] for x in records]==list(range(1,len(records)+1))
    assert len(emitted)<=len(records)<=len(emitted)+int(bool(s['infra']))
    assert [x['data']['ok'] for x in records[:len(emitted)]]==[a['ok'] for a in emitted]
    resets=data(source,'native_environment_reset')
    assert resets==[{'seed':20261011,'native_sources':sources}] or (not resets and s['infra'] and not records)
    scores=[x for x in source if x['kind']=='native_official_score']
    assert len(scores)==int(s['score_bound'])
    if scores:
        score,=scores
        assert (not s['infra'] or t.get('cleanup_error')) and score['data']['score']==s['official_score']
        assert s['official_score'] in (0,1)
        assert not records or source.index(records[-1])<source.index(score)
    else:
        score=None
        assert s['official_score'] is None
    action_evidence=[]; extras=[]; viewport=None; trace_status='missing_technical_evidence'
    trace_name='browser_trace.zip'
    if trace_name in seal:
        path=sealed(attempt,seal,trace_name)
        calls,ends,viewport=trace_primitives(path,config['start_url'])
        # A differently sized trace prefix is preserved as an unresolved technical lineage,
        # never silently used to validate a later successful/official result.
        assert len(emitted)<=len(calls)<=len(emitted)+int(bool(s['infra'])), (run,len(emitted),len(calls))
        for native,(cid,method,start,payload),src in zip(emitted,calls,records):
            kind=check_payload(native['payload'],payload,aliases)
            end,error=ends[cid]
            assert start<=end and native['ok']==(error is None)
            # Deliberately do not export typed strings, private URLs or browser snapshots.
            action_evidence.append({'decision':native['step'],'source_sequence':src['data']['sequence'],
                'source_action_event_sha256':src['sha256'],'controller_native_payload_sha256':hx(canonical(native['payload'])),
                'browser_native_payload_sha256':hx(canonical(payload)),'binding':kind,
                'call_id':cid,'method':method,'action_kind':payload['type'],'browser_returned_ok':error is None})
        extras=[{'call_id':cid,'method':method,'action_kind':payload['type']}
                for cid,method,_,payload in calls[len(emitted):]]
        trace_status='compared' if not extras and len(records)==len(emitted) else 'extra_terminal_source_or_browser_event'
    else:
        assert s['infra'], (run,'non-technical terminal missing browser trace')
    return {'terminal_sha256':s['terminal_sha256'],'controller_head':head,'trusted_source_head':source_head,
        'official_config_sha256':seal['PRIVATE-official-config.json'],'original_task_config_sha256':hx(original),
        'scorer_mode':'url_match','official_score':s['official_score'],
        'source_score_event_sha256':score['sha256'] if score else None,'protocol_sha256':seal['protocol.json'],
        'controller_action_count':len(emitted),'source_action_count':len(records),
        'trace_sha256':seal.get(trace_name),'trace_status':trace_status,'viewport_from_trace':viewport,
        'actions_in_browser_order':action_evidence,'extra_unbound_browser_operations':extras}

result={}; alias_sources={}
for stage,spec in WORK.items():
    p=Path(spec['package'])
    assert sha(p/'manifest.json')==spec['manifest_sha256']
    m=read(p/'manifest.json')
    for n,h in spec['files'].items():assert sha(p/n)==m['files'][n]==h
    sources=read(p/'native-sources.json')
    assert all(sha(Path(n))==d for n,d in sources.items())
    aliases,alias_sources[stage]=maps(sources)
    tasks=unique(read(p/'plan.json')['tasks'], lambda x:x['task_id'])
    bindings=unique(read(p/'native-bindings-public.json')['tasks'], lambda x:x['task_id'])
    result[stage]={run:checked_run(p,sources,tasks,bindings,run,s,aliases) for run,s in spec['runs'].items()}
print(json.dumps({'actual_uid':os.getuid(),'stages':result,'currently_read_native_key_alias_source_sha256':alias_sources,
                  'new_GUI_model_or_scorer_calls':0}))
'''


def check_results(ledger, result):
    expected = specs(ledger)
    assert set(result['stages']) == set(expected) and result['actual_uid'] == 1015
    assert result['new_GUI_model_or_scorer_calls'] == 0
    n = Counter()
    for stage, spec in expected.items():
        audited = result['stages'][stage]
        assert set(audited) == set(spec['runs'])
        for run, source in spec['runs'].items():
            r = audited[run]
            assert r['terminal_sha256'] == source['terminal_sha256'] and r['controller_head'] == source['controller_head']
            assert r['trusted_source_head'] == source['source_head'] and r['official_score'] == source['official_score']
            assert bool(r['source_score_event_sha256']) == source['score_bound'] and r['scorer_mode'] == 'url_match'
            assert r['controller_action_count'] == len(source['observed_native_actions'])
            assert r['controller_action_count'] <= r['source_action_count'] <= r['controller_action_count'] + int(bool(source['infra']))
            assert not r['actions_in_browser_order'] or len(r['actions_in_browser_order']) == r['controller_action_count']
            assert all(x['decision']==y['step'] and x['browser_returned_ok']==y['ok'] and
                       x['controller_native_payload_sha256']==hx(canonical(y['payload']))
                       for x,y in zip(r['actions_in_browser_order'],source['observed_native_actions']))
            if not source['infra']:
                assert r['trace_status']=='compared' and r['trace_sha256']
                assert len(r['actions_in_browser_order']) == r['controller_action_count']
            n['sealed_slots'] += 1
            n['official_score_receipts'] += source['score_bound']
            n['browser_traces'] += bool(r['trace_sha256'])
            n['controller_actions'] += r['controller_action_count']
            n['browser_parameter_bound_actions'] += sum(x['binding']=='native_parameter_bound' for x in r['actions_in_browser_order'])
            n['browser_operation_only_actions'] += sum(x['binding']!='native_parameter_bound' for x in r['actions_in_browser_order'])
            n['browser_bound_actions_returned_error'] += sum(not x['browser_returned_ok'] for x in r['actions_in_browser_order'])
            n['unreconciled_controller_actions'] += r['controller_action_count']-len(r['actions_in_browser_order'])
            n['unbound_extra_browser_operations'] += len(r['extra_unbound_browser_operations'])
    return dict(n)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger',type=Path)
    a=p.parse_args()
    verify(a.ledger)
    ledger=read(a.ledger/'private-linked.json')
    work=specs(ledger)
    assert work
    out=HERE/'native-execution-audits'/str(time.time_ns())
    control.ROOT=out
    library=(HERE/'extract_on_host.py').read_text(encoding='utf-8')
    receipt=control.remote('4090',"__name__='evidence_library'\nWORK="+repr(work)+'\n'+library+'\n'+EXECUTION,
                           'reconcile-saved-browser-native-actions-and-scores',timeout=85)
    operation=Path(receipt['operation'])
    verify(operation)
    assert read(operation/'stdout.bin')==receipt['result']
    counts=check_results(ledger,receipt['result'])
    result={'ledger_seal_sha256':sha(a.ledger/'seal.json'),'operation':str(operation),
            'operation_seal_sha256':sha(operation/'seal.json'),'evidence_counts':counts,'result':receipt['result'],
            'scope':'Read-only: archived Playwright operations and original native URL scoring events; '
                    'no browser replay, task rescore, loaded-JavaScript reexecution, or private answer export. '
                    'Browser OK does not assert that the page visibly changed or the intended task advanced.'}
    save(out/'index.json',result)
    save(out/'seal.json',{'index.json':sha(out/'index.json')})
    print(json.dumps({'audit':str(out),'seal_sha256':sha(out/'seal.json'),**counts}))


if __name__=='__main__':
    main()
