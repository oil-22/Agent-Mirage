"""Prepare outcome-free review while the current browser trajectory is still running."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time

from collect import HERE, control, latest_nf4_stage, manifest_for, read, save, sha
from consolidate_preterminal_review import verify_consolidation
from exact_review_reuse import load_packet, signature
from link import verify
from packets import fetch, make_packets
from review_cycle import review_pairs
from summarize import load_reviews


GUI = r'''
import os
assert os.getuid()==1015
p=Path(ROOT);assert sha(p/'manifest.json')==EXPECTED
attempt,=(p/'batch/runs'/RUN).glob('attempt-*')
ctl,head=journal(attempt/'controller/events.jsonl',live=True)
request={};n=None
for line in ctl:
    item=line['data']
    if line['kind']=='observation_started_timing':n=item['step']
    elif line['kind']=='actual_actor_request':
        assert n not in request;request[n]=item
submitted=unique(data(ctl,'actor_submit_timing'),lambda x:x['step'])
finished=unique(data(ctl,'observation_finished_timing'),lambda x:x['step'])
replies=unique(data(ctl,'actual_actor_reply'),lambda x:x['request_id'])
steps={n:{'request':r,'reply_sha256':replies[r['request_id']]['text_sha256'],
          'submitted_image_sha256':submitted[n]['image_sha256'],'capture_id':submitted[n]['capture_id']}
       for n,r in request.items() if n in finished and r['request_id'] in replies}
assert steps and list(steps)==list(range(1,max(steps)+1))
frames=defaultdict(list)
for f in data(ctl,'PRIVATE_capture_injection'):
    if f['step'] not in steps:continue
    if f['capture_id']==steps[f['step']]['capture_id']:
        assert f['delivered_sha256']==steps[f['step']]['submitted_image_sha256']
    frames[f['step']].append({k:f[k] for k in ('captured_sha256','delivered_sha256','raw_file','delivered_file')})
print(json.dumps({'attempt':str(attempt),'controller_head':head,'steps':steps,'frames':frames}))
'''
MAIN=r'''
import os
assert os.getuid()==1033
os.nice(10)
p=Path(ROOT);assert sha(p/'manifest.json')==EXPECTED
r=model_extract(p,Path(OUTPUT),read(p/'plan.json'))
out={str(v['step']):{'request_id':rid, **{k:v[k] for k in ('step','actual_forward','body_sha256','current_image_sha256',
     'reply_sha256','natural_EOS','messages_ordered','reply_text','wire_sha256','seal_sha256')}}
     for rid,v in r['requests'].items() if v['natural_EOS'] and v['step']<=THROUGH}
msg={k:r['public_legal_messages'][k] for v in out.values() for k in v['messages_ordered']}
print(json.dumps({'steps':out,'messages':msg,'primary_head':r['primary_chain_head']}))
'''


def export(a):
    verify(a.source);verify(a.prior)
    linked=read(a.source/'private-linked.json')
    assert read(a.prior/'condition-by-version.json')['ledger_seal_sha256']==sha(a.source/'seal.json')
    quality, candidates, _=load_reviews(linked,review_pairs(a.prior))
    stage = latest_nf4_stage()
    ptr, manifest, plan=manifest_for(stage)
    slot,=[v for v in plan if v['run_id']==a.run]
    assert all(r['slot']['run_id']!=a.run or r['evidence'] is None for r in linked['rows'])
    key=(HERE/'private-review-alias-key.bin').read_bytes()
    stamp=str(time.time_ns()); private=HERE/'preterminal-review-private'/stamp
    private.mkdir(parents=True,exist_ok=False); control.ROOT=private
    core=(HERE/'extract_on_host.py').read_text(encoding='utf-8')

    def run(host, code, **kw):
        params={'ROOT':manifest['package'+host],'OUTPUT':manifest['output3090'],'EXPECTED':ptr['manifest_sha256'],
                'RUN':a.run,**kw}
        mount="__name__='read_only_review'\n"+''.join(f'{k}={v!r}\n' for k,v in params.items())
        receipt=control.remote(host,mount+core+'\n'+code,'read-outcome-free-review-prefix',timeout=115)
        op=Path(receipt['operation']);verify(op)
        return receipt['result'],{'path':str(op),'seal_sha256':sha(op/'seal.json')}

    g, g_rec=run('4090',GUI)
    m, m_rec=run('3090',MAIN,OWNED_RUNS=[r['run_id'] for r in plan],TARGET_RUNS=[a.run],
                 OLD_PRIMARY_HEAD=None,OLD_FLASH_HEAD=None,THROUGH=max(map(int,g['steps'])))
    assert set(m['steps'])==set(g['steps'])
    steps=[]
    for n,w in m['steps'].items():
        gui=g['steps'][n]
        assert gui['request']['request_id']==w['request_id'] and gui['request']['body_sha256']==w['body_sha256']
        assert w['reply_sha256']==gui['reply_sha256'] and w['current_image_sha256']==gui['submitted_image_sha256']
        assert w['actual_forward'] and w['natural_EOS']
        steps.append({'step':int(n),'frames':g['frames'][n],'main':w,'actual_first_forward':True,'request':gui['request']})
    virtual={'public_legal_messages':m['messages'],'rows':[{'slot':slot,'evidence':{'version':'NF4',
        'stage_id':stage,'steps':steps,'gui_attempt':g['attempt'],'terminal_sha256':None}}]}
    packets,mapping,paths,_,stages,new=make_packets(virtual,key,quality,candidates)
    cas=fetch(private,paths,stages)
    dossier=HERE/'review-packets'/stamp
    display=dossier/'images'; display.mkdir(parents=True,exist_ok=False)
    for digest in paths:os.link(cas/(digest+'.png'),display/(digest+'.png'))
    save(dossier/'semantic-input.json',packets)
    save(dossier/'image-quality-input.json',{'images':sorted(new)})
    (dossier/'读包说明.md').write_text('只含实际有 EOS 的原回复、按序合法可见消息和未裁剪原图。'
        'current_image_sha256 为 null 表示这轮没有当前图，不代表历史中没有图。'
        '动作实施、条件、评分和终局均不可见；独立审查文本与像素。',encoding='utf-8')
    save(dossier/'seal.json',{'semantic-input.json':sha(dossier/'semantic-input.json'),
        'image-quality-input.json':sha(dossier/'image-quality-input.json'),'读包说明.md':sha(dossier/'读包说明.md'),
        'original_images':{d:'images/'+d+'.png' for d in sorted(paths)}})
    save(private/'prefix.json',{'review_input':str(dossier),'review_input_sha256':sha(dossier/'seal.json'),
        'alias_to_source':mapping,'held_and_delivered_image_sources':paths,
        'source_receipts':{'GUI':g_rec,'model':m_rec},'stage':stage,'run':a.run,
        'terminal_outcome_not_read_or_linked':True,'new_model_GUI_scorer_calls':0})
    save(private/'seal.json',{'prefix.json':sha(private/'prefix.json')})
    print(json.dumps({'review_input':str(dossier),'preterminal_private':str(private),
                      'eligible_natural_replies':len(steps),'new_independent_images':len(new)}))


def bind(a):
    for d in (a.source,a.prefix,*a.labels):verify(d)
    prefix=read(a.prefix/'prefix.json'); dossier=Path(prefix['review_input'])
    assert sha(dossier/'seal.json')==prefix['review_input_sha256']
    prefix_binding={'path':str(a.prefix.resolve()),'seal_sha256':sha(a.prefix/'seal.json')}
    for label in a.labels:
        if 'same_request_consolidation_proof_sha256' in read(label/'review.json'):
            verify_consolidation(label, {'preterminal_source':prefix_binding})
    public, _=load_packet(dossier)
    linked=read(a.source/'private-linked.json')
    row,=[r for r in linked['rows'] if r['slot']['run_id']==prefix['run']]
    assert row['status']=='verified_terminal' and row['stage_id']==prefix['stage']
    tape=row['evidence']; steps={s['step']:s for s in tape['steps']}
    assert all(v==linked['public_legal_messages'][k] for k,v in public['messages'].items())
    for rec in prefix['source_receipts'].values():
        op=Path(rec['path']); verify(op); assert sha(op/'seal.json')==rec['seal_sha256']
    for alias, items in public['packets'].items():
        identity=prefix['alias_to_source'][alias]
        assert identity['terminal_sha256'] is None and identity['version']==row['version']
        for turn in items:
            n=turn['decision']; s=steps[n]; m=s['main']; wire=identity['private_candidates'][str(n)]
            assert s['actual_first_forward'] and m['natural_EOS']
            assert wire=={'request_id':s['request']['request_id'],'wire_sha256':m['wire_sha256']}
            assert signature(turn)==(tuple(m['messages_ordered']),m['current_image_sha256'],m['reply_sha256'],m['reply_text'])
        identity['terminal_sha256']=tape['terminal_sha256']
    all_images={f[k] for s in steps.values() for f in s['frames'] for k in ('captured_sha256','delivered_sha256')}
    assert prefix['held_and_delivered_image_sources'].keys()<=all_images
    dst=HERE/'review-private'/str(time.time_ns()); dst.mkdir(exist_ok=False)
    save(dst/'PRIVATE-mapping.json',{'review_input':str(dossier),'review_input_sha256':prefix['review_input_sha256'],
        'alias_to_source':prefix['alias_to_source'],'held_and_delivered_image_sources':prefix['held_and_delivered_image_sources'],
        'ledger':str(a.source.resolve()),'ledger_sha256':sha(a.source/'seal.json'),
        'preterminal_source':prefix_binding})
    save(dst/'seal.json',{'PRIVATE-mapping.json':sha(dst/'PRIVATE-mapping.json')})
    coverage, candidates, _=load_reviews(linked,[(dst,v) for v in a.labels])
    assert set(candidates)=={(prefix['run'],t['decision']) for turns in public['packets'].values() for t in turns}
    assert set(coverage)==set(read(dossier/'image-quality-input.json')['images'])
    print(json.dumps({'review_private':str(dst),'labels':[str(v.resolve()) for v in a.labels],
                      'rebound_candidate_count':len(candidates),'original_image_labels':len(coverage)}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(required=True,dest='mode')
    q=s.add_parser('export');q.add_argument('run');q.add_argument('source',type=Path);q.add_argument('prior',type=Path)
    q=s.add_parser('bind');q.add_argument('source',type=Path);q.add_argument('prefix',type=Path);q.add_argument('labels',type=Path,nargs='+')
    a=p.parse_args()
    (export if a.mode=='export' else bind)(a)


if __name__=='__main__':main()
