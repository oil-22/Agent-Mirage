"""Bind a real verify wire reply to exact sources and actual Controller checks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
from orchestrate import HERE, PACKAGE, REMOTE_PACKAGE, OUTPUT, GUIROOT, COMMON, remote, save, sha, admitted
from join_source_reviews import verify_seal


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()


def main(audit,ident,review):
    admitted();assert audit.parent==review.parent==HERE
    verify_seal(audit);verify_seal(review)
    native=json.loads((audit/'3090-native-bindings.json').read_bytes())
    assert native['passed'] and ident in native['bindings']
    b=native['bindings'][ident];assert b['mapped_request']['operation']=='judge'
    labels=json.loads((review/'review.json').read_bytes())
    assert labels['independent_current_checker_execution_score_join_not_performed']
    code=('ROOT='+repr(OUTPUT)+'\nPACKAGE='+repr(REMOTE_PACKAGE)+'\nIDENT='+repr(ident)+'\nBINDING='+repr(b)+'\n'+COMMON+r'''
p=Path(ROOT)/'worker/requests'/IDENT
assert sha(p/'seal.json')==BINDING['request_seal_sha256']and sha(p/'external-wire.json')==BINDING['wire_sha256']
wire=json.loads((p/'external-wire.json').read_bytes());payload=wire['payload']
response=json.loads((p/'response.json').read_bytes());call=json.loads((p/'native-call.json').read_bytes())
assert response==BINDING['response']and response['verdict']==call['text']
print(json.dumps({'request_id':wire['request_id'],'candidate':payload['candidate'],'system':payload['system'],
 'schema':call['verifier_grammar']['schema'],'raw_reply':response['verdict'],'request_seal_sha256':sha(p/'seal.json'),
 'wire_sha256':sha(p/'external-wire.json'),'native_call_sha256':sha(p/'native-call.json')}))
''')
    out=HERE/('quote-reference-runtime-audit-'+ident+'-'+str(time.time_ns()));out.mkdir()
    save(out/'intent.json',dict(native_audit=str(audit),native_audit_seal_sha256=sha(audit/'seal.json'),
        source_review=str(review),source_review_sha256=sha(review/'review.json'),request=ident,new_model_GUI_scorer_paid_calls=0))
    try:
        raw,op3090=remote('3090',code,'read-only-real-quote-reference-source-'+ident,timeout=55)
        source=json.loads(raw);save(out/'actual-wire-source.json',source)
        label=next(row for row in labels['rows']if row['candidate_text_sha256']==digest(source['candidate'].encode()))
        sys.path.insert(0,str(PACKAGE/'release'))
        from source_quote_references import source_index
        from defense.prompts import VERIFY
        assert source['system'].startswith(VERIFY)
        marker='EXACT_QUOTE_SOURCE_DATA:\n';assert source['system'].count(marker)==1
        table,_=json.JSONDecoder().raw_decode(source['system'].split(marker,1)[1])
        index=source_index(source['candidate']);save(out/'exact-source-index.json',index)
        assert table==[dict(quote_id=r['quote_id'],text=r['text'])for r in index['rows']]
        for row in index['rows']:
            assert digest(row['text'].encode())==row['text_utf8_sha256']
            for occurrence in row['sources']:
                left,right=occurrence['candidate_codepoint_span']
                assert 0<=left<right<=len(source['candidate'])
                raw_source=source['candidate'][left:right]
                if occurrence['lane']=='raw_candidate':assert raw_source==row['text']
                else:
                    assert occurrence['lane']=='decoded_native_STOP_answer'
                    assert json.loads('"'+raw_source+'"')==row['text']
        props=source['schema']['properties']['claims']['items']
        assert 'text'not in props['properties'] and 'text'not in props['required']
        assert props['properties']['quote_id']==dict(type='string',enum=[r['quote_id']for r in index['rows']])
        wire=json.loads(source['raw_reply']);resolved=copy.deepcopy(wire)
        by_id={r['quote_id']:r for r in index['rows']}
        for row,target in zip(wire['claims'],resolved['claims']):
            assert 'text'not in row and row['quote_id']in by_id
            ident_value=target.pop('quote_id');target['text']=by_id[ident_value]['text']
            assert {k:v for k,v in row.items()if k!='quote_id'}=={k:v for k,v in target.items()if k!='text'}
        save(out/'unaltered-wire-verdict.json',wire);save(out/'source-restored-verdict-copy.json',resolved)
        code=('ROOT='+repr(GUIROOT)+'\nREQUEST_ID='+repr(source['request_id'])+'\nRAW_REPLY='+repr(source['raw_reply'])+'\n'+COMMON+r'''
found=[]
for p in sorted((Path(ROOT)/'batch/runs').glob('*/attempt-*/events.jsonl')):
 raw=p.read_bytes();raw=raw[:raw.rfind(b'\n')+1]if raw and not raw.endswith(b'\n')else raw
 events=[];previous='0'*64
 for line in raw.splitlines():
  e=json.loads(line);core=dict(e);signature=core.pop('sha256')
  assert e['seq']==len(events)and e['previous']==previous and hashlib.sha256(json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
  events.append(e);previous=signature
 matches=[i for i,e in enumerate(events)if e['kind']=='actual_judge_wire_response'and e['data']['body']['request_id']==REQUEST_ID]
 for pos in matches:
  end=next((i for i in range(pos+1,len(events))if events[i]['kind']=='verifier_request'),len(events))
  window=events[pos:end]
  raws=[e for e in window if e['kind']=='verifier_raw'];assert len(raws)==1 and raws[0]['data']['phase']=='verify'and raws[0]['data']['response']==RAW_REPLY
  bindings=[e for e in window if e['kind']=='candidate_quote_reference_resolved'];assert len(bindings)==1
  origins=[e for e in window if e['kind']=='candidate_claim_origin_check'];assert len(origins)==1
  assert origins[0]['data']['reject']is False
  found.append({'GUI_chain_path':str(p),'complete_prefix_events':len(events),'head':previous,
   'actual_wire_response_event':events[pos],'verifier_raw_event':raws[0],'Controller_resolution_event':bindings[0],
   'original_provenance_check_after_original_validator':origins[0]})
assert len(found)==1
print(json.dumps(found[0]))
''')
        raw,op4090=remote('4090',code,'read-only-real-Controller-quote-restoration-'+ident,timeout=55)
        controller=json.loads(raw);save(out/'actual-Controller-binding.json',controller)
        binding=controller['Controller_resolution_event']['data']
        assert binding['wire_verdict_sha256']==digest(canonical(wire))
        assert binding['resolved_verdict_sha256']==digest(canonical(resolved))
        assert binding['complete_source_index_sha256']==digest(canonical(index))
        assert binding['source_candidate_utf8_sha256']==index['source_candidate_utf8_sha256']
        assert len(binding['bindings'])==len(wire['claims'])
        result=dict(passed=True,time=time.time(),request=ident,real_native_audit=str(audit),
            candidate_event_sha256=label['candidate_event_sha256'],source_review_sha256=sha(review/'review.json'),source_units=len(index['rows']),
            actual_wire_claims=len(wire['claims']),nonempty_source_ID_mapping_naturally_exercised=bool(wire['claims']),
            prompt_table_schema_reply_original_sources_and_Controller_resolution_bound=True,
            original_verdict_and_provenance_validation_observed=True,
            all_non_source_claim_fields_and_action_preserved=True,
            current_candidate_acceptance_or_GUI_execution_certified=False,
            semantic_truth_completeness_falseblock_or_Mirage_efficacy_established=False,
            runtime_modified=False,new_model_GPU_GUI_scorer_paid_calls=0,
            operations={'3090':str(op3090),'4090':str(op4090)})
        save(out/'receipt.json',result)
        save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
        print(json.dumps(dict(root=str(out),receipt_sha256=sha(out/'receipt.json'),seal_sha256=sha(out/'seal.json'),
            passed=True,claims=len(wire['claims']),new_model_GUI_scorer_paid_calls=0)))
    except BaseException as exc:
        save(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),runtime_modified=False,new_model_GUI_scorer_paid_calls=0))
        save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native-audit',required=True,type=Path)
    p.add_argument('--request',required=True);p.add_argument('--source-review',required=True,type=Path)
    a=p.parse_args();main(a.native_audit.resolve(),a.request,a.source_review.resolve())
