"""Frozen real terminal state -> source-bound feedback -> native actor redecision.

Offline development only: no GUI execution or pretend recapture. Keeps all native
actor messages and images, and all legitimate accepted frames for verification.
"""
import argparse,copy,json
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser()
    for name in ['source','prior','root','token-file']:ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in a.source.read_text().splitlines()]
    observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
    def load(obsid):
        p=observations[obsid]
        images=tuple(VisibleImage((a.source.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
        return PublicView(obsid,p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
    target=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='024-obs026')
    original=target['data']['text'];view=load('024-obs026')
    prior=json.loads(a.prior.read_text());verdict=prior['result']
    assert prior['manifest']['source_sha256']==digest(a.source.read_bytes())
    assert prior['manifest']['candidate_sha256']==digest(original.encode())
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    c=Controller(model.judge,Journal(a.root/'repair'),'post_only',Limits(full_completion_history=True,probe_current_targets=True,probe_target_alignment=True))
    for e in events:
        if e['seq']>=target['seq']:break
        if e['kind']=='decision_accepted':d=e['data'];c.remember(load(d['observation_id']),d['candidate'])
    manifest={'source':str(a.source),'source_sha256':digest(a.source.read_bytes()),'prior':str(a.prior),'prior_sha256':digest(a.prior.read_bytes()),
        'original_candidate_sha256':digest(original.encode()),'original_messages_sha256':digest(canonical(view.messages)),
        'defense_version':DEFENSE_VERSION,'no_new_capture_or_execution':True,'scope':'frozen terminal development, not task completion or a rate estimate'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    c.log.observation(view);c.log.append('frozen_prior_verdict',{'candidate':original,'verdict':verdict,'provenance':manifest})
    corrections=[];candidate=original;rounds=[];passed=False
    template=json.loads((Path(__file__).parent/'native-vwa-request.json').read_text())
    for index in range(c.limits.max_regenerations):
        bad=[x for x in verdict['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
        confirmed=[{'text':x['text'],'source_observation':view.observation_id,'evidence':x['evidence']}for x in verdict['claims']if x['kind']=='gui_fact'and x['status']=='supported'and any('image_index'in ev and ev['image_index']==0 for ev in x['evidence'])]
        corrections.extend(pending_claim_patch(candidate,x,view,confirmed)for x in bad)
        if verdict['action']['status']!='supported':corrections.append({'claim':'proposed_action','status':'relocalize_and_redecide','reason':verdict['action']['reason']})
        corrected=replace(view,messages=copy.deepcopy(view.messages)+[correction_message(corrections)])
        body=copy.deepcopy(template);body['messages']=corrected.messages
        c.log.append('actor_request',{'public':corrected.data(),'corrections':copy.deepcopy(corrections),'no_new_capture':True})
        candidate=model.actor(body);c.actor_calls+=1
        c.log.append('candidate',{'text':candidate,'observation_id':view.observation_id,'regeneration':index+1})
        payload=json.loads(candidate.split('<action>')[1].split('</action>')[0])
        proposal={'name':payload['type'],'payload':payload,'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
        verdict=c.inspect('verify',corrected,candidate,proposal)
        passed=verdict['action']['status']=='supported'and all(x['status']=='supported'for x in verdict['claims']if x['kind']in {'gui_fact','history_report'})
        probes={}
        if passed and proposal['name']=='click':
            probes['point']=c.check_current_point(view,proposal,verdict['action']['target_kind']);passed=probes['point']['agrees']
            if passed:probes['alignment']=c.check_target_alignment(view,candidate,proposal,probes['point']['point']);passed=probes['alignment']['agrees']
        if passed and proposal['name']=='type':probes['focus']=c.check_current_focus(view);passed=probes['focus']['agrees']
        if verdict['pure_wait']!=checked_wait(proposal):raise ValidationError('wait_parser_verifier_disagreement')
        row={'regeneration':index+1,'candidate':candidate,'proposal':proposal,'result':verdict,'passed':passed,'probes':probes}
        rounds.append(row);(a.root/'rounds.json').write_text(json.dumps(rounds,ensure_ascii=False,indent=2))
        if passed:break
    summary={'phase':'completed','passed':passed,'rounds':rounds,'calls':model.calls,'manifest':manifest,
        'actor_calls':c.actor_calls,'verifier_calls':c.verifier_calls,'semantic_mirage':None,'online_task_recovery':None}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
