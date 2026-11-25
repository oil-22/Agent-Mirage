"""Bind the complete planned matrix and shared protocol to the actual loaded stages."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

from collect import HERE, control, manifest_for, measurement_version, read, save, sha, stages
from extract_on_host import canonical, hx
from link import verify
from summarize import CONDITIONS


SHARED = ('actor-template.json', 'primary-reference.json', 'native-parser-source.py',
          'native_environment.py', 'native-bindings-public.json', 'native_fault.py',
          'capture_client.py', 'capture_source.py', 'receipt_protocol.py', 'injection.py',
          'release/defense/qwen_backend.py', 'flash/flash-identity.json', 'flash/gate-contract.json',
          'flash/gate_core.py', 'flash/gate_client.py', 'flash/flash_runtime.py',
          'flash/flash_service.py', 'flash/wire_contract.py')

LOADED = r'''
import os
assert os.getuid() == 1033
verified = {}
for spec in STAGED:
    p = Path(spec['package'])
    assert sha(p/'manifest.json') == spec['manifest_sha256']
    assert sha(p/'plan.json') == spec['plan_sha256']
    for name,digest in spec['shared'].items():
        assert sha(p/name) == digest, (spec['stage'],name)
    primary = Path(spec['output'])/'primary'
    flash = p/'flash/service'
    main, mh = journal(primary/'journal/events.jsonl', live=True)
    aux, ah = journal(flash/'journal/events.jsonl', live=True)
    assert spec['main_chain_at_collection'] in {e['sha256'] for e in main}
    assert spec['flash_chain_at_collection'] in {e['sha256'] for e in aux}
    ml, = data(main, 'loaded')
    fl, = data(aux, 'loaded')
    main_loaded = read(primary/'loaded.json')
    flash_loaded = read(flash/'loaded.json')
    assert sha(primary/'loaded.json') == ml['loaded_sha256']
    assert sha(flash/'loaded.json') == fl['loaded_sha256']
    contract = read(p/'flash/gate-contract.json')
    assert fl['contract_sha256'] == spec['shared']['flash/gate-contract.json']
    assert main_loaded['identity']['uid'] == 1033
    assert main_loaded['attention'] == 'sdpa' and main_loaded['native_generate_unchanged']
    assert not main_loaded['main_history_truncation'] and not main_loaded['image_preprocessing_changed']
    assert flash_loaded['dtype'] == 'bfloat16' and flash_loaded['revision'] == contract['revision']
    assert flash_loaded['single_image'] and flash_loaded['no_cross_request_KV']
    assert main_loaded['dtype'] == spec['dtype']
    if spec['dtype'] == 'NF4 weights; BF16 compute':
        cfg = main_loaded['quantization']
        assert cfg['load_in_4bit'] and cfg['bnb_4bit_quant_type'] == 'nf4'
        assert cfg['bnb_4bit_compute_dtype'] == 'bfloat16'
        assert main_loaded['physical_gpus'] == [0,1,2]
    else:
        assert main_loaded['physical_gpus'] == list(range(7))
    actual_begun = [e['run_id'] for e in data(main, 'run_begin')]
    assert actual_begun == spec['allowed_order'][:len(actual_begun)]
    assert set(spec['reviewed_seals']) <= set(actual_begun)
    ends  = unique(data(main,'run_end'),lambda e:e['run_id'])
    for run,expected_end in spec['reviewed_seals'].items():
        if expected_end is None:
            assert run not in ends
        else:
            assert ends[run]['terminal_sha256'] == expected_end
    verified[spec['stage']] = {
        'main_dtype': main_loaded['dtype'], 'main_physical_gpus': main_loaded['physical_gpus'],
        'main_loaded_sha256': ml['loaded_sha256'], 'Flash_loaded_sha256': fl['loaded_sha256'],
        'Flash_revision': flash_loaded['revision'], 'primary_chain_head': mh, 'flash_chain_head': ah,
        'started_in_frozen_order':len(actual_begun),'model_end_notifications':len(ends),
        'scoring_not_requested_by_auditor':True}
print(json.dumps(verified))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    args = p.parse_args()
    verify(args.ledger)
    ledger = read(args.ledger / 'private-linked.json')
    catalog = stages()
    ptr, baseline, queue = manifest_for('BF16-original')
    reference = read(Path(ptr['runtime']) / 'plan.json')
    tasks = {s['task_id'] for s in queue}
    assert len(queue) == len({r['run_id'] for r in queue}) == 100
    assert len(tasks) == len(reference['tasks']) == 10
    assert len({r['pair_id'] for r in queue}) == 50
    assert Counter((r['task_id'],r['condition'],r['arm']) for r in queue) == Counter(
        (t,c,a) for t in tasks for c in CONDITIONS for a in ('on','off'))
    assert Counter((r['condition'],r['arm']) for r in queue[::2]) == Counter(
        {(c,a):5 for c in CONDITIONS for a in ('on','off')})
    for off_or_on, other in zip(queue[::2],queue[1::2]):
        assert {off_or_on['arm'],other['arm']} == {'on','off'}
        assert all(off_or_on[k] == other[k] for k in ('pair_id','task_id','condition'))
    assert reference['actor_budget'] == {'max_steps':50,'max_calls':70,'max_new_tokens':2048,'seed':42}
    assert reference['browser_seed'] == 20261011 and reference['native_full_history']
    assert reference['gate_recapture_wait_seconds'] == 0.5 and reference['gate_manual_or_yes_only']
    assert not reference['old_paused_queue_resumed']
    assert reference['analysis_checkpoints_seconds_do_not_change_gate'] == [30,120]
    assert [r['slot'] for r in ledger['rows']] == queue
    shared = {name:baseline['files'][name] for name in SHARED}
    stages_out, remote = {}, []
    previous = None
    for stage, (_, start, end) in catalog.items():
        ptr, manifest, suffix = manifest_for(stage)
        folder = Path(ptr['runtime'])
        assert all(sha(folder/name) == digest for name,digest in manifest['files'].items())
        assert all(manifest['files'][name] == digest for name,digest in shared.items())
        assert suffix == queue[start:]
        config = read(folder/'plan.json')
        assert all(config[k] == v for k,v in reference.items() if k != 'queue')
        assert config.get('action_envelope_compatibility') == (
            None if stage == 'BF16-original' else 'qwen-observed-action-envelopes-v1')
        rows = ledger['rows'][start:end]
        assert all(r['stage_id'] == stage and r['version'] == measurement_version(stage) for r in rows)
        observed = ledger['collections'][stage]
        origin = Path(observed['path'])
        verify(origin)
        assert sha(origin/'seal.json') == observed['seal_sha256']
        record = read(origin/(stage+'.json'))
        assert record['manifest_sha256'] == ptr['manifest_sha256']
        fingerprints = record['hosts']['3090']
        changes = None if previous is None else {
            'modified': sorted(k for k in previous.keys() & manifest['files'].keys()
                               if previous[k] != manifest['files'][k]),
            'added': sorted(manifest['files'].keys() - previous.keys()),
            'removed': sorted(previous.keys() - manifest['files'].keys())}
        previous = manifest['files']
        stages_out[stage] = {'measurement_version':measurement_version(stage), 'assigned_slots':end-start,
                             'manifest_sha256':ptr['manifest_sha256'], 'plan_sha256':ptr['plan_sha256'],
                             'file_differences_from_parent':changes}
        remote.append({'stage':stage, 'package':manifest['package3090'], 'output':manifest['output3090'],
                       'manifest_sha256':ptr['manifest_sha256'],'plan_sha256':ptr['plan_sha256'],'shared':shared,
                       'dtype':'NF4 weights; BF16 compute' if measurement_version(stage)=='NF4' else 'bfloat16',
                       'main_chain_at_collection':fingerprints['primary_chain_head'],
                       'flash_chain_at_collection':fingerprints['flash_chain_head'],
                       'allowed_order':[r['slot']['run_id'] for r in rows],
                       'reviewed_seals':{r['slot']['run_id']:r['evidence']['terminal_sha256']
                           if r['evidence']['model_run_end_bound'] else None for r in rows if r['evidence']}})

    out = HERE/'protocol-conformance'/str(time.time_ns())
    out.mkdir(parents=True,exist_ok=False)
    control.ROOT = out
    library = (HERE/'extract_on_host.py').read_text(encoding='utf-8')
    receipt = control.remote('3090', f"__name__='evidence_library'\nSTAGED={remote!r}\n" + library + '\n' + LOADED,
                             'bind-frozen-plan-to-actual-modeled-stages',timeout=55)
    operation = Path(receipt['operation'])
    verify(operation)
    assert set(receipt['result']) == set(stages_out)
    result = {'ledger_seal_sha256':sha(args.ledger/'seal.json'),'assigned_tasks':sorted(tasks),'assigned_pairs':50,
              'assigned_slots':len(queue),'unchanged_task_configs_sha256':hx(canonical(reference['tasks'])),
              'original_order_sha256':hx(canonical(queue)),'fixed_actor_budget':reference['actor_budget'],
              'verified_shared_file_sha256':shared,'stage_differences':stages_out,
              'actual_loaded_stage_evidence':receipt['result'],'operation':str(operation),
              'operation_seal_sha256':sha(operation/'seal.json'),'model_GUI_scoring_calls_by_auditor':0}
    save(out/'index.json',result)
    save(out/'seal.json',{'index.json':sha(out/'index.json')})
    print(json.dumps({'protocol_audit':str(out),'seal_sha256':sha(out/'seal.json'),
                      'actual_stages':receipt['result'],'assigned_slots':100}))


if __name__ == '__main__':
    main()
