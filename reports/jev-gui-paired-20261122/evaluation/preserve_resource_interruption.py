"""Read the failed inference and GPU sample from their original post-exit seals."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from collect import HERE, control, manifest_for, read, save, sha
from link import verify


STAGE = 'NF4-resume-01'
RUN = 'paperpair-T058-silent_drop-on'

MODEL = r'''
import os
os.nice(15)
p = Path(ROOT)
out = Path(OUT)
assert os.getuid() == 1033 and sha(p/'manifest.json') == EXPECTED
post = read(out/'postexit-seal.json')
assert sha(out/'postexit-seal.json') == RELEASE['postexit_sha256']
events, head = journal(sealed(out, post, 'primary/journal/events.jsonl'))
assert head == RELEASE['primary_chain_head']
event = unique(data(events, 'actor_request'), lambda a: a['request_id'])[REQUEST_ID]
assert event['run_id'] == RUN and event['decision'] == STEP and event['wire_sha256'] == MAIN['wire_sha256']
assert REQUEST_ID not in {a['request_id'] for a in data(events, 'actor_reply_sealed')}
assert RUN not in {a['run_id'] for a in data(events, 'run_end')}
folder = Path(MAIN['runtime_request_directory'])
assert str(folder) == event['folder'] and folder.is_relative_to(out/'primary/requests')
seal_file = sealed(out, post, (folder/'seal.json').relative_to(out).as_posix())
assert sha(seal_file) == MAIN['seal_sha256']
seal = read(seal_file)
assert not (folder/'response.json').exists() and 'response.json' not in seal
assert all(post[(folder/name).relative_to(out).as_posix()] == digest for name, digest in seal.items())
wire_file = sealed(folder, seal, 'wire-request.bin')
wire = read(wire_file)
assert sha(wire_file) == MAIN['wire_sha256'] and wire['request_id'] == REQUEST_ID
assert wire['body'] == read(sealed(folder, seal, 'body.json'))
error_file = sealed(folder, seal, 'failure.json')
error = read(error_file)
assert error['no_automatic_retry'] and error['not_semantic_NO'] and sha(error_file) == MAIN['failure_sha256']
assert 'RuntimeError: Unverified compute on reserved GPU 3' in error['error']
assert 'admission-after.json' in error['error']
conflict, = (out/'primary/resource-conflicts').glob('*.json')
sealed(out, post, conflict.relative_to(out).as_posix())
record = read(conflict)
assert record['not_model_NO']
snap = record['snapshot']
expected = record['expected']
card = snap['gpu']['3']
on_card = [a for a in snap['compute'] if a['uuid'] == card['uuid']]
flash, = (a for a in on_card if a['pid'] == expected['3'])
foreign = [a for a in on_card if a['pid'] != expected['3']]
assert flash['identity']['uid'] == 1033 and foreign
assert all(a['identity'] and a['identity']['uid'] != 1033 for a in foreign)
assert float(conflict.stem)/1e9 <= error['time'] <= float(conflict.stem)/1e9 + 5
first = read(sealed(folder, seal, 'first-forward.json'))
prep = read(sealed(folder, seal, 'prepared.json'))
assert first.keys() == prep.keys()
for key, tensor in first.items():
    assert all(tensor[k] == prep[key][k] for k in ('shape','dtype','bytes','sha256'))
    checked_tensor(folder, seal, tensor, full_hash=True)
generation = read(sealed(folder, seal, 'actual-generation.json'))
assert generation['natural_EOS'] and generation['actual_forward_calls'] == MAIN['forward_calls']
print(json.dumps({'UID': os.getuid(), 'journal_head': head, 'request_seal_sha256': sha(seal_file),
    'wire_sha256': sha(wire_file), 'first_forward_sha256': seal['first-forward.json'],
    'forward_raw_bytes_rehashed': sum(v['bytes'] for v in first.values()),
    'internal_generation': {k:generation[k] for k in ('input_tokens','output_tokens','natural_EOS','actual_forward_calls')},
    'generation_sha256': seal['actual-generation.json'], 'failure_sha256': sha(error_file),
    'resource_conflict_file': str(conflict), 'resource_conflict_sha256': sha(conflict),
    'selected_gpu': 3, 'GPU_UUID': card['uuid'], 'foreign_compute': foreign, 'own_Flash_compute': flash,
    'published_main_reply': False, 'run_end_notification': False, 'new_model_GUI_scorer_calls': 0}))
'''

GUI = r'''
import os
p = Path(ROOT)
assert os.getuid() == 1015 and sha(p/'manifest.json') == EXPECTED
post = read(p/'control/postexit-seal.json')
assert sha(p/'control/postexit-seal.json') == RELEASE['postexit_sha256']
idx = read(sealed(p/'control', post, 'batch-terminal-seal.json'))
batch = p/'batch'
attempt = Path(ATTEMPT)
def bound(name):
    return sealed(batch, idx, (attempt/name).relative_to(batch).as_posix())
sealed(batch, idx, (attempt/'seal.json').relative_to(batch).as_posix())
local = read(attempt/'seal.json')
terminal = bound('terminal.json')
assert sha(terminal) == local['terminal.json'] == TERMINAL and read(terminal)['official_reward'] is None
events, head = journal(bound('controller/events.jsonl'))
assert head == CONTROLLER_HEAD
seen = unique(data(events, 'actual_actor_request'), lambda x: x['request_id'])
assert seen[REQUEST_ID]['body_sha256'] == MAIN['body_sha256']
assert REQUEST_ID not in {x['request_id'] for x in data(events, 'actual_actor_reply')}
actions = data(events, 'native_environment_action')
assert len(actions) == read(terminal)['environment_actions'] == STEP - 1
for key in ('raw_file', 'delivered_file'):
    assert sha(bound(FRAME[key])) == local[FRAME[key]] == FRAME['captured_sha256'] == FRAME['delivered_sha256']
print(json.dumps({'UID': os.getuid(), 'controller_head': head, 'terminal_sha256': sha(terminal),
    'original_PNG_sha256': FRAME['captured_sha256'], 'original_PNG_path': str(attempt/FRAME['raw_file']),
    'delivered_actor_reply': False, 'failed_decision_executed': False, 'native_actions_before_failure': len(actions),
    'official_score': None, 'new_model_GUI_scorer_calls': 0}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('release_audit', type=Path)
    args = parser.parse_args()
    verify(args.ledger)
    verify(args.release_audit)
    ledger = read(args.ledger/'private-linked.json')
    release = read(args.release_audit/'index.json')
    assert release['ledger_seal_sha256'] == sha(args.ledger/'seal.json') and release['stage'] == STAGE
    assert release['phase'] == 'technical_failure' and release['cutoff_in_original_100'] == 61
    row = ledger['rows'][60]
    t = row['evidence']
    assert row['slot']['run_id'] == RUN and row['stage_id'] == STAGE
    assert t['terminal']['infrastructure_failure'] and not t['model_run_end_bound']
    step = t['steps'][-1]
    assert step['step'] == 39 and step['actual_first_forward'] and not step['reply'] and not step['executed']
    frame, = step['frames']
    ptr, manifest, _ = manifest_for(STAGE)
    out = HERE/'failure-evidence'/('T058-resource-interruption-' + str(time.time_ns()))
    out.mkdir(exist_ok=False)
    control.ROOT = out
    core = (HERE/'extract_on_host.py').read_text(encoding='utf-8')

    def probe(host):
        result = release['hosts'][host]
        op = Path(result['operation'])
        verify(op)
        assert sha(op/'seal.json') == result['operation_seal'] and read(op/'stdout.bin') == result['result']
        params = {'ROOT':manifest['package'+host], 'OUT':manifest['output3090'], 'EXPECTED':ptr['manifest_sha256'],
            'RELEASE':result['result'], 'MAIN':step['main'], 'STEP':step['step'], 'REQUEST_ID':step['request']['request_id'],
            'RUN':RUN, 'FRAME':frame, 'ATTEMPT':t['gui_attempt'], 'TERMINAL':t['terminal_sha256'],
            'CONTROLLER_HEAD':t['controller_head']}
        source = "__name__='evidence_library'\n" + ''.join(f'{k}={v!r}\n' for k,v in params.items())
        source += core + (MODEL if host == '3090' else GUI)
        compile(source, host, 'exec')
        receipt = control.remote(host, source, 'preserve-T058-resource-interruption', timeout=120)
        op = Path(receipt['operation'])
        verify(op)
        return {**receipt, 'operation_seal_sha256': sha(op/'seal.json')}

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = dict(zip(('3090','4090'), pool.map(probe, ('3090','4090'))))
    result = {'ledger_seal_sha256':sha(args.ledger/'seal.json'), 'release_audit_sha256':sha(args.release_audit/'seal.json'),
        'run':RUN, 'terminal_sha256':t['terminal_sha256'], 'request_id':step['request']['request_id'],
        'native_actor_or_parser_failure_is_generic_wrapper_reason':True,
        'operational_cause':'Foreign compute on Flash GPU discovered by the main request post-generation guard.',
        'no_original_retry':True, 'unstarted_frozen_ids':release['verified_never_started_in_stage'], 'hosts':receipts}
    save(out/'index.json',result)
    save(out/'seal.json',{'index.json':sha(out/'index.json')})
    print(json.dumps({'preservation':str(out),'seal_sha256':sha(out/'seal.json'),
        'never_started':len(result['unstarted_frozen_ids']), 'model':receipts['3090']['result']}))


if __name__ == '__main__':
    main()
