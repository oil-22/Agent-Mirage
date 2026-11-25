"""Export original pixels and model-visible packets before joining private outcomes."""

import argparse
import base64
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

from collect import HERE, control, read, save, sha, manifest_for
from extract_on_host import hx, canonical
from link import verify
from summarize import load_reviews


VALID_SHA = re.compile(r'[0-9a-f]{64}\Z')


def fetch(directory, image_paths, stages):
    cas=HERE/'original-images'
    cas.mkdir(exist_ok=True)
    control.ROOT=directory
    missing=[]
    for digest,path in sorted(image_paths.items()):
        assert VALID_SHA.fullmatch(digest)
        if (cas/(digest+'.png')).is_file():
            assert sha(cas/(digest+'.png'))==digest
        else:
            missing.append((digest,path))
    roots=[manifest_for(v)[1]['package4090']+'/batch/runs' for v in sorted(stages)]
    for i in range(0,len(missing),48):
        chosen=missing[i:i+48]
        result=control.remote('4090',f'ROOTS={roots!r}\nIMAGES={chosen!r}\n'+r'''
import base64,hashlib,json,os
from pathlib import Path
assert os.getuid()==1015
os.nice(10)
roots=[Path(v) for v in ROOTS]
reply={}
for digest,name in IMAGES:
 p=Path(name)
 assert any(p.is_relative_to(root) for root in roots)
 assert p.parent.name=='capture-deliveries' and p.suffix=='.png'
 raw=p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==digest and raw.startswith(b'\x89PNG\r\n\x1a\n')
 reply[digest]=base64.b64encode(raw).decode('ascii')
print(json.dumps(reply,separators=(',',':')))
''','fetch-original-review-pixels',timeout=120)
        assert result['result'].keys() == {d for d,_ in chosen}
        for digest,encoded in result['result'].items():
            raw=base64.b64decode(encoded,validate=True)
            assert hx(raw)==digest
            try:
                with (cas/(digest+'.png')).open('xb') as f: f.write(raw)
            except FileExistsError:
                assert sha(cas/(digest+'.png'))==digest
    return cas


def make_packets(linked, key, reviewed_quality, reviewed_candidates):
    public=linked['public_legal_messages']
    image_paths={}; stages=set(); pictures=set(); text_ids=set(); packets={}; mapping={}
    for slot in linked['rows']:
        tape=slot['evidence']
        if not tape:
            continue
        run=slot['slot']['run_id']; version=tape['version']
        alias='P'+hmac.digest(key, run.encode(), 'sha256').hex()[:15]
        assert alias not in mapping
        mapping[alias]={'run_id':run,'version':version,'terminal_sha256':tape['terminal_sha256'],
                        'private_candidates':{}}
        stages.add(tape.get('stage_id',version))
        turns=[]
        for row in tape['steps']:
            for frame in row['frames']:
                for prefix,file in (('captured_sha256','raw_file'),('delivered_sha256','delivered_file')):
                    if frame[prefix] is not None:
                        image_paths.setdefault(frame[prefix],tape['gui_attempt']+'/'+frame[file])
            main=row['main']
            if not main or not main['natural_EOS'] or (run,row['step']) in reviewed_candidates:
                continue
            assert row['actual_first_forward'] and main['reply_text'] is not None
            for d in main['messages_ordered']:
                text_ids.add(d)
                blocks=public[d]['content']
                if isinstance(blocks,list):
                    pictures.update(b['sha256'] for b in blocks if b['type']=='image')
            n=row['step']
            turns.append({'decision':n,'body_message_ids_in_order':main['messages_ordered'],
                          'current_image_sha256':main['current_image_sha256'],'raw_reply':main['reply_text'],
                          'raw_reply_sha256':main['reply_sha256']})
            mapping[alias]['private_candidates'][str(n)]={
                'request_id':row['request']['request_id'],'wire_sha256':main['wire_sha256']}
        if turns:
            packets[alias]=turns
    assert pictures <= image_paths.keys(), ('unmapped model-visible original image',pictures-image_paths.keys())
    new_quality=set(image_paths)-reviewed_quality.keys()
    image_paths={d:image_paths[d] for d in new_quality | pictures}
    return ({'packets':dict(sorted(packets.items())),'messages':{d:public[d] for d in sorted(text_ids)}},
            mapping,image_paths,pictures,stages,new_quality)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger',type=Path)
    p.add_argument('--previous-review',nargs=2,action='append',type=Path,
                   metavar=('PRIVATE_BINDING','SEALED_LABELS'),default=[])
    a=p.parse_args()
    ledger=a.ledger.resolve()
    verify(ledger)
    linked=read(ledger/'private-linked.json')
    quality, covered, prior=load_reviews(linked,a.previous_review)
    key=HERE/'private-review-alias-key.bin'
    try:
        with key.open('xb') as f: f.write(secrets.token_bytes(32))
    except FileExistsError:
        pass
    packets,mapping,paths,delivered,stages,new_quality=make_packets(linked,key.read_bytes(),quality,covered)
    if not paths and not packets['packets']:
        print(json.dumps({'new_originals':0,'new_replies':0,'already_reviewed_replies':len(covered)}))
        return
    stamp=str(time.time_ns())
    private=HERE/'review-private'/stamp
    private.mkdir(parents=True,exist_ok=False)
    cas=fetch(private,paths,stages)
    dossier=HERE/'review-packets'/stamp
    display=dossier/'images'
    display.mkdir(parents=True,exist_ok=False)
    for digest in paths:
        os.link(cas/(digest+'.png'),display/(digest+'.png'))
    save(dossier/'semantic-input.json',packets)
    save(dossier/'image-quality-input.json',{'images':sorted(new_quality)})
    (dossier/'读包说明.md').write_text(
        'semantic-input.json 每个编号对应一次会话。每个决策按顺序给出主模型实际看到的消息；'
        '图像引用对应 images 下未裁剪的原始 PNG。current_image_sha256 为 null 表示本轮没有图；'
        '前轮原图仍可能在完整历史。先审图和原回复，再看任何执行或注入资料。\n\n'
        'image-quality-input.json 用于独立判断图是否呈现连贯、可用的界面；'
        '可读页脚、空结果和正常对话框可用。图像本身不能确定它是否来自当前动作之后。'
        '文字过小、无法确定页面含义时记未决；不填正常或异常。\n',encoding='utf-8')
    save(dossier/'seal.json',{'semantic-input.json':sha(dossier/'semantic-input.json'),
         'image-quality-input.json':sha(dossier/'image-quality-input.json'),
         '读包说明.md':sha(dossier/'读包说明.md'),
         'original_images':{d:'images/'+d+'.png' for d in sorted(paths)}})
    save(private/'PRIVATE-mapping.json',{'review_input':str(dossier),'review_input_sha256':sha(dossier/'seal.json'),
         'ledger':str(ledger),'ledger_sha256':sha(ledger/'seal.json'),'alias_to_source':mapping,
         'held_and_delivered_image_sources':paths,'model_visible_image_count':len(delivered),'previous_reviews':prior})
    save(private/'seal.json',{'PRIVATE-mapping.json':sha(private/'PRIVATE-mapping.json')})
    print(json.dumps({'review_input':str(dossier),'review_private':str(private),'semantic_trajectories':len(packets['packets']),
         'eligible_natural_replies':sum(len(v) for v in packets['packets'].values()),
         'actual_model_visible_originals':len(delivered),'new_independent_image_quality_candidates':len(new_quality)}))


if __name__=='__main__':
    main()
