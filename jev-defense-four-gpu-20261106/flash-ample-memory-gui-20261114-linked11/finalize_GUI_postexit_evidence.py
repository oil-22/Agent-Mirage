"""Bounded fresh final audit after the original29 GUI and all services exit.

Read-only with respect to experiments. Audit artifacts are separate. No model,
browser, scorer, launch, retry, cleanup or old queue entry point is invoked.
"""
import argparse
import ast
import base64
import json
import time
from pathlib import Path

from control import HERE, OUT, R3090, R4090, remote, save, sha
from capture_live_evidence import COMMON


def load(p):
    return json.loads(p.read_bytes())


def sources():
    original = HERE / 'capture_live_evidence.py'
    constants = [n.value for n in ast.walk(ast.parse(original.read_text('utf8')))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    source = next(v for v in constants if v.startswith('\nimport subprocess\np=Path(PACKAGE);'))
    main_start = source.index("for d in sorted((r/'primary/requests').iterdir()):")
    flash_start = source.index("for d in sorted((p/'flash/service/requests').iterdir()):")
    end = source.index("out['primary_loaded']")
    main = source[main_start:flash_start].replace(
        "for d in sorted((r/'primary/requests').iterdir()):",
        "for d in [r/'primary/requests'/name for name in SELECTED]:")
    # Every original per-request assertion is retained; these checks bind the
    # complete postexit seal and original system in addition to those checks.
    main = main.replace(" template=json.loads((p/'actor-template.json').read_bytes());",
                        " assert wire['body']['messages'][0]==json.loads((p/'actor-template.json').read_bytes())['messages'][0]\n template=json.loads((p/'actor-template.json').read_bytes());")
    flash = source[flash_start:end].replace(
        "for d in sorted((p/'flash/service/requests').iterdir()):",
        "for d in [p/'flash/service/requests'/name for name in SELECTED]:")
    final_binding = r'''
 expected={str(d.relative_to(BASE))/name:h for name,h in seal.items()}
 expected[str(d.relative_to(BASE))+'/seal.json']=sha(d/'seal.json')
 actual={name:h for name,h in GLOBAL.items()if name.startswith(str(d.relative_to(BASE))+'/')}
 assert expected==actual
 assert {v.name for v in d.iterdir()if v.is_file()}==set(seal)|{'seal.json'}
'''
    main += final_binding
    flash += final_binding
    # Native raw tensors and no-KV/single-image request checks above are the
    # original live checks, usable after exit without asserting live old PIDs.
    constants = [n.value for n in ast.walk(ast.parse((HERE / 'audit_flash_live.py').read_text('utf8')))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    cpu = next(v for v in constants if v.startswith('\nimport hashlib,json,os,time'))
    cpu = cpu.replace('ROOT', repr(R3090)).replace(
        "for d in sorted((root/'service/requests').iterdir()):",
        "for d in [root/'service/requests'/name for name in SELECTED]:")
    for text in [COMMON + main, COMMON + flash, cpu]:
        compile(text, '<preserved-postexit-checks>', 'exec')
    return main, flash, cpu


def admission(host):
    root = OUT if host == '3090' else R4090
    code = ('ROOT=' + repr(root) + '\nPACKAGE=' + repr(R3090) + '\nHOST=' + repr(host)
            + '\nEXPECTED_MANIFEST=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + COMMON + r'''
r=Path(ROOT);p=Path(PACKAGE)
source=p if HOST=='3090'else r
assert sha(source/'manifest.json')==EXPECTED_MANIFEST
for name,h in json.loads((source/'manifest.json').read_bytes())['files'].items():assert sha(source/name)==h
if HOST=='3090':
 paths=[r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']
 status=json.loads((r/'primary/status.json').read_bytes());terminal=json.loads((r/'primary/terminal.json').read_bytes())
 assert status['phase']=='completed'and status['done']==status['expected']==29 and status['active']is None
 assert terminal['status']=='completed'and terminal['done']==terminal['expected']==29
 group=json.loads((r/'exit.json').read_bytes());assert group['exit_code']==0 and group['failure']is None and all(v['exit_code']==0 for v in group['children'])
else:
 paths=[r/'control/process.json',r/'control/runner-process.json']
 status=json.loads((r/'batch/status.json').read_bytes());terminal=None
 assert status['phase']=='completed'and status['completed']==status['processed']==status['expected']==29
 group=json.loads((r/'control/exit.json').read_bytes());assert group['child_exit']==0
processes=[]
for path in paths:
 record=json.loads(path.read_bytes());proc=Path('/proc',str(record['pid']));actual=identity(record['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==record[k]for k in ['pid','uid','command','start_ticks'])
 assert not same,'Original process still live; wait without restart'
 processes.append({'saved':record,'actual_if_PID_exists':actual,'same_live_process':False})
seal=r/'postexit-seal.json'if HOST=='3090'else r/'control/postexit-seal.json'
assert seal.exists();expected=json.loads(seal.read_bytes())
out={'time':time.time(),'original_processes_exited':processes,'status':status,'terminal':terminal,'group_exit':group,'postexit_seal_sha256':sha(seal),'postexit_entries':expected,'new_model_GPU_GUI_calls':0}
if HOST=='3090':
 out['main_names']=[v.name for v in sorted((r/'primary/requests').iterdir())if v.is_dir()]
 out['Flash_names']=[v.name for v in sorted((p/'flash/service/requests').iterdir())if v.is_dir()]
 assert all((r/'primary/requests'/name/'seal.json').exists()for name in out['main_names'])
 assert all((p/'flash/service/requests'/name/'seal.json').exists()for name in out['Flash_names'])
 assert len(out['main_names'])==terminal['attempted_actor_calls']==terminal['complete_actor_replies']
 for name in ['main','Flash']:
  path=r/'primary/journal/events.jsonl'if name=='main'else p/'flash/service/journal/events.jsonl'
  proof,events=chain(path);assert not proof['ignored_partial_last_line'];out[name+'_chain']=proof
else:
 runs=list((r/'batch/runs').glob('*/attempt-*/terminal.json'));assert len(runs)==29 and all((v.parent/'seal.json').exists()for v in runs)
print(json.dumps(out))
''')
    raw, op = remote(host, code, 'postexit-completion-and-actual-exit-' + host, timeout=55)
    return {'result': json.loads(raw), 'operation': str(op)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    native, flash, cpu = sources()
    if args.prepare_only:
        root = HERE / ('postexit-audit-preparation-' + str(time.time_ns()))
        root.mkdir()
        (root / 'source.py').write_bytes(Path(__file__).read_bytes())
        for name, text in [('native-selection-template.py', native), ('Flash-selection-template.py', flash), ('Flash-CPU-template.py', cpu)]:
            (root / name).write_text(text, encoding='utf8')
        save(root / 'preparation.json', {'time': time.time(), 'original_native_inspector_sha256': sha(HERE / 'capture_live_evidence.py'),
             'original_Flash_CPU_inspector_sha256': sha(HERE / 'audit_flash_live.py'),
             'original_per_request_raw_checks_retained': True, 'all29_and_actual_exits_required': True,
             'old_live_process_assertions_replaced_only_by_verified_postexit_admission': True,
             'fresh_full_raw_rehash_only_after_exit': True, 'postexit_global_seal_coverage_required': True,
             'current_runtime_sources_changed': False, 'no_weight_rehash_or_generation': True,
             'new_model_GPU_GUI_calls': 0, 'prepared_only_not_final_audit': True})
        save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(root), 'actual_final_audit_executed': False, 'new_model_GPU_GUI_calls': 0}))
        return
    assert not (HERE / 'postexit-evidence-current.json').exists(), 'Inspect existing final evidence; never overwrite'
    # No output is treated as final unless both independent hosts prove normal
    # complete29 and actual exits. An observation failure is not a job failure.
    original_main, original_gui = admission('3090'), admission('4090')
    root = HERE / ('full-postexit-evidence-' + str(time.time_ns()))
    root.mkdir()
    (root / 'inspector-source.py').write_bytes(Path(__file__).read_bytes())
    save(root / '3090-admission.json', original_main)
    save(root / '4090-admission.json', original_gui)
    admitted = original_main['result']
    global_seal = admitted['postexit_entries']
    main_rows, flash_rows, cpu_rows, last_per_run = [], [], [], {}
    for label, names, template in [('main', admitted['main_names'], native), ('Flash', admitted['Flash_names'], flash)]:
        for index, name in enumerate(names):
            boundaries = list(last_per_run.values()) if label == 'main' else []
            # Only prior body/reply boundaries are needed to preserve full
            # legal history assertions across one-request batches.
            boundary = r'''
for row in BOUNDARIES:
 d=Path(row['folder']);seal=json.loads((d/'seal.json').read_bytes());assert sha(d/'seal.json')==row['seal_sha256']
 for n in ['wire-request.bin','response.json']:assert sha(d/n)==seal[n]
 w=json.loads((d/'wire-request.bin').read_bytes());a=json.loads((d/'response.json').read_bytes());history[w['run_id']]=w['body']['messages']+[{'role':'assistant','content':a['text']}]
'''
            code = ('PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\nSELECTED=' + repr([name])
                    + '\nGLOBAL=' + repr(global_seal) + '\nBOUNDARIES=' + repr(boundaries) + '\n' + COMMON
                    + "p=Path(PACKAGE);r=Path(OUTPUT);BASE=r if LABEL=='main'else p;history={};out={'sealed_main_requests':[],'sealed_Flash_requests':[]}\n")
            code = 'LABEL=' + repr(label) + '\n' + code + boundary + template + '\nprint(json.dumps(out))\n'
            raw, op = remote('3090', code, 'fresh-postexit-full-raw-' + label + '-' + name, timeout=55)
            result = json.loads(raw)
            save(root / (label + '-%05d.json' % index), {'result': result, 'operation': str(op)})
            values = result['sealed_main_requests' if label == 'main' else 'sealed_Flash_requests']
            assert len(values) == 1
            if label == 'main':
                main_rows.extend(values)
                last_per_run[values[0]['run_id']] = values[0]
            else:
                flash_rows.extend(values)
            print(json.dumps({'fresh_raw_' + label: index + 1, 'expected': len(names)}), flush=True)
    # Request folders just rehashed above must cover the same full global
    # snapshot. Everything else in that snapshot is also freshly hashed.
    other = {n: h for n, h in global_seal.items() if not n.startswith(('primary/requests/', 'flash/service/requests/'))}
    entries = list(other.items())
    for index in range(0, len(entries), 20):
        code = 'ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\nROWS=' + repr(entries[index:index + 20]) + '\n' + COMMON + r'''
r=Path(ROOT);p=Path(PACKAGE)
for name,h in ROWS:
 q=(p if name.startswith('flash/service/')else r)/name
 assert q.is_file()and sha(q)==h
print(json.dumps({'files_freshly_verified':len(ROWS),'new_model_GUI_calls':0}))
'''
        raw, op = remote('3090', code, 'fresh-postexit-other-files-' + str(index), timeout=55)
        save(root / ('other-%05d.json' % index), {'result': json.loads(raw), 'operation': str(op)})
    control_entries = list(original_gui['result']['postexit_entries'].items())
    for index in range(0, len(control_entries), 20):
        code = 'ROOT=' + repr(R4090) + '\nROWS=' + repr(control_entries[index:index + 20]) + '\n' + COMMON + r'''
r=Path(ROOT)/'control'
for name,h in ROWS:assert sha(r/name)==h
print(json.dumps({'GUI_control_files_freshly_verified':len(ROWS),'new_model_GUI_calls':0}))
'''
        raw, op = remote('4090', code, 'fresh-postexit-GUI-control-files-' + str(index), timeout=55)
        save(root / ('GUI-control-%05d.json' % index), {'result': json.loads(raw), 'operation': str(op)})
    for index in range(0, len(admitted['Flash_names']), 8):
        raw, op = remote('3090', 'SELECTED=' + repr(admitted['Flash_names'][index:index + 8]) + '\n' + cpu,
                         'postexit-Flash-full-native-CPU-' + str(index), timeout=55)
        value = json.loads(raw)
        assert value['GPU_allocations_by_audit'] == value['new_inference_by_audit'] == 0
        cpu_rows.extend(value['requests'])
        save(root / ('Flash-CPU-%05d.json' % index), {'result': value, 'operation': str(op)})
    assert {v['request_id']: v['seal_sha256'] for v in cpu_rows} == {v['request_id']: v['seal_sha256'] for v in flash_rows}
    # The existing terminal inspector needs no live process and hashes every
    # terminal file/chain. Its source is used without executing its CLI here.
    tree = ast.parse((HERE / 'inspect_terminals.py').read_text('utf8'))
    expr = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'code' for t in n.targets))
    code = eval(compile(ast.Expression(expr.value), '<terminal-inspector-expression>', 'eval'), {'R4090': R4090, 'repr': repr})
    raw, op = remote('4090', code, 'postexit-all29-terminal-files-and-chains', timeout=55)
    terminal_audit = json.loads(raw)
    assert len(terminal_audit['terminals']) == 29
    assert not any(v['infrastructure_failure'] or v['cleanup_error'] for v in terminal_audit['terminals'])
    save(root / 'terminal-audit.json', {'result': terminal_audit, 'operation': str(op)})
    # Recheck the global seals and actual exits at the end of this potentially
    # long read-only audit. New idle foreign jobs do not alter old evidence.
    final_main, final_gui = admission('3090'), admission('4090')
    assert final_main['result']['postexit_seal_sha256'] == admitted['postexit_seal_sha256']
    assert final_gui['result']['postexit_seal_sha256'] == original_gui['result']['postexit_seal_sha256']
    save(root / 'final-admission.json', {'3090': final_main, '4090': final_gui})
    save(root / '3090.json', {'sealed_main_requests': main_rows, 'sealed_Flash_requests': flash_rows,
         'fresh_full_raw_rehash': True, 'original_processes_exited': admitted['original_processes_exited']})
    save(root / 'summary.json', {'time': time.time(), 'fresh_full_main_requests': len(main_rows),
         'fresh_full_Flash_requests': len(flash_rows), 'fresh_Flash_CPU_probability_inputs': len(cpu_rows),
         'global3090_postexit_entries_verified': len(global_seal), 'terminal_count': 29,
         'GUI_control_postexit_entries_verified': len(control_entries),
         'original_processes_exited': True, 'historical_live_ownership_not_claimed_current': True,
         'controller_cross_host_binding_finalization_still_required': True,
         'semantic_completion_or_effectiveness_proven': False, 'new_model_GPU_GUI_calls': 0})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'postexit-evidence-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
         'raw_postexit_audit_only': True, 'controller_cross_host_binding_finalization_still_required': True,
         'goal': 'active', 'time': time.time()})
    print(json.dumps({'evidence': str(root), 'new_model_GPU_GUI_calls': 0,
                      'effectiveness_proven': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
