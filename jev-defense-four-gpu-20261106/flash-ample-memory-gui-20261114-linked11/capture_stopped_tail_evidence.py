"""Read-only tail audit after verified model/GUI exit, preserving technical failure.

Prior raw checks retain their times. This is not the final full postexit rehash.
All original success-request checks are retained. Request 397 is audited through
a separate rejection branch and can never enter the delivered-success list.
"""
import ast
import json
import time
from pathlib import Path
from control import HERE, OUT, R3090, R4090, remote, save, sha
from capture_live_evidence import COMMON


def load(p):
    return json.loads(p.read_bytes())


def main():
    prior = HERE / 'live-evidence-incremental-1794670466470514000'
    assert all(sha(prior / n) == h for n, h in load(prior / 'seal.json').items())
    previous = load(prior / '3090.json')
    before = load(prior / 'summary.json')
    assert len(previous['sealed_main_requests']) == 394
    assert len(previous['sealed_Flash_requests']) == 197
    constants = [v.value for v in ast.walk(ast.parse((HERE / 'capture_live_evidence.py').read_text('utf8')))
                 if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    original = next(v for v in constants if v.startswith('\nimport subprocess\np=Path(PACKAGE);'))
    start = original.index("for d in sorted((r/'primary/requests').iterdir()):")
    middle = original.index("for d in sorted((p/'flash/service/requests').iterdir()):")
    end = original.index("out['primary_loaded']")
    success = original[start:middle].replace(
        "for d in sorted((r/'primary/requests').iterdir()):",
        "for d in [r/'primary/requests'/name for name in ['00395','00396']]:")
    success = success.replace(" template=json.loads((p/'actor-template.json').read_bytes());",
        " assert wire['body']['messages'][0]==json.loads((p/'actor-template.json').read_bytes())['messages'][0]\n template=json.loads((p/'actor-template.json').read_bytes());")
    flash = original[middle:end].replace(
        "for d in sorted((p/'flash/service/requests').iterdir()):",
        "for d in [p/'flash/service/requests'/name for name in FLASH_NAMES]:")
    old_main = {Path(v['folder']).name: v['seal_sha256'] for v in previous['sealed_main_requests']}
    old_flash = {v['request_id']: v['seal_sha256'] for v in previous['sealed_Flash_requests']}
    boundary = previous['sealed_main_requests'][-1]
    assert Path(boundary['folder']).name == '00394'
    code = ('PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\nOLD_MAIN=' + repr(old_main)
        + '\nOLD_FLASH=' + repr(old_flash) + '\nBOUNDARY=' + repr(boundary)
        + '\nPREFIX=' + repr({'main': before['main_chain'], 'Flash': before['Flash_chain']})
        + '\n' + COMMON + r'''
p=Path(PACKAGE);r=Path(OUTPUT);out={'time':time.time(),'processes':{},'sealed_main_requests':[],'sealed_Flash_requests':[],'failed_requests':[]};history={}
for label,file in [('primary',r/'primary/process.json'),('Flash',p/'flash/service/process.json')]:
 record=json.loads(file.read_bytes());proc=Path('/proc',str(record['pid']));actual=identity(record['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==record[k]for k in ['uid','command','start_ticks'])
 assert not same,'Model process still live; no post-stop admission'
 out['processes'][label]={'saved':record,'actual_if_PID_exists':actual,'same_live_process':False}
assert json.loads((r/'primary/terminal.json').read_bytes())['attempted_actor_calls']==397
for n,h in OLD_MAIN.items():assert sha(r/'primary/requests'/n/'seal.json')==h
for n,h in OLD_FLASH.items():assert sha(p/'flash/service/requests'/n/'seal.json')==h
for label,path in [('main',r/'primary/journal/events.jsonl'),('Flash',p/'flash/service/journal/events.jsonl')]:
 proof,events=chain(path);assert not proof['ignored_partial_last_line'];n=PREFIX[label]['verified_prefix_events']
 assert len(events)>=n and hashlib.sha256(canonical(events[n-1])).hexdigest()==PREFIX[label]['head']
 out[label+'_chain']=proof
FLASH_NAMES=[d.name for d in sorted((p/'flash/service/requests').iterdir())if d.name not in OLD_FLASH and(d/'seal.json').exists()]
d=Path(BOUNDARY['folder']);seal=json.loads((d/'seal.json').read_bytes());assert sha(d/'seal.json')==BOUNDARY['seal_sha256']
for n in ['wire-request.bin','body.json','response.json']:assert sha(d/n)==seal[n]
w=json.loads((d/'wire-request.bin').read_bytes());a=json.loads((d/'response.json').read_bytes());history[w['run_id']]=w['body']['messages']+[{'role':'assistant','content':a['text']}]
''' + success + flash + r'''
d=r/'primary/requests/00397';seal=json.loads((d/'seal.json').read_bytes())
assert all(sha(d/n)==h for n,h in seal.items())
assert not(d/'response.json').exists()and(d/'failure.json').exists()and not(d/'admission-after.json').exists()
wire=json.loads((d/'wire-request.bin').read_bytes());body=json.loads((d/'body.json').read_bytes());actual=json.loads((d/'actual-generation.json').read_bytes());native=json.loads((d/'native-call.json').read_bytes());prepared=json.loads((d/'prepared.json').read_bytes());first=json.loads((d/'first-forward.json').read_bytes());failure=json.loads((d/'failure.json').read_bytes())
assert body==wire['body']and wire['decision_index']==28 and wire['run_id']=='flash14-T089-stale_replace-gate'
assert body['messages'][:len(history[wire['run_id']])]==history[wire['run_id']]
template=json.loads((p/'actor-template.json').read_bytes());assert body['messages'][0]==template['messages'][0]
assert{k:v for k,v in body.items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'}
assert native['generated_ids']==actual['output_ids']and actual['natural_EOS']and actual['output_tokens']==32 and actual['input_tokens']==28120
assert native['request_messages_sha256']==hashlib.sha256(canonical(body['messages'])).hexdigest()
for k in prepared:
 assert all(prepared[k][f]==first[k][f]for f in ['shape','dtype','bytes','sha256'])
 assert sha(d/prepared[k]['file'])==prepared[k]['sha256']and sha(d/first[k]['file'])==first[k]['sha256']
assert 'Foreign/unverified compute on GPU 3: {2190562, 2040397}'in failure['error']and failure['not_semantic_NO']and failure['no_automatic_retry']
png=base64.b64decode(body['messages'][-1]['content'][-1]['image_url']['url'].split(',',1)[1],validate=True)
out['failed_requests'].append({'folder':str(d),'request_id':wire['request_id'],'run_id':wire['run_id'],'decision':28,'wire_sha256':sha(d/'wire-request.bin'),'body_sha256':hashlib.sha256(canonical(body)).hexdigest(),'seal_sha256':sha(d/'seal.json'),'current_image_sha256':hashlib.sha256(png).hexdigest(),'input_tokens':28120,'output_tokens':32,'natural_EOS':True,'full_raw_input_first_forward_and_sequence_files_verified':True,'public_success_response_exists':False,'action_execution_permitted':False,'failure':failure})
assert len(out['sealed_main_requests'])==2 and len(out['sealed_Flash_requests'])==2
out['parent_postexit_seal_present_at_read']=(r/'postexit-seal.json').exists()
print(json.dumps(out))
''')
    compile(code, '<stopped-tail-audit>', 'exec')
    dest = HERE / ('stopped-tail-evidence-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'inspector-source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'remote-source.py').write_text(code, encoding='utf8')
    raw, op = remote('3090', code, 'post-stop-new-tail-and-undelivered-resource-failure', timeout=55)
    additions = json.loads(raw)
    save(dest / '3090-new-tail.json', {'result': additions, 'operation': str(op)})
    mains = previous['sealed_main_requests'] + additions['sealed_main_requests']
    flashes = previous['sealed_Flash_requests'] + additions['sealed_Flash_requests']
    assert len(mains) == 396 and len(flashes) == 199
    save(dest / '3090.json', {**additions, 'sealed_main_requests': mains, 'sealed_Flash_requests': flashes,
        'cumulative_verification_is_linked_not_fresh_full_rehash': True})
    original_gui = next(v for v in constants if v.startswith("\nr=Path(ROOT);out={'time':time.time(),'UID':os.getuid(),'new_GUI_actions_by_inspector':0"))
    gui_loop = original_gui[original_gui.index("for events in(r/'batch/runs')"):original_gui.index('shots=')]
    code = 'ROOT=' + repr(R4090) + '\n' + COMMON + r'''
r=Path(ROOT);out={'time':time.time(),'processes':{},'controllers':[],'new_GUI_actions_by_inspector':0}
for name in ['control/process.json','control/runner-process.json']:
 record=json.loads((r/name).read_bytes());proc=Path('/proc',str(record['pid']));actual=identity(record['pid'])if proc.exists()else None
 same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==record[k]for k in ['uid','command','start_ticks'])
 assert not same;out['processes'][name]={'saved':record,'actual_if_PID_exists':actual,'same_live_process':False}
''' + gui_loop + '\nprint(json.dumps(out))\n'
    raw, op = remote('4090', code, 'post-stop-controller-chains-and-actual-GUI-exits')
    gui = json.loads(raw)
    save(dest / '4090.json', gui)
    save(dest / '4090-operation.json', {'operation': str(op)})
    by_id = {v['request_id']: v for v in mains}
    flash_by_id = {v['request_id']: v for v in flashes}
    failed = additions['failed_requests'][0]
    failed_bound = False
    main_bound = flash_bound = 0
    for controller in gui['controllers']:
        returned = {v['request_id'] for v in controller['actor_replies']}
        actions = {v['step'] for v in controller['environment_actions']}
        for number, (frame, request) in enumerate(zip(controller['forwarded_images'], controller['actor_requests']), 1):
            gate = frame['gate_request_id']
            if gate:
                f = flash_by_id[gate]
                assert f['decision'] == 'YES' and f['image_sha256'] == frame['image_sha256']
                flash_bound += 1
            actual = by_id.get(request['request_id'])
            if actual:
                assert actual['body_sha256'] == request['body_sha256'] and actual['current_image_sha256'] == frame['image_sha256']
                assert request['request_id'] in returned
                main_bound += 1
            else:
                assert request['request_id'] == failed['request_id'] and number == 28
                assert failed['body_sha256'] == request['body_sha256'] and failed['current_image_sha256'] == frame['image_sha256']
                assert request['request_id'] not in returned and number not in actions
                failed_bound = True
    assert failed_bound and main_bound == 396 and flash_bound == 199
    summary = {'time': time.time(), 'previous_audit': str(prior), 'previous_seal_sha256': sha(prior / 'seal.json'),
        'new_complete_main_raw_replies_verified': 2, 'new_Flash_raw_replies_verified': 2,
        'cumulative_verified_delivered_main_replies': 396, 'cumulative_verified_Flash_replies': 199,
        'failed_native_generations_verified_separately': 1, 'failed_generation_not_promoted_to_public_success': True,
        'old_raw_check_times_retained_not_freshly_rehashed': True,
        'model_and_GUI_process_exits_verified': True,
        'launcher_full_postexit_audit_complete': False,
        'fresh_full_postexit_rehash_still_required': True,
        'main_chain': additions['main_chain'], 'Flash_chain': additions['Flash_chain'],
        'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'goal': 'active'}
    save(dest / 'summary.json', summary)
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'evidence': str(dest), **summary}))


if __name__ == '__main__':
    main()
