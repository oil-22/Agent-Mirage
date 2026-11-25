"""Source-bound point-reader controls. No actor, GUI, hidden labels or answer access."""
import argparse,copy,json,time,traceback
from pathlib import Path
from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,canonical,digest
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in(a.source/'events.jsonl').read_text().splitlines()]
    req=next(e for e in reversed(events)if e['kind']=='verifier_request'and e['data']['phase']=='point'and e['data']['format_retry']==0)
    pub=req['data']['public'];images=tuple(VisibleImage((a.source/(i['sha256']+'.image')).read_bytes(),i['role'])for i in pub['images'])
    exact=PublicView(pub['observation_id'],copy.deepcopy(pub['messages']),images,pub['recent_action'],pub['execution_feedback'],pub['observed_at']);assert canonical(exact.data())==canonical(pub)
    points=[('exact_failed_point',523,679,'button','1'),('adjacent_page_two',563,679,'button','2'),('blank_background',100,100,'background',''),('footer_contact_text',135,875,'content','Contact')]
    manifest={'source':str(a.source),'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'source_request_seq':req['seq'],'source_public_sha256':digest(canonical(pub)),
        'predeclared_points':[{'name':n,'x':x,'y':y,'expected_kind':k,'expected_visible_text':t}for n,x,y,k,t in points],
        'scope':'Nonblind development controls on one real screenshot. Expected labels never sent to reader. Not Mirage labels, formal outcomes or efficacy. No GUI or actor.'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[];frozen=None
    for name,x,y,kind,text in points:
        (a.root/'status.json').write_text(json.dumps({'phase':'running','case':name,'time':time.time()}))
        log=Journal(a.root/name);c=Controller(model.judge,log,'joint',Limits());before=len(model.calls)
        proposal={'name':'click','parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':{'type':'click','x':x,'y':y}}
        try:
            if name=='exact_failed_point':
                log.observation(exact,audience='source_public');v=c.inspect('point',exact,req['data']['candidate'])
                frozen=v
            else:v=c.check_current_point(exact,proposal,'unknown')['point']
            passed=v['kind']==kind and (v['visible_text'].strip()==text if text else v['visible_text'].strip()=='')
            row={'case':name,'passed':passed,'verdict':v,'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
        except Exception:row={'case':name,'passed':False,'error':traceback.format_exc(),'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
        logged=[json.loads(x)for x in(log.root/'events.jsonl').read_text().splitlines()]
        if name=='exact_failed_point':
            assert all(canonical(e['data']['public'])==canonical(pub)and e['data']['candidate']==req['data']['candidate']for e in logged if e['kind']=='verifier_request')
            row['exact_public_and_query_unchanged']=True
        row['events_sha256']=digest((log.root/'events.jsonl').read_bytes());results.append(row)
        (a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
    if frozen:
        for name,page,expected in [('matching_target',1,'supported'),('wrong_target',3,'contradicted')]:
            (a.root/'status.json').write_text(json.dumps({'phase':'running','case':name,'time':time.time()}))
            log=Journal(a.root/name);c=Controller(model.judge,log,'joint',Limits());before=len(model.calls)
            candidate='I will click page '+str(page)+'.\n<action>{"type":"click","x":523,"y":679}</action>'
            proposal={'name':'click','parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000','payload':{'type':'click','x':523,'y':679}}
            try:
                v=c.check_target_alignment(exact,candidate,proposal,frozen)
                verdict=v['result']
                row={'case':name,'passed':verdict['action']['status']==expected,'verdict':verdict,'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
            except Exception:row={'case':name,'passed':False,'error':traceback.format_exc(),'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
            results.append(row);(a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
    name='pure_native_wait';(a.root/'status.json').write_text(json.dumps({'phase':'running','case':name,'time':time.time()}))
    log=Journal(a.root/name);c=Controller(model.judge,log,'post_only',Limits());before=len(model.calls)
    candidate='I will wait.\n<action>{"type":"wait"}</action>';proposal={'name':'wait','parsed':True,'executor_fallback_wait':False,'payload':{'type':'wait'},'coordinate_space':'normalized_1000'}
    try:
        v=c.inspect('verify',exact,candidate,proposal);row={'case':name,'passed':v['pure_wait']and v['action']['status']=='supported','verdict':v,'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
    except Exception:row={'case':name,'passed':False,'error':traceback.format_exc(),'verifier_calls':c.verifier_calls,'receipts':model.calls[before:]}
    results.append(row);(a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
    summary={'phase':'completed','passed':len(results)==7 and all(x['passed']for x in results),'results':results,'scope':manifest['scope']}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(a.root/'status.json').write_text(json.dumps({'phase':'completed','passed':summary['passed'],'time':time.time()}))
    print(json.dumps({'phase':'completed','passed':summary['passed']}),flush=True)
if __name__=='__main__':main()
