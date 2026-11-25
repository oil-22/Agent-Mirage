"""Collect sealed GUI terminals and their model evidence without a service call."""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
sys.path.insert(0, str(EXPERIMENT))
import control


VERSIONS = {
    'BF16-original': ('frozen-current.json', 0, 22),
    'BF16-envelope': ('action-envelope-repair/linked-current.json', 22, 26),
    'NF4': ('quantized-continuation-20261123/current.json', 26, 100),
}
NF4_RESUME_POINTER = 'quantized-continuation-20261123/native-key-resume-current.json'
NF4_RESOURCE_RESUME_POINTER = 'quantized-continuation-20261123/resource-stop-resume-current.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def stages():
    result = VERSIONS.copy()
    if (EXPERIMENT/NF4_RESUME_POINTER).exists():
        ptr = read(EXPERIMENT/NF4_RESUME_POINTER)
        old, start, end = VERSIONS['NF4']
        assert ptr['stage_id']=='NF4-resume-01' and ptr['measurement_version']=='NF4'
        assert start < ptr['preserved_prefix'] < end and ptr['preserved_prefix']+ptr['unstarted_suffix']==end
        result['NF4']=(old,start,ptr['preserved_prefix'])
        result[ptr['stage_id']]=(NF4_RESUME_POINTER,ptr['preserved_prefix'],end)
    if (EXPERIMENT/NF4_RESOURCE_RESUME_POINTER).exists():
        ptr = read(EXPERIMENT/NF4_RESOURCE_RESUME_POINTER)
        parent = ptr['parent_stage']
        old, start, end = result[parent]
        cut = ptr['preserved_prefix']
        assert parent == 'NF4-resume-01' and ptr['stage_id'] == 'NF4-resume-02'
        assert ptr['measurement_version'] == 'NF4' and start < cut < end
        assert cut + ptr['unstarted_suffix'] == end
        assert read(EXPERIMENT/old)['manifest_sha256'] == ptr['parent_manifest_sha256']
        result[parent]=(old,start,cut)
        result[ptr['stage_id']]=(NF4_RESOURCE_RESUME_POINTER,cut,end)
    return result


def measurement_version(stage):
    return stage if stage in VERSIONS else 'NF4'


def latest_nf4_stage():
    return next(s for s in reversed(stages()) if measurement_version(s)=='NF4')


def manifest_for(stage):
    ptr = read(EXPERIMENT / stages()[stage][0])
    root = Path(ptr['runtime'])
    mf = read(root / 'manifest.json')
    assert sha(root / 'manifest.json') == ptr['manifest_sha256']
    assert sha(root / 'plan.json') == ptr['plan_sha256'] == mf['plan_sha256']
    return ptr, mf, read(root / 'plan.json')['queue']


def collect(batch, stage, source, full_queue, previous):
    ptr, manifest, queue = manifest_for(stage)
    _, start, end = stages()[stage]
    planned = full_queue[start:end]
    assert queue == full_queue[start:]
    allowed = {x['run_id'] for x in planned}
    results = {'version': measurement_version(stage), 'stage_id':stage, 'manifest_sha256': ptr['manifest_sha256'],
               'plan_sha256': ptr['plan_sha256'], 'intended_slots': len(planned), 'hosts': {}}
    old_gui={}; old_model={}
    if previous and (previous/(stage+'.json')).exists():
        recorded=read(previous/'seal.json')
        prior=previous/(stage+'.json')
        assert sha(prior)==recorded[prior.name]
        before=read(prior)
        assert before['manifest_sha256']==ptr['manifest_sha256']
        assert before['plan_sha256']==ptr['plan_sha256']
        old_gui,old_model=(before['hosts'][h] for h in ('4090','3090'))
        assert set(old_gui['runs']) <= allowed
        results['base_audit']={'previous_collection':str(previous),'seal_sha256':sha(previous/'seal.json'),
                               'previous_version_file_sha256':recorded[prior.name],
                               'old_terminals':len(old_gui['runs'])}
    for host in ('4090', '3090'):
        prefix = (f'ROOT={manifest["package"+host]!r}\nOUTPUT={manifest["output3090"]!r}\n'
                  f'EXPECTED={ptr["manifest_sha256"]!r}\nHOST={host!r}\n'
                  f'OWNED_RUNS={sorted(allowed)!r}\n')
        if host == '3090':
            prefix += (f'TARGET_RUNS={sorted(set(results["hosts"]["4090"]["runs"])-set(old_gui.get("runs",{})))!r}\n'
                       f'OLD_PRIMARY_HEAD={old_model.get("primary_chain_head")!r}\n'
                       f'OLD_FLASH_HEAD={old_model.get("flash_chain_head")!r}\n')
        else:
            known={r:v['terminal_sha256'] for r,v in old_gui.get('runs',{}).items()}
            prefix += f'KNOWN_TERMINALS={known!r}\n'
        raw = control.remote(host, prefix + 'import os\nos.nice(10)\n' + source,
                             'extract-' + stage, timeout=240)
        result = raw['result']
        if host=='4090' and old_gui:
            assert set(result['runs']).isdisjoint(old_gui['runs'])
            assert set(result['previously_audited_terminals_rechecked'])==set(old_gui['runs'])
            result['runs']={**old_gui['runs'],**result['runs']}
        if host=='3090' and old_model:
            assert all(result['run_end'].get(k)==v for k,v in old_model['run_end'].items())
            for k in ('requests','flash'):
                assert result[k].keys().isdisjoint(old_model[k])
                result[k]={**old_model[k],**result[k]}
            result['public_legal_messages']={**old_model['public_legal_messages'],**result['public_legal_messages']}
        found = set(result['runs'] if host == '4090' else result['run_begin'])
        assert found <= allowed, (stage, host, found - allowed)
        results['hosts'][host] = result
        results.setdefault('transport', {})[host] = {
            'operation': raw['operation'], 'seal_sha256': sha(Path(raw['operation']) / 'seal.json')}
    save(batch / (stage + '.json'), results)
    return {'GUI_terminals': len(results['hosts']['4090']['runs']),
            'GUI_unsealed': len(results['hosts']['4090']['live_unsealed']),
            'model_run_end': len(results['hosts']['3090']['run_end']),
            'bound_model_attempts': len(results['hosts']['3090']['requests'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    catalog=stages()
    parser.add_argument('versions', nargs='*', metavar='STAGE', help=', '.join(catalog))
    parser.add_argument('--previous',type=Path,help='Reuse terminal evidence after checking unchanged GUI terminal SHA and model/Flash journal ancestry.')
    args = parser.parse_args()
    versions = list(dict.fromkeys(args.versions)) or list(catalog)
    if set(versions)-catalog.keys():
        parser.error('choose from ' + ', '.join(catalog))
    _, _, full = manifest_for('BF16-original')
    assert len(full) == len({v['run_id'] for v in full}) == 100
    assert all(a['pair_id'] == b['pair_id'] and a['gate_enabled'] != b['gate_enabled']
               for a, b in zip(full[::2], full[1::2]))
    source_path = HERE / 'extract_on_host.py'
    # Compile locally before starting any read-only remote process.
    source = source_path.read_text(encoding='utf-8')
    compile(source, str(source_path), 'exec')
    batch = HERE / 'collections' / str(time.time_ns())
    batch.mkdir(parents=True, exist_ok=False)
    control.ROOT = batch
    save(batch / 'collection.json', {'extractor_sha256': sha(source_path), 'versions': versions,
                                     'mode': 'read_only', 'run_locks_or_service_calls': 0})
    print('Evidence collection:', batch, flush=True)
    index = {}
    with ThreadPoolExecutor(max_workers=len(versions)) as pool:
        jobs = {pool.submit(collect, batch, version, source, full,
                            args.previous.resolve() if args.previous else None): version for version in versions}
        for job in as_completed(jobs):
            version = jobs[job]
            try:
                index[version] = job.result()
            except Exception as exc:
                index[version] = {'reader_error': repr(exc)}
            print(version, json.dumps(index[version], ensure_ascii=False), flush=True)
    save(batch / 'index.json', index)
    names = sorted(p for p in batch.iterdir() if p.suffix == '.json')
    save(batch / 'seal.json', {p.name: sha(p) for p in names})
    return int(any('reader_error' in x for x in index.values()))


if __name__ == '__main__':
    sys.exit(main())
