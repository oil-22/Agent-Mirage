"""Linked read-only retry after the source export's SSH read deadline.

Reuses the already frozen GUI prefix. It changes no model/GUI conditions and
retains all source, request seals and exact byte checks in the failed reader.
"""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, remote, save, sha


def main():
    failed=Path(sys.argv[1]).resolve()
    assert failed.parent==HERE and not(failed/'seal.json').exists()
    g=json.loads((failed/'GUI.json').read_bytes())
    gui=g['result'];events=gui['prefix_events']
    replies=[v for v in events if v['kind']=='actual_actor_reply']
    requests=[v for v in events if v['kind']=='actual_actor_request']
    count=len(replies);run=requests[0]['data']['run_id'] if 'run_id' in requests[0]['data'] else failed.name.split('source-prefix-',1)[1].rsplit('-'+str(count)+'-',1)[0]
    ops=HERE.parent/'flash-resource-continuation-20261115-linked12/operations'
    failed_ops=[]
    for op in ops.glob('*-live-prefix-lawful-full-history-PNG-export'):
        if (op/'failure.json').exists() and ('RUN='+repr(run)+'\nCOUNT='+repr(count)+'\n') in (op/'source.py').read_text('utf8'):
            failed_ops.append(op)
    assert len(failed_ops)==1
    op=failed_ops[0]
    save(failed/'failure.json',{'type':'ReadOnlySourceExportSSHDeadline','failed_reader_operation':str(op),'failed_reader_sha256':sha(op/'source.py'),'transport_failure':json.loads((op/'failure.json').read_bytes()),'GUI_and_models_continue_unchanged':True,'new_model_GUI_calls':0})
    save(failed/'seal.json',{q.name:sha(q)for q in failed.iterdir()if q.is_file()})
    root=HERE/('source-prefix-'+run+'-'+str(count)+'-linked-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'parent.json',{'root':str(failed),'seal_sha256':sha(failed/'seal.json'),'read_deadline_only_from_seconds':55,'read_deadline_only_to_seconds':240,'full_source_and_all_original_seal_checks_unchanged':True,'new_model_GUI_calls':0})
    (root/'GUI.json').write_bytes((failed/'GUI.json').read_bytes())
    (root/'unchanged-remote-reader.py').write_bytes((op/'source.py').read_bytes())
    print(json.dumps({'linked_root':str(root),'read_only':True,'new_model_GUI_calls':0}),flush=True)
    raw,operation=remote('3090',(op/'source.py').read_text('utf8'),'linked-prefix-lawful-full-history-PNG-export',timeout=240)
    actor=json.loads(raw);images=actor.pop('images');(root/'images').mkdir()
    for h,encoded in images.items():
        data=base64.b64decode(encoded,validate=True);assert hashlib.sha256(data).hexdigest()==h
        (root/'images'/(h+'.png')).write_bytes(data)
    assert len(actor['requests'])==len(requests)==len(replies)==count
    for row,reply,request in zip(actor['requests'],replies,requests):
        assert row['request_id']==reply['data']['request_id']==request['data']['request_id']
        assert row['body_sha256']==request['data']['body_sha256']
        assert hashlib.sha256(row['native_text'].encode()).hexdigest()==reply['data']['text_sha256']
    save(root/'actor.json',{'operation':str(operation),'result':actor})
    save(root/'summary.json',{'run_id':run,'complete_replies_in_prefix':count,'unique_original_delivered_PNGs':len(images),'full_lawful_histories_exported':True,'semantic_labels_not_provided':True,'official_score_not_in_reviewer_packet':True,'trajectory_semantics_unknown':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{str(q.relative_to(root)).replace('\\','/'):sha(q)for q in root.rglob('*')if q.is_file()})
    save(HERE/('source-prefix-'+run+'-'+str(count)+'-current.json'),{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'root':str(root),'replies':count,'unique_PNGs':len(images),'whole_trajectory_unknown':True,'new_model_GUI_calls':0}),flush=True)


if __name__=='__main__':main()
