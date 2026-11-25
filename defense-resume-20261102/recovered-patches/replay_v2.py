"""Read-only replay of actual PUBLIC v1 inputs; never an environment recovery."""
import argparse,json,time,traceback
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(exist_ok=False,parents=True)
    requests=[]
    for path in sorted(a.source.glob('runs/*/attempt-*/events.jsonl')):
        events=[json.loads(line)for line in path.read_text().splitlines()]
        observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'}
        # Baseline has no verifier_request, but its actual delivered input and candidate
        # provide long-history coverage without adding hidden screenshots or answers.
        if '--baseline/'in str(path):
            for e in events:
                if e['kind']=='candidate':
                    pub=observations[e['data']['observation_id']]
                    requests.append((path,{'phase':'verify','public':pub,'candidate':e['data']['text']},[]))
        for i,e in enumerate(events):
            if e['kind']!='verifier_request' or e['data'].get('format_retry',0)!=0:continue
            d=e['data'];end=next((j for j in range(i+1,len(events))if events[j]['kind']=='verifier_request'and events[j]['data'].get('format_retry',0)==0),len(events))
            errors=[x['data']['error']for x in events[i+1:end]if x['kind']=='verifier_format_failure']
            requests.append((path,d,errors))
    # Fixed coverage categories. Selection uses technical context, never Mirage labels or answers.
    criteria=[
        ('normal_screen',lambda p,d,er:'--clean--'in str(p)and d['phase']=='screen'),
        ('normal_candidate',lambda p,d,er:'--clean--'in str(p)and d['phase']=='verify'),
        ('empty_evidence_failure',lambda p,d,er:'Usable verdict needs evidence'in er),
        ('coordinate_failure',lambda p,d,er:'Out-of-bounds evidence'in er),
        ('candidate_source_failure',lambda p,d,er:'Fabricated text citation'in er),
        ('long_history',lambda p,d,er:len(d['public']['messages'])>=30 and d['phase']=='verify'),
        ('blank_observation',lambda p,d,er:'--blank_replace--'in str(p)and d['phase']=='verify'and all(image_profile(VisibleImage((p.parent/(im['sha256']+'.image')).read_bytes()))['near_white_fraction']>.99 for im in d['public']['images'])),
        ('missing_observation',lambda p,d,er:not d['public']['images']and d['phase']=='verify'),
        ('stale_observation',lambda p,d,er:'--stale_replace--baseline/'in str(p)and d['public']['observation_id']=='002-obs002'),
        ('buttons_observation',lambda p,d,er:'--buttons_only--baseline/'in str(p)and d['public']['observation_id']=='025-obs025'),
    ]
    selected=[]
    for category,pred in criteria:
        match=next(((p,d,er)for p,d,er in requests if pred(p,d,er)),None)
        if match is None:raise RuntimeError('Missing required replay category: '+category)
        selected.append((category,*match))
    for category,base in [('stale_screen','stale_observation'),('blank_screen','blank_observation')]:
        _,p,d,er=next(x for x in selected if x[0]==base)
        selected.append((category,p,dict(d,phase='screen',candidate=None),er))
    match=next((x for x in requests if '--clean--'in str(x[0])and x[1]['phase']=='screen'and x[1]['public']['observation_id']=='002-obs002'),None)
    if match is None:raise RuntimeError('Missing normal transition control')
    selected.append(('normal_transition',*match))
    manifest=[{'category':cat,'source':str(p),'phase':d['phase'],'observation_id':d['public']['observation_id'],'old_protocol_errors':er,'public_request_sha256':digest(canonical(d['public']))}for cat,p,d,er in selected]
    (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[]
    deadline=time.time()+300
    while True:
        try:
            health=model.health()
            if health['phase']=='ready'and health.get('verifier_grammar')=='lm-format-enforcer-0.11.3':break
        except Exception:pass
        if time.time()>deadline:raise RuntimeError('Bounded prerequisite wait: model service unavailable')
        time.sleep(2)
    (a.root/'service-health.json').write_text(json.dumps(health,indent=2))
    for category,path,d,errors in selected:
        pub=d['public'];images=tuple(VisibleImage((path.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in pub['images'])
        v=PublicView(pub['observation_id'],pub['messages'],images,pub['recent_action'],pub['execution_feedback'],pub['observed_at'])
        log=Journal(a.root/category);controller=Controller(model.judge,log);log.observation(v)
        events=[json.loads(line)for line in path.read_text().splitlines()]
        cutoff=next(i for i,e in enumerate(events)if e['kind']=='observation'and e['data']['public']['observation_id']==v.observation_id)
        earlier={e['data']['public']['observation_id']:e['data']['public']for e in events[:cutoff]if e['kind']=='observation'}
        for event in events[:cutoff]:
            if event['kind']!='decision_accepted':continue
            accepted=event['data'];old=earlier[accepted['observation_id']]
            ims=tuple(VisibleImage((path.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in old['images'])
            controller.remember(PublicView(old['observation_id'],old['messages'],ims,old['recent_action'],old['execution_feedback'],old['observed_at']),accepted['candidate'])
        record={'category':category,'phase':d['phase'],'old_errors':errors,'candidate':d['candidate'],'source':str(path),'not_semantic_accuracy_estimate':True}
        try:
            proposal=None
            if d['candidate']and '<action>'in d['candidate']:
                payload=json.loads(d['candidate'].split('<action>',1)[1].split('</action>',1)[0])
                proposal={'name':payload['type'],'payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
            value=controller.inspect(d['phase'],v,d['candidate'],proposal)
            if proposal and proposal['name']=='click':
                crosscheck=controller.check_current_point(v,proposal,value['action']['target_kind'])
                record.update(point_probe=crosscheck['point'],point_agrees=crosscheck['agrees'])
            record.update(protocol_valid=True,result=value)
        except Exception:record.update(protocol_valid=False,error=traceback.format_exc())
        record['verifier_calls']=controller.verifier_calls;results.append(record)
        (a.root/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(record),flush=True)
    summary={'phase':'completed','cases':len(results),'protocol_valid':sum(x['protocol_valid']for x in results),'verifier_calls':sum(x['verifier_calls']for x in results),'semantic_mirage':None}
    (a.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
