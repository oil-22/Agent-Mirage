"""Fresh raw audit of one immutable exited GUI model group, including rejection.

The parent can be audited while its continuation is running. This never claims
all29 completed, never enters a model/browser/launcher, and never imports the
old finalizer. Original per-request checks are extracted as data, not rerun CLI.
"""
import argparse
import ast
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha
from capture_live_evidence import COMMON

OLD = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'


def load(path):
    return json.loads(Path(path).read_bytes())


def strings(path):
    return [n.value for n in ast.walk(ast.parse(path.read_text('utf8')))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def templates(package):
    src = next(v for v in strings(HERE / 'capture_live_evidence.py')
               if v.startswith('\nimport subprocess\np=Path(PACKAGE);'))
    a = src.index("for d in sorted((r/'primary/requests').iterdir()):")
    b = src.index("for d in sorted((p/'flash/service/requests').iterdir()):")
    c = src.index("out['primary_loaded']")
    native = src[a:b].replace("for d in sorted((r/'primary/requests').iterdir()):",
                              "for d in [r/'primary/requests'/NAME]:")
    native = native.replace(" template=json.loads((p/'actor-template.json').read_bytes());",
        " assert json.loads((d/'body.json').read_bytes())==wire['body']\n assert wire['body']['messages'][0]==json.loads((p/'actor-template.json').read_bytes())['messages'][0]\n template=json.loads((p/'actor-template.json').read_bytes());")
    flash = src[b:c].replace("for d in sorted((p/'flash/service/requests').iterdir()):",
                             "for d in [p/'flash/service/requests'/NAME]:")
    binding = r'''
prefix=str(d.relative_to(BASE))+'/'
expected={prefix+name:h for name,h in seal.items()};expected[prefix+'seal.json']=sha(d/'seal.json')
assert {n:h for n,h in GLOBAL.items()if n.startswith(prefix)}==expected
assert {f.name for f in d.iterdir()if f.is_file()}==set(seal)|{'seal.json'}
assert all(f.is_file()for f in d.iterdir())
'''
    native += binding
    flash += binding
    failed = [v for v in strings(OLD / 'capture_stopped_tail_evidence.py')
              if "d=r/'primary/requests/00397';seal=" in v]
    assert len(failed) == 1
    failed = failed[0].split("assert len(out['sealed_main_requests'])==2")[0] + binding
    cpu = next(v for v in strings(HERE / 'audit_flash_live.py')
               if v.startswith('\nimport hashlib,json,os,time'))
    cpu = cpu.replace('ROOT', repr(package)).replace(
        "for d in sorted((root/'service/requests').iterdir()):",
        "for d in [root/'service/requests'/name for name in SELECTED]:")
    for text in [native, flash, failed]:
        compile(COMMON + text, '<fresh-exited-original-checks>', 'exec')
    compile(cpu, '<fresh-exited-Flash-CPU-checks>', 'exec')
    return native, flash, failed, cpu


ADMISSION = r'''
p=Path(PACKAGE);r=Path(OUTPUT);assert os.getuid()==1033
assert sha(p/'manifest.json')==EXPECTED_MANIFEST
for name,h in json.loads((p/'manifest.json').read_bytes())['files'].items():assert sha(p/name)==h,name
status=json.loads((r/'primary/status.json').read_bytes());terminal=json.loads((r/'primary/terminal.json').read_bytes());group=json.loads((r/'exit.json').read_bytes())
if GROUP=='parent':
 assert sha(r/'postexit-seal.json')==EXPECTED_POSTEXIT
 assert status['phase']=='technical_failure'and status['done']==16 and status['expected']==29
 assert status['attempted_actor_calls']==397 and status['complete_actor_replies']==396
 assert group['exit_code']==1 and group['failure']is None
else:
 assert status['phase']=='completed'and status['done']==status['expected']==13 and status['active']is None
 assert terminal['status']=='completed'and terminal['done']==terminal['expected']==13
 assert terminal['attempted_actor_calls']==terminal['complete_actor_replies']
 assert group['exit_code']==0 and group['failure']is None and all(v['exit_code']==0 for v in group['children'])
processes=[]
for f in [r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']:
 saved=json.loads(f.read_bytes());proc=Path('/proc',str(saved['pid']));actual=identity(saved['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
 assert not same,'This group still runs; no postexit raw admission'
 processes.append({'saved':saved,'actual_if_PID_exists':actual,'same_live_process':False})
post=json.loads((r/'postexit-seal.json').read_bytes())
actual={str(f.relative_to(r))for f in r.rglob('*')if f.is_file()and f.name!='postexit-seal.json'}|{str(f.relative_to(p))for f in(p/'flash/service').rglob('*')if f.is_file()and f.name!='token'}
assert set(post)==actual
main_names=[f.name for f in sorted((r/'primary/requests').iterdir())];Flash_names=[f.name for f in sorted((p/'flash/service/requests').iterdir())]
assert all((r/'primary/requests'/n/'seal.json').exists()for n in main_names)
assert all((p/'flash/service/requests'/n/'seal.json').exists()for n in Flash_names)
assert len(main_names)==terminal['attempted_actor_calls']
if GROUP=='parent':assert len(main_names)==397 and len(Flash_names)==199
proofs={}
for label,path in [('main',r/'primary/journal/events.jsonl'),('Flash',p/'flash/service/journal/events.jsonl')]:
 proof,events=chain(path);assert not proof['ignored_partial_last_line'];proofs[label]=proof
print(json.dumps({'time':time.time(),'group':GROUP,'package':str(p),'output':str(r),'postexit_entries':post,
 'postexit_seal_sha256':sha(r/'postexit-seal.json'),'main_names':main_names,'Flash_names':Flash_names,
 'processes_actually_exited':processes,'chains':proofs,'status':status,'terminal':terminal,'group_exit':group,
 'new_model_GPU_GUI_calls':0,'all29_completion_claimed':False}))
'''


BOUNDARY = r'''
for row in BOUNDARIES:
 if row['run_id']!=CURRENT_RUN:continue
 d=Path(row['folder']);s=json.loads((d/'seal.json').read_bytes());assert sha(d/'seal.json')==row['seal_sha256']
 for n in ['wire-request.bin','body.json','response.json']:assert sha(d/n)==s[n]
 w=json.loads((d/'wire-request.bin').read_bytes());a=json.loads((d/'response.json').read_bytes());history[w['run_id']]=w['body']['messages']+[{'role':'assistant','content':a['text']}]
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=['parent', 'continuation'], required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    b = load(HERE / 'package/parent-bindings.json')
    parent = args.group == 'parent'
    package = b['package3090'] if parent else '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
    output = b['output3090'] if parent else '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    expected = b['manifest_sha256'] if parent else sha(HERE / 'package/manifest.json')
    native, flash, failure, cpu = templates(package)
    prefix = ('PACKAGE=' + repr(package) + '\nOUTPUT=' + repr(output) + '\nGROUP=' + repr(args.group)
              + '\nEXPECTED_MANIFEST=' + repr(expected) + '\nEXPECTED_POSTEXIT=' + repr(b['postexit_seal_sha256']) + '\n' + COMMON)
    compile(prefix + ADMISSION, '<exited-group-admission>', 'exec')
    if args.prepare_only:
        dest = HERE / ('exited-group-raw-reader-preparation-' + args.group + '-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        for name, text in [('native', native), ('Flash', flash), ('failure', failure), ('CPU', cpu)]:
            (dest / (name + '-reader.py')).write_text(text, encoding='utf8')
        save(dest / 'preparation.json', {'time': time.time(), 'group': args.group,
             'readers_compiled_only_not_executed': True, 'original_success_checks_preserved': True,
             'failed00397_has_separate_rejection_branch_never_a_public_reply': True,
             'new_model_GPU_GUI_calls': 0, 'all29_completion_claimed': False})
        save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
        print(json.dumps({'preparation': str(dest), 'actual_raw_audit_executed': False}))
        return
    pointer = HERE / ('exited-' + args.group + '-raw-current.json')
    assert not pointer.exists(), 'Use the completed immutable raw audit; do not repeat'
    if args.resume:
        dest = args.resume.resolve()
        assert dest.parent == HERE and dest.name.startswith('fresh-exited-' + args.group + '-raw-')
        assert not (dest / 'seal.json').exists()
        assert sha(dest / 'source.py') == sha(Path(__file__)), 'Resumption must use identical reader source'
        admitted = load(dest / 'admission.json')['result']
    else:
        raw, op = remote('3090', prefix + ADMISSION, 'fresh-exited-' + args.group + '-raw-admission')
        admitted = json.loads(raw)
        dest = HERE / ('fresh-exited-' + args.group + '-raw-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        save(dest / 'admission.json', {'result': admitted, 'operation': str(op)})
    global_seal = admitted['postexit_entries']
    last = {}
    mains, flashes, failed, cpu_rows = [], [], [], []
    for label, names, template in [('main', admitted['main_names'], native), ('Flash', admitted['Flash_names'], flash)]:
        for name in names:
            resultfile = dest / (label + '-' + name + '.json')
            technical = parent and label == 'main' and name == '00397'
            if resultfile.exists():
                value = load(resultfile)
                assert value['reader_source_sha256'] == sha(dest / 'source.py')
                result = value['result']
            else:
                boundaries = [last[v] for v in sorted(last)] if label == 'main' else []
                code = (prefix + '\nNAME=' + repr(name) + '\nGLOBAL=' + repr(global_seal)
                    + '\nBOUNDARIES=' + repr(boundaries) + '\n'
                    + "r=Path(OUTPUT);p=Path(PACKAGE);history={};out={'sealed_main_requests':[],'sealed_Flash_requests':[],'failed_requests':[]};BASE="
                    + ('r' if label == 'main' else 'p') + '\nCURRENT_RUN='
                    + ("json.loads((r/'primary/requests'/NAME/'wire-request.bin').read_bytes())['run_id']" if label == 'main' else 'None')
                    + '\n' + BOUNDARY
                    + (failure if technical else template) + '\nprint(json.dumps(out))\n')
                raw, op = remote('3090', code, 'fresh-exited-' + args.group + '-' + label + '-' + name, timeout=55)
                result = json.loads(raw)
                save(resultfile, {'result': result, 'operation': str(op), 'reader_source_sha256': sha(dest / 'source.py')})
            if technical:
                assert len(result['failed_requests']) == 1 and not result['sealed_main_requests']
                failed.extend(result['failed_requests'])
            elif label == 'main':
                assert len(result['sealed_main_requests']) == 1
                mains.extend(result['sealed_main_requests'])
                row = result['sealed_main_requests'][0]
                last[row['run_id']] = row
            else:
                assert len(result['sealed_Flash_requests']) == 1
                flashes.extend(result['sealed_Flash_requests'])
            if (int(name) % 10 == 0 if label == 'main' else len(flashes) % 20 == 0):
                print(json.dumps({'raw_audit': str(dest), 'group': args.group, 'main': len(mains),
                                  'Flash': len(flashes), 'preserved_failure': len(failed)}), flush=True)
    other = [(n, h) for n, h in global_seal.items()
             if not n.startswith(('primary/requests/', 'flash/service/requests/'))]
    for index in range(0, len(other), 12):
        path = dest / ('other-%05d.json' % index)
        if path.exists():
            continue
        code = prefix + '\nROWS=' + repr(other[index:index + 12]) + '\n' + r'''
r=Path(OUTPUT);p=Path(PACKAGE)
for name,h in ROWS:assert sha((p if name.startswith('flash/service/')else r)/name)==h,name
print(json.dumps({'time':time.time(),'files_freshly_rehashed':len(ROWS),'new_model_GPU_GUI_calls':0}))
'''
        raw, op = remote('3090', code, 'fresh-exited-' + args.group + '-other-' + str(index), timeout=55)
        save(path, {'result': json.loads(raw), 'operation': str(op)})
    for index in range(0, len(admitted['Flash_names']), 8):
        path = dest / ('CPU-%05d.json' % index)
        if path.exists():
            value = load(path)['result']
        else:
            raw, op = remote('3090', 'SELECTED=' + repr(admitted['Flash_names'][index:index + 8]) + '\n' + cpu,
                             'fresh-exited-' + args.group + '-Flash-CPU-' + str(index), timeout=55)
            value = json.loads(raw)
            assert value['GPU_allocations_by_audit'] == value['new_inference_by_audit'] == 0
            save(path, {'result': value, 'operation': str(op)})
        cpu_rows.extend(value['requests'])
    assert {v['request_id']: v['seal_sha256'] for v in cpu_rows} == {v['request_id']: v['seal_sha256'] for v in flashes}
    assert len(mains) == admitted['terminal']['complete_actor_replies']
    assert len(mains) + len(failed) == len(admitted['main_names'])
    assert len(failed) == (1 if parent else 0)
    raw, op = remote('3090', prefix + ADMISSION, 'fresh-exited-' + args.group + '-audit-final-identity-recheck')
    final = json.loads(raw)
    assert final['postexit_seal_sha256'] == admitted['postexit_seal_sha256'] and final['chains'] == admitted['chains']
    save(dest / 'final-admission.json', {'result': final, 'operation': str(op)})
    save(dest / '3090.json', {'sealed_main_requests': mains, 'sealed_Flash_requests': flashes,
         'failed_requests': failed, 'fresh_full_raw_rehash': True,
         'original_processes_exited': final['processes_actually_exited']})
    save(dest / 'Flash-CPU.json', {'result': {'requests': cpu_rows, 'verified_complete_Flash_replies': len(cpu_rows),
         'new_inference_by_audit': 0, 'GPU_allocations_by_audit': 0}})
    save(dest / 'summary.json', {'time': time.time(), 'group': args.group,
         'fresh_full_complete_main_requests': len(mains), 'fresh_full_Flash_requests': len(flashes),
         'separately_preserved_failed_native_generations': len(failed),
         'full_postexit_manifest_files_freshly_rehashed': len(global_seal),
         'actual_original_group_process_exits_verified': True,
         'request_and_nonrequest_files_complete_under_original_global_seal': True,
         'fresh_Flash_CPU_tensor_and_probability_bindings': len(cpu_rows),
         'not_current_GPU_ownership_evidence': True, 'all29_completion_claimed': False,
         'full_GUI_controller_audit_still_required': True, 'new_model_GPU_GUI_calls': 0,
         'Mirage_reduction': None})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    save(pointer, {'root': str(dest), 'seal_sha256': sha(dest / 'seal.json'),
         'group': args.group, 'all29_completion_claimed': False, 'time': time.time()})
    print(json.dumps({'raw_audit': str(dest), 'complete_main': len(mains), 'Flash': len(flashes),
                      'separate_failures': len(failed), 'new_model_GPU_GUI_calls': 0}))


if __name__ == '__main__':
    main()
