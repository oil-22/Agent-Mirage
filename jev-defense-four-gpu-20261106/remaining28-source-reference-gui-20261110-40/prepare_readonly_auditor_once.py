"""Bind strict read-only native auditors to approved28 and the quote-ID schema."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'remaining29-full-history-gui-20261110-37'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    assert not(HERE/'readonly-auditor-preparation-created.json').exists()
    names=['auxiliary_receipt_checks.py','mixed_exchange_checks.py','primary_receipt_checks.py',
        'mixed_journal_map.py','mixed_audit_selection.py','mixed_audit_service.py','mixed_audit_GUI.py',
        'audit_mixed_receipts_once.py','auxiliary-receipt-audit-preparation-created.json']
    original={}
    for name in names:
        assert not(HERE/name).exists()
        shutil.copyfile(OLD/name,HERE/name);original[name]=sha(OLD/name)
    path=HERE/'mixed_audit_service.py';source=path.read_text(encoding='utf8')
    start=source.index("    plan = read(package / 'plan.json')\n")
    stop=source.index('    selected = selector.select_completed_requests',start)
    old=source[start:stop]
    new='''    plan = read(package / 'plan.json')
    continuation = read(package / 'continuation.json')
    require(manifest['tracks'] == 28 and manifest['total_original_tracks'] == 32 and manifest['skipped_completed_terminal_tracks'] == 4, 'Wrong approved28 queue')
    require(sha(package / 'continuation.json') == manifest['continuation_sha256'], 'Continuation source differs')
    require(sha(package / 'plan.json') == continuation['unchanged_full32_plan_sha256'], 'Original full32 plan differs')
    require(continuation['excluded_run_ids'] == [row['run_id'] for row in plan['queue'][:4]] ==
            ['fullhistory23-T000-clean-noaux', 'fullhistory23-T000-clean-aux', 'fullhistory23-T000-stale_replace-aux', 'fullhistory23-T000-stale_replace-noaux'], 'Four immutable terminal exclusions differ')
    for row in continuation['terminal_copies']:
        require(sha(package / row['copy']) == row['sha256'], 'Original terminal bytes differ')
    queue = [row for row in plan['queue'] if row['run_id'] not in continuation['excluded_run_ids']]
    require([row['run_id'] for row in queue] == continuation['remaining_run_ids'] and len(queue) == 28, 'Original remaining order differs')
    require(sha(package / 'completed-request-exclusions.json') == continuation['completed_request_exclusions_sha256'], 'Completed request exclusions differ')
    require(len(read(package / 'completed-request-exclusions.json')['unique_request_ids']) == 437, '437 original requests must remain excluded')
    require(manifest['source_condition_choice'] == 'adopt_exact_candidate_quote_reference_wire' and manifest['source_condition_decision_received'] is True, 'Approved quote-reference choice differs')
    require(sha(package / 'human-source-reference-condition-decision.json') == manifest['human_decision_receipt_sha256'], 'Exact human choice receipt differs')
    mapping = mapper.map_requests(events, queue, {'actor': 0, 'judge': 0, 'evidence': 0})
'''
    source=source[:start]+new+source[stop:]
    before="    schema, prompts = types.ModuleType('source_schema'), types.ModuleType('source_prompts')"
    assert source.count(before)==1
    source=source.replace(before,"    sys.path.insert(0, str(package / 'release'))\n"+before)
    before="phase='history_report' if payload['system'].startswith(prompts.HISTORY_REPORT) else None)"
    after="phase='history_report' if payload['system'].startswith(prompts.HISTORY_REPORT) else 'exact_source_reference' if payload['system'].startswith(prompts.VERIFY) else None)"
    assert source.count(before)==1;source=source.replace(before,after)
    compile(source,str(path),'exec');path.write_text(source,encoding='utf8',newline='\n')
    for name in names:
        if name!='mixed_audit_service.py':assert sha(HERE/name)==original[name]
    out=HERE/('readonly-auditor-preparation-'+str(time.time_ns()));out.mkdir()
    for name in names:shutil.copyfile(HERE/name,out/name)
    shutil.copyfile(__file__,out/Path(__file__).name)
    (out/'old-queue-binding.txt').write_text(old,encoding='utf8')
    (out/'new-queue-binding.txt').write_text(new,encoding='utf8')
    save(out/'receipt.json',dict(time=time.time(),original_auditor_SHAs=original,
        only_readonly_changes='28/four/437/approved receipt queue binding plus source-defined verify quote-ID schema; all native/HTTP/inputID/tensor/generation/EOS checks retained',
        runtime_changed=False, previous_controls_reexecuted=False,new_model_GPU_GUI_scorer_paid_calls=0))
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    result=dict(root=str(out),receipt_sha256=sha(out/'receipt.json'),seal_sha256=sha(out/'seal.json'))
    save(HERE/'readonly-auditor-preparation-created.json',result);print(json.dumps(result))

if __name__=='__main__':main()
