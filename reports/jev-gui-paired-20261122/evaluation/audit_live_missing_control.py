"""Bind a live missing-image or in-transit stale control to the actual model forward."""

import argparse
import json
from pathlib import Path
import time

from collect import HERE, control, manifest_for, read, save, sha
from extract_on_host import canonical, hx
from link import verify


STAGE = 'NF4-resume-01'
GUI = r'''
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
p = Path(ROOT)
assert os.getuid() == 1015 and sha(p/'manifest.json') == EXPECTED
attempt, = (p/'batch/runs'/RUN).glob('attempt-*')
controller, ch = journal(attempt/'controller/events.jsonl', live=True)
source, sh = journal(attempt/'trusted-source/events.jsonl', live=True, source=True)
binding = read(attempt/'trusted-source/ready.json')
key = bytes.fromhex(binding['public_key'])
assert hx(key) == binding['key_id'] and not binding['fixture']
assert binding['identity']['uid'] == 1015 and sha(p/'capture_source.py') == binding['source_code_sha256']
pub = Ed25519PublicKey.from_public_bytes(key)
frames = data(controller, 'PRIVATE_capture_injection')
changed, = [f for f in frames if f['injected']]
n = changed['step']
assert n > 1 and changed['capture_kind'] == 'initial' and changed['condition'] == CONDITION
previous, = [f for f in frames if f['step'] == n-1]
if CONDITION == 'silent_drop':
    assert changed['delivered_file'] is None and changed['delivered_sha256'] is None
else:
    assert CONDITION == 'stale_replace'
    assert changed['delivered_file'] and changed['delivered_sha256'] == previous['captured_sha256']
    assert previous['captured_sha256'] == previous['delivered_sha256'] != changed['captured_sha256']
signed = unique(data(source, 'actual_native_capture_signed'), lambda x: x['receipt']['capture_id'])
submit = unique(data(controller, 'actor_submit_timing'), lambda r: r['step'])
action = unique(data(controller, 'native_environment_action'), lambda r: r['step'])
replies = unique(data(controller, 'actual_actor_reply'), lambda r: r['request_id'])
groups = defaultdict(list)
step = None
for event in controller:
    if event['kind'] == 'observation_started_timing':
        step = event['data']['step']
    groups[step].append(event)
steps = {}
for step in (n-1, n, n+1):
    if step not in submit:
        continue
    f, = [x for x in frames if x['step'] == step]
    assert f['capture_kind'] == 'initial' and submit[step]['capture_id'] == f['capture_id']
    trusted = signed[f['capture_id']]
    receipt = trusted['receipt']
    stem = attempt/'capture-deliveries'/f'{f["capture_index"]:04d}'
    assert read(Path(str(stem)+'-signed-receipt.json')) == receipt
    expected = read(Path(str(stem)+'-expected-challenge.json'))
    assert all(receipt[k] == expected[k] for k in ('challenge','environment_id','action_sequence'))
    pub.verify(bytes.fromhex(receipt['signature']), canonical({k:v for k,v in receipt.items() if k!='signature'}))
    assert sha(attempt/f['raw_file']) == sha(Path(trusted['original_file'])) == receipt['image_sha256'] == f['captured_sha256']
    assert all(receipt[k] == binding[k] for k in ('session_id','environment_id','source_code_sha256'))
    if f['delivered_file'] is not None:
        assert sha(attempt/f['delivered_file']) == f['delivered_sha256']
        if step != n:
            assert f['delivered_sha256'] == receipt['image_sha256']
        else:
            assert CONDITION == 'stale_replace' and f['delivered_sha256'] != receipt['image_sha256']
    assert submit[step]['image_sha256'] == f['delivered_sha256']
    blockers = {'precheck_decision','capture_receipt_decision','gate_decision','recapture_requested'}
    assert not blockers & {r['kind'] for r in groups[step]}
    req, = data(groups[step], 'actual_actor_request')
    res = replies[req['request_id']]
    steps[step] = {'request_id': req['request_id'], 'body_sha256': req['body_sha256'],
                   'reply_sha256': res['text_sha256'], 'signed_original_sha256': f['captured_sha256'],
                   'delivered_sha256': f['delivered_sha256'], 'capture_id': f['capture_id'],
                   'signed_action_sequence': receipt['action_sequence'], 'signed_challenge': receipt['challenge'],
                   'ack': [action[step]['payload'], action[step]['ok']] if step in action else None}
before, injected = steps[n-1], steps[n]
assert before['signed_action_sequence']+1 == injected['signed_action_sequence']
assert before['signed_challenge'] != injected['signed_challenge']
assert before['ack'] and before['ack'][1]
print(json.dumps({'injection_decision': n, 'steps': steps, 'controller_head': ch, 'capture_head': sh,
    **({'missing_decision': n} if CONDITION == 'silent_drop' else {})}))
'''


MAIN = r'''
import os
p = Path(ROOT)
assert os.getuid() == 1033 and sha(p/'manifest.json') == EXPECTED
primary = Path(OUTPUT)/'primary'
events, head = journal(primary/'journal/events.jsonl', live=True)
aux, ah = journal(p/'flash/service/journal/events.jsonl', live=True)
assert not [r for r in data(events,'Flash_reply_forwarded') if r['run_id'] == RUN]
received = unique(data(events, 'actor_request'), lambda x: x['request_id'])
sealed_replies = unique(data(events, 'actor_reply_sealed'), lambda x: x['request_id'])
template = read(p/'actor-template.json')
previous_body = previous_reply = None
steps = {}
for key, source in sorted(GUI_STEPS.items(), key=lambda x:int(x[0])):
    n = int(key)
    rid = source['request_id']
    record = sealed_replies[rid]
    q = Path(record['folder'])
    seal = read(q/'seal.json')
    assert sha(q/'seal.json') == record['seal_sha256']
    wire = read(sealed(q,seal,'wire-request.bin'))
    assert (wire['run_id'],wire['decision_index'],wire['request_id']) == (RUN,n,rid)
    assert received[rid]['wire_sha256'] == seal['wire-request.bin']
    body = wire['body']; assert body == read(sealed(q,seal,'body.json'))
    assert {k:v for k,v in body.items() if k!='messages'} == {k:v for k,v in template.items() if k!='messages'}
    assert body['messages'][0] == template['messages'][0] and len(body['messages']) == 2*n
    if previous_body is not None:
        assert body['messages'][:-1] == previous_body + [{'role':'assistant','content':previous_reply}]
    table = {}; ordered = project_messages(body['messages'],table)
    current = table[ordered[-1]]
    img = [x['sha256'] for x in current['content'] if x['type']=='image']
    img = img[0] if img else None
    assert source['delivered_sha256'] == img and hx(canonical(body)) == source['body_sha256']
    first = read(sealed(q,seal,'first-forward.json')); prepared = read(sealed(q,seal,'prepared.json'))
    assert first.keys() == prepared.keys()
    for kind in first:
        assert all(first[kind][k] == prepared[kind][k] for k in ('sha256','shape','dtype','bytes'))
        checked_tensor(q,seal,first[kind],full_hash=n==INJECTED)
    assert sum(x['type']=='image' for k in ordered for x in (table[k]['content'] if isinstance(table[k]['content'],list) else [])) == first['image_grid_thw']['shape'][0]
    res = read(sealed(q,seal,'response.json')); g = read(sealed(q,seal,'actual-generation.json'))
    native = read(sealed(q,seal,'native-call.json')); cfg = read(sealed(q,seal,'effective-generation.json'))
    assert res['request_sha256'] == seal['wire-request.bin'] and res['request_id'] == rid
    assert hx(res['text'].encode()) == source['reply_sha256'] and res['text'] == native['text']
    ids = native['input_ids']; assert hx(struct.pack('<'+'q'*len(ids),*ids)) == first['input_ids']['sha256']
    eos = cfg['eos_token_id']; eos = [eos] if isinstance(eos,int) else eos
    assert g['natural_EOS'] and g['actual_forward_calls'] >= 1 and cfg['max_new_tokens'] == 2048
    assert g['output_ids'] == native['generated_ids'] and g['output_ids'][-1] in eos
    steps[n] = {'request_id': rid, 'seal_sha256': sha(q/'seal.json'), 'messages_ordered': ordered,
                'current_user_projected': current, 'actual_first_forward_images': first['image_grid_thw']['shape'][0],
                'actual_current_png_sha256': img, 'tensor_bytes_rehashed': n==INJECTED,
                'actual_forward_calls': g['actual_forward_calls'], 'native_EOS': True}
    previous_body, previous_reply = body['messages'],res['text']
image = steps[INJECTED]['actual_current_png_sha256']
assert image == GUI_STEPS[str(INJECTED)]['delivered_sha256']
assert ((CONDITION=='silent_drop' and image is None) or
        (CONDITION=='stale_replace' and image == steps[INJECTED-1]['actual_current_png_sha256']))
print(json.dumps({'steps':steps,'primary_head':head,'Flash_head':ah,'Flash_calls_for_this_arm':0}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('reviewed_ledger', type=Path)
    a = parser.parse_args()
    verify(a.reviewed_ledger)
    ledger = read(a.reviewed_ledger/'private-linked.json')
    ptr, manifest, slots = manifest_for(STAGE)
    slot, = [x for x in slots if x['run_id'] == a.run]
    condition = slot['condition']
    assert condition in {'silent_drop','stale_replace'} and slot['arm'] == 'off'
    clean, = [x for x in ledger['rows'] if x['slot']['task_id']==slot['task_id'] and x['slot']['arm']=='off'
              and x['slot']['condition']=='clean_control']
    assert clean['evidence'] and clean['version'] == 'NF4'
    known = {str(s['step']):s for s in clean['evidence']['steps']}
    out = HERE/'live-observation-evidence'/str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    control.ROOT = out
    lib = (HERE/'extract_on_host.py').read_text(encoding='utf-8')

    def run(host, tail, extra=None):
        prefix = {'ROOT':manifest['package'+host], 'OUTPUT':manifest['output3090'],
                  'RUN':a.run, 'EXPECTED':ptr['manifest_sha256'], 'CONDITION':condition, **(extra or {})}
        code = "__name__='read_only_library'\n" + ''.join(f'{k}={v!r}\n' for k,v in prefix.items()) + lib + tail
        result = control.remote(host,code,'bind-existing-altered-image-control',timeout=45)
        path = Path(result['operation']); verify(path)
        return {**result,'operation_seal_sha256':sha(path/'seal.json')}

    gui = run('4090', GUI)
    previous_step, injection_step, following = (str(gui['result']['injection_decision']+d) for d in (-1,0,1))
    model = run('3090', MAIN, {'INJECTED':int(injection_step),'GUI_STEPS':gui['result']['steps']})
    gs = gui['result']['steps']; ms = model['result']['steps']
    first = known[previous_step]; second = known[injection_step]
    ack = [first['executed']['payload'], first['executed']['ok']] if first['executed'] else None
    current = ledger['public_legal_messages'][second['main']['messages_ordered'][-1]]
    received_png = ms[injection_step]['actual_current_png_sha256']
    altered = {**current,'content':[x if x['type']!='image' else {**x,'sha256':received_png}
        for x in current['content'] if x['type']!='image' or received_png is not None]}
    only_current = ms[injection_step]['messages_ordered'] == second['main']['messages_ordered'][:-1]+[hx(canonical(altered))]
    terms = {'previous_main_and_native_ack_match_clean': gs[previous_step]['ack'] == ack and
             gs[previous_step]['body_sha256'] == first['main']['body_sha256'] and
             gs[previous_step]['reply_sha256'] == first['main']['reply_sha256'],
             'signed_original_at_injected_decision_matches_clean': gs[injection_step]['signed_original_sha256'] == second['main']['current_image_sha256'],
             'entire_actual_message_history_matches_clean_except_current_image_block':only_current,
             'next_actual_frame_matches_clean_original_at_injected_decision':
                 (ms[following]['actual_current_png_sha256'] == second['main']['current_image_sha256']) if following in ms else None}
    if condition == 'stale_replace':
        terms['injected_pixels_equal_previous_but_not_this_action_signed_original'] = (
            received_png == gs[previous_step]['signed_original_sha256'] != gs[injection_step]['signed_original_sha256'])
        assert terms['injected_pixels_equal_previous_but_not_this_action_signed_original']
    save(out/'evidence.json', {'run':a.run,'version':'NF4','condition':condition,'GUI':gui,'main':model,'comparisons':terms,
        'clean_reference_terminal_sha256':clean['evidence']['terminal_sha256'],
        'reviewed_ledger_seal_sha256':sha(a.reviewed_ledger/'seal.json'),
        'observation_evidence_only_no_score_or_semantic_labels':True,'new_GPU_model_GUI_or_scorer_calls':0})
    save(out/'seal.json',{'evidence.json':sha(out/'evidence.json')})
    print(json.dumps({'audit':str(out),'seal_sha256':sha(out/'seal.json'),'injection_decision':int(injection_step),
                      'actual_current_png':received_png,'actual_action_ack':gs[injection_step]['ack'],
                      'images_in_full_model_input':ms[injection_step]['actual_first_forward_images'],**terms}))


if __name__ == '__main__':
    main()
