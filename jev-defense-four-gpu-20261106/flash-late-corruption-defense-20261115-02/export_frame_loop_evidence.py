"""Export exact already-audited bad/accepted frames, without model calls."""
import base64
import hashlib
import json
import time
from pathlib import Path, PurePosixPath
from control import HERE, manifest, remote, save, sha
from record_source_checkpoint import checked


def main():
    pointer = HERE/'frame-loop-source-evidence-current.json'
    assert not pointer.exists()
    audit, ar = checked(HERE/'completed-group-audit-current.json')
    summary = json.loads((ar/'summary.json').read_bytes())
    assert summary['processed_GUI_trajectories'] == 12
    assert summary['all_original_model_GUI_launcher_identities_exited']
    episodes = json.loads((ar/'capture-episodes.json').read_bytes())['result']['episodes']
    controllers = json.loads((ar/'GUI.json').read_bytes())['result']['controllers']
    mains = json.loads((ar/'native-and-Flash.json').read_bytes())['primary']
    by_id = {r['request_id']:r for r in mains}
    cases, files = [], {}
    for ep in episodes:
        loops = ep['real_NO_to_fresh_capture_YES_sequences']
        if not loops:
            continue
        assert ep['gate_enabled'] and ep['injection_fired'] and len(loops) == 1
        assert not ep['unmodified_raw_NO_for_source_review']
        loop = loops[0]
        assert loop['NO_count'] == 3 and loop['accepted_fresh_unmodified_raw']
        c = next(r for r in controllers if r['terminal']['run']['run_id'] == ep['run_id'])
        events = c['events']
        no_events = [r['gate'] for r in ep['injected_gate_decisions']]
        assert len(no_events) == 3 and all(r['data']['decision'] == 'NO' for r in no_events)
        yes = next(r for r in events if r['kind'] == 'gate_decision' and r['data']['capture_id'] == loop['YES']['capture_id'])
        request = next(r for r in events if r['kind'] == 'actual_actor_request' and r['seq'] > yes['seq'])
        reply = next(r for r in events if r['kind'] == 'actual_actor_reply' and r['seq'] > request['seq'])
        action = next(r for r in events if r['kind'] == 'native_environment_action' and r['seq'] > reply['seq'])
        assert not any(r['kind'] == 'actual_actor_request' and reply['seq'] < r['seq'] < action['seq'] for r in events)
        assert action['data']['ok'] is True
        main = by_id[request['data']['request_id']]
        assert main['request_id'] == reply['data']['request_id']
        assert hashlib.sha256(main['native_text'].encode()).hexdigest() == reply['data']['text_sha256']
        assert main['current_image_sha256'] == loop['YES']['image_sha256'] == loop['accepted_source']['captured_sha256']
        bad = {r['data']['image_sha256'] for r in no_events}
        run_requests = [by_id[r['data']['request_id']] for r in events if r['kind'] == 'actual_actor_request']
        assert not bad.intersection(h for r in run_requests for h in r['all_image_sha256s'])
        deliveries = [r['source']['data'] for r in ep['injected_gate_decisions']]+[loop['accepted_source']]
        for d in deliveries:
            for field, hash_field in [('raw_file','captured_sha256'),('delivered_file','delivered_sha256')]:
                file = str(PurePosixPath(c['attempt'])/d[field])
                if file in files:
                    assert files[file] == d[hash_field]
                files[file] = d[hash_field]
        cases.append({'run_id':ep['run_id'],'condition':ep['condition'],
            'trigger_step':ep['trigger_step'],'NO_count':3,'real_same_live_recaptures':3,
            'accepted_fresh_unmodified_raw':True,'bad_frames_absent_from_entire_main_history':True,
            'no_main_or_environment_action_between_first_NO_and_YES':True,
            'rejected_capture_events':no_events,'accepted_capture':loop,
            'deliveries':deliveries,'actual_primary_request':request['data'],
            'actual_primary_reply':main['native_text'],'actual_primary_reply_receipt_seal_sha256':main['seal_sha256'],
            'exact_normal_frame_reached_primary':True,'actual_native_action_after_acceptance':action['data']})
    assert len(cases) == 4 and sum(r['NO_count'] for r in cases) == summary['Flash_NO'] == 12
    m = manifest()
    code = 'FILES='+repr(files)+'\nP='+repr(m['package4090'])+'\n'+r'''
import base64,hashlib,json,os
from pathlib import Path
assert os.getuid()==1015
rows=[]
for name,h in FILES.items():
 q=Path(name);assert q.resolve().is_relative_to(Path(P).resolve())
 before=q.stat();raw=q.read_bytes();after=q.stat()
 assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
 assert hashlib.sha256(raw).hexdigest()==h and raw.startswith(b'\x89PNG\r\n\x1a\n')
 rows.append({'path':name,'sha256':h,'base64':base64.b64encode(raw).decode()})
print(json.dumps({'files':rows,'new_model_GUI_calls':0}))
'''
    raw, operation = remote('4090',code,'completed-frame-loop-exact-original-PNG-export',timeout=50)
    exported = json.loads(raw)
    assert {r['path']:r['sha256'] for r in exported['files']} == files
    root = HERE/('frame-loop-source-evidence-'+str(time.time_ns()))
    root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    (root/'user-frame-loop-acceptance.json').write_bytes((HERE/'user-frame-loop-acceptance-20261115.json').read_bytes())
    (root/'images').mkdir()
    for row in exported['files']:
        content = base64.b64decode(row.pop('base64'),validate=True)
        assert hashlib.sha256(content).hexdigest() == row['sha256']
        file = root/'images'/(row['sha256']+'.png')
        if file.exists():
            assert file.read_bytes() == content
        else:
            file.write_bytes(content)
    save(root/'evidence.json',{'time':time.time(),'audit':audit,'original_export_operation':str(operation),
        'cases':cases,'original_files':exported['files'],'manual_image_review_pending':True,
        'normal_frame_text_misreading_excluded_from_current_acceptance':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{str(q.relative_to(root)).replace('\\','/'):sha(q) for q in root.rglob('*') if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'frame_loop_evidence':str(root),'cases':len(cases),
        'unique_original_PNGs':len(list((root/'images').iterdir())),'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
