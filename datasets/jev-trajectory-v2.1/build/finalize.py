"""Run the portable verifier, write actual counts, and package a self-contained release."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import zipfile

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from verify import check, lines, digest, require, sha
from validation_extension import BASE_FIXED, BASE_ROWS

def writej(p,value):
    p.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

def report():
    rows,stats=check(HERE,report=False)
    added=rows[BASE_ROWS:]; ids={r['sample_id'] for r in added}
    audits=[a for a in lines(HERE/'audit.jsonl') if a['sample_id'] in ids]
    bymode=Counter(a['source']['condition'] for a in audits)
    new_runs={a['source']['source_run'] for a in audits}
    calibration=dict(
        added_observed=len(added), added_constructed=0, added_by_delivery=dict(bymode),
        added_by_action=dict(Counter(m['action']['type'] for m in added)),
        added_by_family=dict(Counter(m['family_id'] for m in added)),
        added_source_runs=len(new_runs), added_source_tasks=len({m['task_id'] for m in added}),
        controls=sum(len(a['donor_sources']) for a in audits),
        same_trajectory_next_action_controls=sum(bool(d['control'] and d['control']['later_repeat']) for d in lines(HERE/'build/review-decisions.jsonl')),
        injected_native_unreplaced_pngs_available=sum(a['evidence']['original_unreplaced_png_in_package'] for a in audits),
        val_pair_observed=sum(r['pair_observed'] for r in rows if r['split']=='val'),
        val_constructed=sum(not r['pair_observed'] for r in rows if r['split']=='val'),
    )
    stats['validation_extension'].update(calibration)
    writej(HERE/'stats.json',stats)
    inputs={h for r in rows for h in (r['before_sha256'],r['candidate_sha256'])}
    support={h for a in lines(HERE/'audit.jsonl') for h in a.get('support_images',[])}
    files={p.stem for p in (HERE/'images').glob('*.png')}
    require(files==inputs|support,'PNG directory does not exactly cover model and audit evidence')
    sources=json.loads((HERE/'build/extension-checks.json').read_bytes())
    require(sources['reviewed_input_bindings']==sources['new_native_request_and_encoder_matches']==len(added) and
            sources['control_receipts']==calibration['controls'] and sources['logs_reconciled']==len(added)+calibration['controls'],'New source accounting')
    files=['train.jsonl','train-balanced.jsonl','test.jsonl','val.jsonl','val-v2-original.jsonl','val-added-no.jsonl',
           'val-added-index.jsonl','manifest.jsonl','audit.jsonl','protocol.json','build/review-decisions.jsonl']
    writej(HERE/'validation.json',dict(
        verified_unique_model_inputs=stats['rows'],split_label_counts=stats['splits'],**calibration,
        observed_source_and_native_encoder_checks=sources,
        original_v2_complete_manifest_and_audit_prefix_sha_verified=True,
        original_v2_files_verified=list(BASE_FIXED),
        input_pngs_hashed_and_decoded=len(inputs),audit_only_pngs_hashed_and_decoded=len(support-inputs),
        duplicate_inputs=stats['duplicate_inputs'],cross_split_image_or_source_group_overlap=0,
        protected_regression_images=stats['regression_images_checked'],
        note='Per-row labels are a visual review using the dispatched action. Logs establish delivery and execution, not task success. Existing v2 proof is retained in build/v2-validation.json.',
        file_sha256={n:digest(HERE/n) for n in files}))
    print('Verified',stats['splits'],calibration,flush=True)

def pack():
    zip_path=HERE.parent/(HERE.name+'.zip')
    files=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.md','.py','.json','.jsonl','.png'})
    require(all(HERE/n in files for n in ('stats.json','validation.json','README.md','verify.py','val-added-no.jsonl','build/review-decisions.jsonl')),'Release missing files')
    sums=HERE/'checksums.sha256'
    sums.write_bytes(''.join(digest(p)+'  '+p.relative_to(HERE).as_posix()+'\n' for p in files).encode())
    files.append(sums)
    # Publish only after verifying every stored member and its checksum.
    draft=zip_path.with_suffix('.zip.part')
    with zipfile.ZipFile(draft,'w',allowZip64=True) as z:
        for f in files:z.write(f,f.relative_to(HERE).as_posix(),compress_type=zipfile.ZIP_STORED if f.suffix=='.png' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(draft) as z:
        require(len(z.namelist())==len(set(z.namelist()))==len(files) and z.testzip() is None,'ZIP CRC/member count')
        require(z.read(sums.name)==sums.read_bytes(),'Archived checksum file differs')
        for ln in z.read(sums.name).decode().splitlines():
            hx,n=ln.split('  ',1)
            with z.open(n) as f:require(hashlib.file_digest(f,'sha256').hexdigest()==hx,'ZIP member hash mismatch: '+n)
    hx=digest(draft)
    draft.replace(zip_path)
    (HERE/'bundle.sha256').write_bytes((hx+'  '+zip_path.name+'\n').encode())
    print('Verified ZIP',zip_path,zip_path.stat().st_size,hx,flush=True)

if __name__=='__main__':
    {'check':report,'zip':pack}[sys.argv[1]]()
