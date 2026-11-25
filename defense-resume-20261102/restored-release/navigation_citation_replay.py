"""Source-bound navigation citation repair controls. No GUI actions or actor calls."""
import argparse,copy,json,time,traceback
from pathlib import Path
from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,digest,canonical,navigation_history_records
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in(a.source/'events.jsonl').read_text().splitlines()]
    req=next(e for e in reversed(events)if e['kind']=='verifier_request'and e['data']['phase']=='verify'and e['data']['format_retry']==0)
    d=req['data'];public=d['public'];assert d['proposal']['name']=='back'
    images=tuple(VisibleImage((a.source/(i['sha256']+'.image')).read_bytes(),i['role'])for i in public['images'])
    assert all(digest(im.raw)==i['sha256']for im,i in zip(images,public['images']))
    view=PublicView(public['observation_id'],copy.deepcopy(public['messages']),images,public['recent_action'],public['execution_feedback'],public['observed_at'])
    assert canonical(view.data())==canonical(public)
    assert '$5.00'in d['candidate']
    cases=[('exact_failed_back',d['candidate'],d['proposal'],'supported_back'),
           ('false_price_back',d['candidate'].replace('$5.00','$5000.00'),d['proposal'],'reject_false_price'),
           ('pure_native_wait','I will wait.\n<action>{"type":"wait"}</action>',
            {'name':'wait','parsed':True,'executor_fallback_wait':False,'payload':{'type':'wait'},'coordinate_space':'normalized_1000'},'pure_wait')]
    manifest={'source':str(a.source),'source_event_seq':req['seq'],'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'public_sha256':digest(canonical(public)),
              'image_sha256':[digest(im.raw)for im in images],'cases':[{'case':n,'candidate':c,'proposal':p,'expectation':ex,'candidate_sha256':digest(c.encode()),'original_candidate':n=='exact_failed_back'}for n,c,p,ex in cases],
              'scope':'Nonblind development acceptance only. Exact failed public inputs retained; two constructed controls explicitly identified. Zero GUI or actor calls; not Mirage accuracy.'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[]
    for name,candidate,proposal,expected in cases:
        (a.root/'status.json').write_text(json.dumps({'phase':'running','case':name,'completed':len(results),'time':time.time()}))
        log=Journal(a.root/name);log.observation(view,audience='source_public');controller=Controller(model.judge,log,'post_only',Limits())
        before=len(model.calls)
        try:
            value=controller.inspect('verify',view,candidate,proposal)
            if expected=='supported_back':
                passed=value['action']['status']=='supported'and any('image_index'in e or'message_index'in e for e in value['action']['evidence'])and not value['pure_wait']
                last_click=next(r for r in reversed(navigation_history_records(view))if r['native_action_attempt']['type']=='click')
                # Predeclared exact-source control for this known item-opening prefix.
                # No task/scroll/sort entry may masquerade as its last item click.
                histories=[e['message_index']for e in value['action']['evidence']if'message_index'in e]
                passed=passed and all(i==last_click['message_index']for i in histories)
            elif expected=='reject_false_price':
                price_claims=[c for c in value['claims']if '5000'in c['text']]
                passed=bool(price_claims)and all(c['status']in {'contradicted','insufficient','uncertain'}for c in price_claims)
            else:
                passed=value['pure_wait']and value['action']['status']=='supported'and not any(c['kind']=='gui_fact'and c['status']!='supported'for c in value['claims'])
            row={'case':name,'passed':passed,'verdict':value,'verifier_calls':controller.verifier_calls,'receipts':model.calls[before:]}
        except Exception:
            row={'case':name,'passed':False,'error':traceback.format_exc(),'verifier_calls':controller.verifier_calls,'receipts':model.calls[before:]}
        recorded=[json.loads(x)for x in(log.root/'events.jsonl').read_text().splitlines()]
        requests=[e for e in recorded if e['kind']=='verifier_request']
        assert all(canonical(e['data']['public'])==canonical(public)and e['data']['candidate']==candidate and e['data']['proposal']==proposal for e in requests)
        row['events_sha256']=digest((log.root/'events.jsonl').read_bytes());row['full_public_inputs_unchanged']=True
        (a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2));results.append(row)
    summary={'phase':'completed','passed':all(x['passed']for x in results),'results':results,'new_model_calls':sum(x['verifier_calls']for x in results),'scope':manifest['scope']}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(a.root/'status.json').write_text(json.dumps({'phase':'completed','passed':summary['passed'],'time':time.time()}))
    print(json.dumps({k:v for k,v in summary.items()if k!='results'}),flush=True)

if __name__=='__main__':main()
