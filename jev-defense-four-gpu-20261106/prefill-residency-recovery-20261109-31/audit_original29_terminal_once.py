"""Audit sealed NEW29 failure and every completed request without rerunning it."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'memory-scheduled-full-history-gui-20261109-29'
PRES = OLD / 'failure-preservation-1794228241952080200'
sha = lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p:json.loads(Path(p).read_bytes())
canonical = lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def save(p, v):
    with p.open('x', encoding='utf8') as stream:
        json.dump(v,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def chain(p):
    raw = p.read_bytes()
    assert raw.endswith(b'\n')
    rows, previous, counts = [], '0'*64, {}
    for line in raw.splitlines():
        row = json.loads(line)
        signature = row.pop('sha256')
        assert row['seq'] == len(rows) and row['previous'] == previous
        assert hashlib.sha256(canonical(row)).hexdigest() == signature
        previous = signature
        counts[row['kind']] = counts.get(row['kind'],0)+1
        rows.append(dict(row,sha256=signature))
    return {'events':len(rows),'head':previous,'counts':counts},rows


def main():
    assert not (HERE / 'original29-terminal-audit-created.json').exists()
    assert sha(PRES / 'receipt.json') == '6b6881fb9c650dd9d689438d4534d8698c347b09158c1619166817e3841409a8'
    preservation = read(PRES / 'receipt.json')
    roots, inventories = {}, {}
    for host, info in preservation['hosts'].items():
        assert sha(info['receipt']) == info['receipt_sha256']
        receipt = read(info['receipt'])
        root = Path(receipt['local_public_originals'])
        for name, expected in receipt['public_exported_files'].items():
            assert sha(root / name) == expected, (host,name)
        roots[host], inventories[host] = root/'output', receipt['all_original_files']
        terminal = root / 'output/terminal-manifest.json'
        if terminal.is_file():
            for name, expected in read(terminal).items():
                assert receipt['all_original_files'][name] == expected, (host,name)
    service, gui = roots['3090'], roots['4090']
    attempt = gui / 'batch/runs/fullhistory23-T000-clean-noaux/attempt-1794227118456197872'
    sc, service_events = chain(service/'worker/journal/events.jsonl')
    gc, events = chain(attempt/'events.jsonl')
    assert sc['events'] == 96 and gc['events'] == 278
    assert sc['head'] == 'a53ca3d3391a8de8488925bd1ec754b45457a04c63b1d65840176d8c44243097'
    assert gc['head'] == '739c4846b972ef61bff8b2ede33ca2518a8d80ed5de1b64618a3e164acdb7594'
    wires = {e['data']['wire_sha256']:e['data']['body'] for e in events
             if e['kind'] in ['actual_actor_wire_request','actual_judge_wire_request']}
    assert len(wires) == 21
    totals = {'actor':0,'judge':0,'auxiliary':0,'natural_EOS':0,'prefill_OOM':0,
              'successful_input_tokens':0,'successful_output_tokens':0,
              'successful_native_generation_seconds':0.0,'successful_instrumented_seconds':0.0}
    requests = []
    for folder in sorted((service/'worker/requests').iterdir()):
        bindings = read(folder/'seal.json')
        for name, expected in bindings.items():
            assert inventories['3090'][(folder/name).relative_to(service).as_posix()] == expected
        wire, payload = read(folder/'external-wire.json'), read(folder/'payload.json')
        assert wires[sha(folder/'external-wire.json')] == wire and wire['payload'] == payload
        op = payload['operation']
        totals[op] += 1
        prepared, first = read(folder/'prepared.json'), read(folder/'first-forward.json')
        assert prepared.keys() == first.keys()
        for key in prepared:
            assert all(prepared[key][k] == first[key][k] for k in ['shape','dtype','bytes','sha256'])
            for source in [prepared,first]:
                assert bindings[source[key]['file']] == source[key]['sha256']
        row = {'request':folder.name,'operation':op,'decision_index':wire['decision_index'],
               'input_tokens':prepared['input_ids']['shape'][1],
               'complete_images':prepared['image_grid_thw']['shape'][0],
               'seal_sha256':sha(folder/'seal.json'),'all_CPU_and_first_forward_tensor_SHA_equal':True}
        if (folder/'actual-generation.json').is_file():
            generated, native, response = read(folder/'actual-generation.json'),read(folder/'native-call.json'),read(folder/'response.json')
            assert response['request_id'] == wire['request_id']
            assert response['external_wire_sha256'] == sha(folder/'external-wire.json')
            assert response['text' if op=='actor' else 'verdict'] == native['text']
            assert native['generated_ids'] == generated['output_ids']
            assert len(native['input_ids']) == generated['input_tokens'] == row['input_tokens']
            assert generated['natural_EOS'] and not native['hit_output_cap']
            assert generated['output_ids'][-1] in read(folder/'effective-generation.json')['eos_token_id']
            totals['natural_EOS'] += 1
            totals['successful_input_tokens'] += generated['input_tokens']
            totals['successful_output_tokens'] += generated['output_tokens']
            totals['successful_native_generation_seconds'] += native['seconds']
            totals['successful_instrumented_seconds'] += response['seconds_including_instrumentation']
            row.update(natural_EOS=True,output_tokens=generated['output_tokens'])
        else:
            assert folder.name == '0021' and row['input_tokens'] == 32184 and row['complete_images'] == 17
            assert (folder/'generated-token-progress.jsonl').stat().st_size == 0
            assert read(folder/'forward-count.json')['actual_forward_calls'] == 1
            assert 'OutOfMemoryError' in read(folder/'failure.json')['traceback']
            totals['prefill_OOM'] += 1
            row.update(generated_tokens=0,natural_EOS=None,technical_outcome='prefill_OOM')
        requests.append(row)
    assert totals['actor']==6 and totals['judge']==15 and totals['auxiliary']==0
    assert totals['natural_EOS']==20 and totals['prefill_OOM']==1
    reviews, labels = [], []
    for index in range(1,5):
        pointer = read(OLD/('source-review-%02d-created.json'%index))
        directory = Path(pointer['review'])
        assert sha(directory/'review.json') == pointer['review_sha256']
        for name, expected in read(directory/'seal.json').items():
            assert sha(directory/name) == expected
        reviews.append(pointer)
        labels.extend(read(directory/'review.json')['rows'])
    assert len(labels)==6 and len({r['candidate_event_sha256'] for r in labels})==6
    assert {r['candidate_event_sha256'] for r in labels} == {e['sha256'] for e in events if e['kind']=='candidate'}
    assert all(r['semantic_assertion_count']==0 for r in labels)
    terminal = read(attempt/'technical-failure.json')
    assert terminal['actor_calls']==17 and terminal['verifier_calls']==49
    assert terminal['environment_actions']==16 and terminal['decisions']==17
    assert terminal['official_reward']==0 and terminal['scoring_status']=='complete'
    assert terminal['semantic_mirage'] is None
    assert read(service/'exit.json')['worker_exit_code']==1
    assert read(gui/'control/exit.json')['child_exit']==1
    result = {'schema':'new29-all-requests-technical-terminal-source-coverage-audit-v1','time':time.time(),
        'passed':True,'preservation_receipt_sha256':sha(PRES/'receipt.json'),
        'all499service_and175GUI_original_files_SHA_bound':True,
        'public_exports_verified':{h:len(read(i['receipt'])['public_exported_files']) for h,i in preservation['hosts'].items()},
        'service_chain':sc,'GUI_chain':gc,'requests':requests,'totals':totals,
        'original_trajectory_budget_spent':{'actor':17,'judge':49,'auxiliary':0,'actions':16},
        'original_caps':{'actor':70,'judge':140,'auxiliary':60,'steps':50},
        'original11candidate_reviews_retained_without_double_counting':True,
        'new29candidate_reviews':reviews,'new_candidates_reviewed':6,'new_unreviewed':0,
        'definite_semantic_Mirage_in_reviewed_new_candidates':0,
        'new_candidates_action_only_no_fact_assertions':True,
        'logical_trajectory_Mirage':None,'completed_trajectories':0,'technical_incomplete_trajectories':1,
        'unstarted_original_tracks':31,'official_score':0,'official_scorer_calls_in_new29':1,
        'score0_is_technical_not_semantic_model_zero':True,'four_GPU_reserved_seconds_inside_new29_launcher':read(service/'exit.json')['four_GPU_reserved_seconds_in_launcher'],
        'cost_exclusions':'Summed successful calls exclude failed work/loading/holder reservation outside launcher; no walltime/currency/energy or benefit claim.',
        'no_old_completed_calls_actions_or_controls_reexecuted':True,
        'new_model_GUI_scorer_paid_calls_from_this_audit':0,'efficacy_established':False,'goal':'active'}
    target = HERE / ('original29-terminal-audit-'+str(time.time_ns()))
    target.mkdir()
    save(target/'audit.json',result)
    save(target/'seal.json',{'audit.json':sha(target/'audit.json')})
    pointer = {'root':str(target),'audit_sha256':sha(target/'audit.json'),'seal_sha256':sha(target/'seal.json')}
    save(HERE/'original29-terminal-audit-created.json',pointer)
    print(json.dumps({'audit':pointer,'totals':totals,'trajectory_Mirage':None,'unstarted':31},ensure_ascii=False))


if __name__ == '__main__':
    main()
