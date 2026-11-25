"""One real terminal-verification replay using all LEGAL accepted past frames.

No GUI/capture substitution, hidden image, injection ledger or evaluator input.
This is development evidence, not an online task result.
"""
import argparse,json,ast
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True)
    a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in a.source.read_text().splitlines()]
    observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
    def load(obsid):
        p=observations[obsid];images=tuple(VisibleImage((a.source.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
        return PublicView(obsid,p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
    target=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='024-obs026')
    view=load(target['data']['observation_id']);text=target['data']['text']
    payload=json.loads(text.split('<action>')[1].split('</action>')[0]);assert payload['type']=='stop'
    proposal={'name':'stop','payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    c=Controller(model.judge,Journal(a.root/'completion'),'post_only',Limits(full_completion_history=True))
    for event in events:
        if event['seq']>=target['seq']:break
        if event['kind']=='decision_accepted':
            d=event['data'];c.remember(load(d['observation_id']),d['candidate'])
    manifest={'source':str(a.source),'source_sha256':digest(a.source.read_bytes()),
        'candidate_sha256':digest(text.encode()),'legally_accepted_frames':len(c.reference_bank),
        'unique_frames':len({digest(r['image'].raw)for r in c.reference_bank}),
        'no_hidden_frames_or_evaluator':True,'scope':'one terminal developmental replay, not online completion'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    result=c.inspect('verify',view,text,proposal)
    bad=[x for x in result['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
    summary={'phase':'completed','passed':not bad and result['action']['status']=='supported',
        'verifier_calls':c.verifier_calls,'result':result,'manifest':manifest,
        'calls':model.calls,'defense_version':DEFENSE_VERSION,'semantic_mirage':None}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
