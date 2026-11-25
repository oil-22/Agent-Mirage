import copy,gzip,hashlib,json,pathlib,shutil
root=pathlib.Path('/data/researcher/attention-audit-20261031');base=root/'propagation/attention-experiment/Qwen3.8-27B';dest=root/'source-campaign';dest.mkdir(exist_ok=True)
assets=root/'inputs/mirage-trace/_shared/input-images/_embedded-input-images';outassets=dest/'assets';outassets.mkdir(exist_ok=True)
def store(h):
    matches=list(assets.glob('*/'+h+'.*'));assert len(matches)==1,(h,matches)
    p=matches[0];assert hashlib.sha256(p.read_bytes()).hexdigest()==h
    target=outassets/h[:2]/p.name;target.parent.mkdir(exist_ok=True)
    if not target.exists():shutil.copyfile(p,target)
    return 'archive-image://sha256/'+h
raw=[]
for step in [10,20,30,40,44,45,46]:
    p=next(base.glob(f'WebMall*/qwen27-propagation-20261020/evidence/webmall/requests/{step:03d}.json'));req=json.loads(p.read_text())
    for msg in req['messages']:
        if isinstance(msg['content'],list):
            for item in msg['content']:
                if item.get('type')=='image_url':item['image_url']['url']=store(item['image_url']['url'].rsplit('/',1)[1])
    raw.append({'id':f'WM-{step:02d}','task':'WebMall-Find-Task8','app':'WebMall','step':step,'source_step':9,'source_assistant_index':9,'history':'full','stage':'followup','source_kind':'embedded_step_block','request':req,'source_artifact':str(p.relative_to(root)),'source_artifact_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for step in [11,20,35,50]:
    p=next(base.glob(f'VisualWebArena*/qwen27-propagation-20261020/results/vwa_s{step:02d}/*/input.json'));meta=json.loads(p.read_text())
    for image in meta['images']:store(image['sha256'])
    raw.append({'id':f'VWA-{step:02d}','task':'VWA-classifieds_177','app':'VisualWebArena','step':step,'source_step':10,'history':'full','stage':'followup','source_kind':'native_prompt_reconstruction','metadata':meta,'source_artifact':str(p.relative_to(root)),'source_artifact_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(dest/'raw.json').write_text(json.dumps(raw,ensure_ascii=False))
print('raw sources',len(raw),'assets',len(list(outassets.glob('*/*'))))
