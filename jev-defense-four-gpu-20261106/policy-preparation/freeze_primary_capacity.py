"""Freeze one original full w08 judge input for NEW layout capacity only, no inference."""
import base64
import json
from pathlib import Path

from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, canonical, digest

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parents[1]/'defense-resume-20261102/package-retry2/restored-inputs'


class Captured(Exception): pass


def main():
    root=BASE/'primary-capacity-frozen-01';root.mkdir(exist_ok=False)
    packet_raw=(SOURCE/'inputs/w08.json').read_bytes();packet=json.loads(packet_raw);public=packet['public']
    images=[]
    for item in public['images']:
        raw=(SOURCE/'images'/(item['sha256']+'.png')).read_bytes()
        assert digest(raw)==item['sha256'];images.append(VisibleImage(raw,item['role']))
    view=PublicView(public['observation_id'],public['messages'],tuple(images),public['recent_action'],public['execution_feedback'],public['observed_at'])
    assert canonical(view.data())==canonical(public)
    bodies=[]
    def capture(system, actual_view, candidate):
        assert canonical(actual_view.data())==canonical(public)
        wire=actual_view.data()
        wire['images']=[{'raw_base64':base64.b64encode(im.raw).decode(),'role':im.role}for im in actual_view.images]
        bodies.append({'operation':'judge','system':system,'view':wire,'candidate':candidate})
        raise Captured()
    ctl=Controller(capture,Journal(root/'source-capture-journal'),'joint',
        Limits(max_verifier_calls=1,max_format_retries=0,probe_history_reports=True),sleeper=lambda _:None)
    try:ctl.inspect('verify',view,packet['candidate'],packet['proposal'])
    except Captured:pass
    assert len(bodies)==1
    body=bodies[0]
    (root/'request.json').write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf8')
    receipt={'scope':'NEW four-GPU layout engineering capacity, known old source, not new semantic trial',
        'source_packet_sha256':digest(packet_raw),'source_public_sha256':digest(canonical(public)),
        'source_candidate_sha256':digest(canonical(packet['candidate'])),
        'message_count':len(public['messages']),'image_count':len(images),
        'images':[{'sha256':digest(im.raw),'role':im.role}for im in images],
        'request_canonical_sha256':digest(canonical(body)),
        'system_sha256':digest(body['system'].encode()),
        'max_primary_judge_calls':1,'max_output_tokens':4096,'max_format_retries':0,
        'original_generation_backend':'BF16/SDPA native current source, original judge grammar',
        'full_history_unchanged':True,'full_images_unchanged':True,
        'new_flash_predictions_in_system':False,'not_joint_policy_proof':True,
        'actor_calls':0,'GUI_actions':0,'paid_API_calls':0,'model_calls_made_while_freezing':0,
        'automatic_retry':False,'semantic_pass':None}
    (root/'plan.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    (root/'server-admission.json').write_text(json.dumps({'mode':'capacity_preflight','max_new_calls':1,
        'requests':[{'case_id':'w08-full-input-new-layout-capacity','fingerprint':digest(canonical(body))}]},indent=2),encoding='utf8')
    (root/'seal.json').write_text(json.dumps({str(p.relative_to(root)).replace('\\','/'):digest(p.read_bytes())
        for p in root.rglob('*')if p.is_file()},indent=2),encoding='utf8')
    print(json.dumps({'root':str(root),'request_fingerprint':receipt['request_canonical_sha256'],
                      'messages':len(public['messages']),'images':len(images),'max_new_judge_calls':1}))


if __name__=='__main__':main()
