"""Read-only sealed-file allocation statistics; no source data is rewritten."""
import argparse
import collections
import json
from pathlib import Path
import time

from orchestrate import HERE, OUTPUT, REMOTE_PACKAGE, COMMON, remote, save, sha
from join_source_reviews import verify_seal


CODE = r'''
root=Path(ROOT);package=Path(PACKAGE)
assert os.getuid()==1033 and root.stat().st_uid==1033 and not root.is_symlink()
assert sha(package/'manifest.json')==MANIFEST
def volume(p):
 s=p.stat();v=os.statvfs(p)
 try:
  mounted=json.loads(subprocess.check_output(['findmnt','-J','-T',str(p),'-o','TARGET,SOURCE,FSTYPE,OPTIONS'],text=True))
 except Exception as error:
  mounted={'unavailable':type(error).__name__}
 return {'path':str(p),'device':s.st_dev,'uid':s.st_uid,'available_bytes':v.f_bavail*v.f_frsize,
  'total_bytes':v.f_blocks*v.f_frsize,'mount':mounted}
rows=[]
for reference in SEALED:
 ident=reference['request'];assert ident.isdigit()
 p=root/'worker/requests'/ident
 assert p.stat().st_uid==1033 and not p.is_symlink()and sha(p/'seal.json')==reference['seal_sha256']
 seal=json.loads((p/'seal.json').read_bytes());sizes={};blocks={}
 for name in seal:
  assert Path(name).name==name
  f=p/name;s=f.stat();assert f.is_file()and not f.is_symlink()and s.st_uid==1033
  sizes[name]=s.st_size;blocks[name]=s.st_blocks*512
 sizes['seal.json']=(p/'seal.json').stat().st_size
 blocks['seal.json']=(p/'seal.json').stat().st_blocks*512
 rows.append({'request':ident,'operation':reference['operation'],'decision_index':reference['decision_index'],
  'seal_sha256':reference['seal_sha256'],'file_logical_bytes':sizes,'file_allocated_bytes':blocks,
  'prepared_and_actual_first_forward_pixels_have_equal_sealed_SHA':
   seal.get('prepared_pixel_values.tensor')is not None and seal.get('prepared_pixel_values.tensor')==seal.get('first_forward_pixel_values.tensor')})
print(json.dumps({'time':time.time(),'uid':os.getuid(),'data_volume':volume(root),'home_volume':volume(package),
 'sealed_requests':rows,'big_binary_SHA_not_repeated_for_capacity_statistics':True,
 'identity_authority_is_supplied_existing_full_SHA_snapshot':True,'running_unsealed_files_excluded':True,
 'no_mutation_GPU_allocation_or_model_GUI_scorer_calls':True}))
'''


def main(evidence):
    assert evidence.parent == HERE
    verify_seal(evidence)
    actual = json.loads((evidence / '3090.json').read_bytes())
    assert not actual['worker/process.json']['actual'].get('absent')
    sealed = actual['sealed_requests']
    folder = HERE / ('storage-footprint-evidence-' + str(time.time_ns()))
    folder.mkdir()
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(folder / 'intent.json', dict(time=time.time(), actual_evidence=str(evidence),
        actual_evidence_seal_sha256=sha(evidence / 'seal.json'), current_run='fullhistory23-T000-clean-aux',
        source_file_read_only=True, new_model_GUI_scorer_calls=0))
    prefix = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE)
        + '\nMANIFEST=' + repr(actual['manifest_sha256']) + '\nSEALED=' + repr(sealed) + '\n')
    remote_code = prefix + COMMON + CODE
    (folder / 'remote-source.py').write_text(remote_code, encoding='utf8')
    output, operation = remote('3090', remote_code, 'owned-live-sealed-request-storage-footprint-read-only', timeout=55)
    value = json.loads(output)
    save(folder / 'actual.json', dict(value, remote_operation=str(operation)))
    by_op, by_file, allocated = collections.Counter(), collections.Counter(), collections.Counter()
    identical = 0
    for row in value['sealed_requests']:
        by_op[row['operation']] += sum(row['file_logical_bytes'].values())
        by_file.update(row['file_logical_bytes'])
        allocated.update(row['file_allocated_bytes'])
        identical += row['prepared_and_actual_first_forward_pixels_have_equal_sealed_SHA']
    old = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32/logical-terminal-collection-1794251064196236500'
    verify_seal(old)
    original = json.loads((old / 'service-preservation.json').read_bytes())
    original_bytes = sum(s['bytes'] for row in original['selected_requests'] for s in row['original_file_stats'].values())
    scenario = 31 * original_bytes
    # A source-bound illustrative scenario only: aux and future trajectory length differ.
    summary = dict(time=time.time(), actual_source_evidence=str(evidence), sealed_requests=len(sealed),
        total_current_sealed_request_logical_bytes=sum(by_op.values()), logical_bytes_by_operation=dict(by_op),
        largest_filename_logical_bytes=by_file.most_common(6), total_selected_allocated_bytes=sum(allocated.values()),
        equal_sealed_prepared_first_forward_pixel_SHA_pairs=identical,
        data_available_bytes=value['data_volume']['available_bytes'], home_available_bytes=value['home_volume']['available_bytes'],
        data_filesystem=value['data_volume']['mount'], home_filesystem=value['home_volume']['mount'],
        original_first_track_current_root_request_logical_bytes=original_bytes,
        illustrative31_times_original_first_track_bytes=scenario,
        illustrative_scenario_exceeds_current_data_free=scenario>value['data_volume']['available_bytes'],
        scenario_is_not_forecast_or_upper_bound=True,
        different_future_lengths_auxiliary_and_full_history_costs_not_predictable_here=True,
        filesystem_compression_dedup_moves_or_deletions_performed=False,
        new_model_GUI_scorer_paid_calls=0, no_experiment_runtime_or_condition_changes=True,
        all31_future_storage_fit_not_proven=True)
    save(folder / 'summary.json', summary)
    save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
    authority = dict(root=str(folder), summary_sha256=sha(folder / 'summary.json'), seal_sha256=sha(folder / 'seal.json'))
    save(HERE / ('storage-footprint-evidence-created-' + folder.name.rsplit('-', 1)[1] + '.json'), authority)
    print(json.dumps(dict(authority, summary=summary), ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True, type=Path)
    main(parser.parse_args().evidence.resolve())
