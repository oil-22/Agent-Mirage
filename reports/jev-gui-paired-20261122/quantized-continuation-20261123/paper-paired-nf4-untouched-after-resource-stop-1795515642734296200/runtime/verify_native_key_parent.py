"""Read the sealed first NF4 attempt; startup must never submit one of its arms again."""

import json
from pathlib import Path

from resource_guard import sha


def read(p):
    return json.loads(p.read_bytes())


def checked(root, seal, *names):
    for name in names:
        assert sha(root/name) == seal[name], (root, name)


def verify_prior_nf4(package, host, full, gone, events):
    link = read(package/'nf4-resume-link.json')
    old_p = Path(link['parent_packages'][host])
    old_m = read(old_p/'manifest.json')
    assert sha(old_p/'manifest.json') == link['parent_manifest_sha256']
    assert sha(old_p/'plan.json') == old_m['plan_sha256'] == link['parent_plan_sha256']
    assert read(old_p/'plan.json')['queue'] == full[26:]
    expected = [r['run_id'] for r in full[26:29]]
    assert set(expected) == set(link['terminal_sha256_by_run'])
    if host == '3090':
        out = Path(old_m['output3090'])
        assert all(gone(read(q)) for q in (out/'launcher-process.json',out/'primary/process.json',
                                          old_p/'flash/service/process.json'))
        post = read(out/'postexit-seal.json')
        assert sha(out/'postexit-seal.json') == link['model_postexit_sha256']
        log = 'primary/journal/events.jsonl'
        checked(out, post, 'released.json','exit.json','primary/terminal.json',log,'primary/capacity/seal.json')
        assert read(out/'released.json')['fresh_lease_locks_closed'] == 9
        assert read(out/'primary/terminal.json')['done'] == 3
        rows,head = events(out/log)
        assert head == link['model_journal_head']
        begins = [x['data']['run_id'] for x in rows if x['kind']=='run_begin']
        ends = [x['data'] for x in rows if x['kind']=='run_end']
        assert begins == expected == [q['run_id'] for q in ends]
        assert [q['infrastructure_failure'] for q in ends] == [False,False,True]
        assert all(not q['manual_stop'] for q in ends)
        actual = {q['run_id']:q['terminal_sha256'] for q in ends}
    else:
        control=old_p/'control';batch=old_p/'batch';runs=batch/'runs'
        assert all(gone(read(control/name)) for name in ('process.json','runner-process.json'))
        post=read(control/'postexit-seal.json')
        assert sha(control/'postexit-seal.json') == link['GUI_postexit_sha256']
        checked(control,post,'exit.json','batch-terminal-seal.json')
        seal=read(control/'batch-terminal-seal.json')
        assert sha(control/'batch-terminal-seal.json') == link['GUI_batch_seal_sha256']
        checked(batch,seal,'status.json')
        st=read(batch/'status.json');assert st['phase']=='technical_failure' and st['processed']==3 and st['completed']==2
        assert {q.name for q in runs.iterdir()}==set(expected)
        actual={}
        for run,slot in zip(expected,full[26:29]):
            attempt,=(runs/run).glob('attempt-*')
            local=read(attempt/'seal.json')
            term=attempt/'terminal.json';log=attempt/'controller/events.jsonl'
            checked(attempt,local,'terminal.json','controller/events.jsonl')
            checked(batch,seal,*(q.relative_to(batch).as_posix() for q in (term,log,attempt/'seal.json')))
            t=read(term);assert t['run']==slot
            assert t['infrastructure_failure']==(run==expected[-1])
            assert (t['official_reward'] is None)==(run==expected[-1])
            actual[run]=sha(term)
        old,head=events(log)
        assert head == link['failed_GUI_controller_head']
        failed,=[x['data'] for x in old if x['kind']=='native_execution_failure']
        assert failed['message']=='Native environment failed: Keyboard.press: Unknown key: "Down"'
    assert actual==link['terminal_sha256_by_run']
    return {'old_processes_exited':True,'terminals':actual,'untouched_slot_count':len(full[29:])}


def admit_prior_capacity(native, package, root, save, sha, resource, journal):
    """Bind unchanged runtime/hardware to its archived successful full-history stress call."""
    link=read(package/'nf4-resume-link.json')
    old_p=Path(link['parent_packages']['3090'])
    old_m=read(old_p/'manifest.json')
    assert sha(old_p/'manifest.json')==link['parent_manifest_sha256']
    out=Path(old_m['output3090']);before=out/'primary';prior=before/'capacity'
    post=read(out/'postexit-seal.json')
    assert sha(out/'postexit-seal.json')==link['model_postexit_sha256']
    checked(out,post,'lease.json','primary/ready.json','primary/loaded.json','primary/checkpoint-admission.json',
            'primary/actual-state.json','primary/quantization-state.json','primary/capacity/seal.json')
    seal=read(prior/'seal.json');checked(prior,seal,'qualification.json','source.json','first-forward.json',
                                       'prepared.json','actual-generation.json','effective-generation.json')
    ready=read(before/'ready.json');q=read(prior/'qualification.json')
    assert sha(prior/'seal.json')==ready['capacity_seal_sha256']
    assert q['passed'] and q['input_tokens']==53167 and q['natural_EOS'] and q['original_2048_output_cap']
    assert q['identical_complete_native_input_bytes_to_BF16'] and q['NF4_engineering_calls']==1
    keys=('native_state','CUDA','device_map','physical_gpus','dtype','quantization','bitsandbytes','attention',
          'native_model_source_sha256','native_generation_backend_sha256','torch','transformers',
          'CUDA_LAUNCH_BLOCKING','primary_allocator_memory_fraction','allocator_gc_threshold')
    loaded=read(before/'loaded.json')
    assert all(loaded[k]==native.loaded[k] for k in keys)
    for name in ('checkpoint-admission.json','actual-state.json','quantization-state.json'):
        assert sha(before/name)==sha(root/name),name
    old_lease=read(out/'lease.json');new_lease=read(root.parent/'lease.json')
    pairs=list(zip(old_lease['gpu'],new_lease['gpu'],strict=True))
    assert len(pairs)==4 and all(a['index']==b['index'] and a['uuid']==b['uuid'] and b['free_mib']>=23000
                                 for a,b in pairs)
    live=resource(True)
    assert live['held_inherited_locks']==9
    cap=root/'capacity';cap.mkdir(exist_ok=False)
    save(cap/'previous-capacity.json',{'path':str(prior),'source_seal_sha256':sha(prior/'seal.json'),
                                      'source_qualification_sha256':sha(prior/'qualification.json'),
                                      'source_first_forward_sha256':seal['first-forward.json'],
                                      'same_checkpoint_runtime_layout_and_physical_GPU_UUIDs':True})
    save(cap/'fresh_resource_admission.json',live)
    result={'passed':True,'input_tokens':q['input_tokens'],'identical_complete_native_input_bytes_to_BF16':True,
            'new_engineering_generation_calls':0,'fresh_full_history_forward_not_repeated':True,
            'fresh_actual_quantization_and_resource_admission_passed':True,
            'capacity_memory_and_generation_evidence_from_prior_sealed_attempt':True}
    save(cap/'qualification.json',result)
    save(cap/'seal.json',{p.name:sha(p) for p in cap.iterdir()})
    digest=sha(cap/'seal.json')
    journal.emit('NF4_capacity_evidence_readmitted',{'seal_sha256':digest,'new_generation_calls':0})
    return {'summary':result,'seal_sha256':digest}
