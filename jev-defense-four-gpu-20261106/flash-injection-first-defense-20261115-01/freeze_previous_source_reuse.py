"""Bind pre-existing reviews only for byte-identical full inputs AND replies.

This is a local evidence join, not a new model call or independent reviewer.
"""
import hashlib
import json
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'flash-resource-continuation-20261115-linked12'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)


def dictionaries(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from dictionaries(child)
    elif isinstance(value,list):
        for child in value:yield from dictionaries(child)


def main():
    pointer=HERE/'exact-source-review-reuse-current.json';assert not pointer.exists()
    verified={}
    def check(root,expected=None):
        root=Path(root)
        if root in verified:
            if expected is not None:assert verified[root]==expected
            return
        h=sha(root/'seal.json')
        if expected is not None:assert h==expected
        for n,v in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/n)==v,(str(root),n)
        verified[root]=h
    p=json.loads((HERE/'completed-group-audit-current.json').read_bytes());newroot=Path(p['root']);check(newroot,p['seal_sha256'])
    newrows=json.loads((newroot/'native-and-Flash.json').read_bytes())['primary'];assert len(newrows)==103
    registryroot=OLD/'semantic-coverage-registry-1794681968796492900';check(registryroot)
    registry=json.loads((registryroot/'registry.json').read_bytes());labels={v['request_id']:v for v in registry['rows']}
    raw=[]
    for name in ['exited-parent-raw-current.json','exited-continuation-raw-current.json']:
        p=json.loads((OLD/name).read_bytes());root=Path(p['root']);check(root,p['seal_sha256'])
        for file in sorted(root.glob('main-*.json')):
            for row in json.loads(file.read_bytes())['result']['sealed_main_requests']:
                raw.append({**row,'local_raw_reader_result':str(file),'local_raw_reader_result_sha256':sha(file)})
    oldby={}
    for row in raw:
        if row['request_id']not in labels:continue
        label=labels[row['request_id']]
        assert row['seal_sha256']==label['request_seal_sha256']
        key=(row['body_sha256'],hashlib.sha256(row['native_text'].encode()).hexdigest())
        oldby.setdefault(key,[]).append((row,label))
    rows=[];pending=[];publication_cache={}
    for row in newrows:
        key=(row['body_sha256'],hashlib.sha256(row['native_text'].encode()).hexdigest())
        matches=oldby.get(key,[])
        if not matches:
            pending.append({'request_id':row['request_id'],'run_id':row['run_id'],'decision':row['decision'],'body_sha256':key[0],'reply_sha256':key[1],'current_image_sha256':row['current_image_sha256']});continue
        assert all(v[0]['native_text']==row['native_text']and v[0]['current_image_sha256']==row['current_image_sha256']for v in matches)
        assert all(v[1]['source_judgment']==matches[0][1]['source_judgment']and v[1]['pure_native_WAIT']==matches[0][1]['pure_native_WAIT']for v in matches)
        old,label=matches[0];pub=Path(label['publication']);check(pub,label['publication_seal_sha256'])
        if pub not in publication_cache:publication_cache[pub]=json.loads((pub/'review-joined.json').read_bytes())
        # Historical publication schemas differ. Locate the exact canonically
        # sealed row, rather than guessing one schema's nested key names.
        source=next(v for v in dictionaries(publication_cache[pub])if hashlib.sha256(canon(v)).hexdigest()==label['published_row_sha256'])
        assert hashlib.sha256(canon(source)).hexdigest()==label['published_row_sha256']
        assert old['request_id']in json.dumps(source)and old['seal_sha256']in json.dumps(source)
        rows.append({'request_id':row['request_id'],'run_id':row['run_id'],'decision':row['decision'],'new_request_seal_sha256':row['seal_sha256'],'exact_complete_body_sha256':key[0],'exact_complete_reply_sha256':key[1],'current_image_sha256':row['current_image_sha256'],'old_raw_binding':old,'old_registry_binding':label,'unchanged_original_publication_row':source,'exact_complete_history_and_candidate_reuse':True,'new_independent_reviewers':0})
    root=HERE/('exact-source-review-reuse-'+str(time.time_ns()));root.mkdir();(root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'reuse.json',{'time':time.time(),'new_group_audit':str(newroot),'registry':str(registryroot),'verified_local_seals':{str(k):v for k,v in verified.items()},'exact_reused_candidate_count':len(rows),'new_source_review_pending_count':len(pending),'rows':rows,'pending_new_candidates':pending,'new_or_changed_source_labels':0,'new_independent_reviewers':0,'new_model_GUI_calls':0,'complete_all103_semantic_review':not pending,'Mirage_reduction_proven':False})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'exact_reused':len(rows),'new_review_pending':len(pending)})
    print(json.dumps({'root':str(root),'exact_complete_body_AND_reply_reused':len(rows),'new_source_review_pending':len(pending),'new_model_GUI_calls':0}))


if __name__=='__main__':main()
