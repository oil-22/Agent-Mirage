"""Read original archived image assets over SSH, without model or GUI calls.

The earlier discovery only understood inline data URLs; it found zero because
these exports use archive-image references. Linked02 found a missing propagation export; this attempt reads only existing campaign original artifacts. Preserve it and resolve references
in a distinct read-only attempt. Source exports are not declared full wire logs.
"""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
OUT = ROOT / 'source-discovery-linked03'
OUT.mkdir(exist_ok=False)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()

spec = importlib.util.spec_from_file_location('readonly_remote', WORKSPACE / 'defense-resume-20261102/restored-release/remote.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
plans = ['attention-audit-20261031/campaign/plan.json']
selections, seen = [], set()
for name in plans:
    raw = (WORKSPACE / name).read_bytes()
    for case in json.loads(raw)['cases']:
        if case['condition'] not in ('current_control', 'original') or case.get('history') != 'full':
            continue
        images = [(mi, bi, block['image_url']['url'])
            for mi, message in enumerate(case['request']['messages']) if isinstance(message.get('content'), list)
            for bi, block in enumerate(message['content']) if block.get('type') == 'image_url']
        if not images:
            continue
        mi, bi, url = images[-1]
        assert url.startswith('archive-image://sha256/')
        digest = url.rsplit('/', 1)[1]
        if digest in seen:
            continue
        seen.add(digest)
        selections.append({'id': f'S{len(selections)+1:02d}', 'image_sha256': digest,
            'source_plan': name, 'source_plan_sha256': sha(raw),
            'source_case_id': case['id'], 'condition': case['condition'],
            'task': case['task'], 'app': case['app'], 'step': case['step'],
            'image_message_index': mi, 'image_content_block_index': bi,
            'original_source_artifact': case.get('source_archive_path', case.get('source_artifact')),
            'original_source_artifact_sha256': case.get('source_archived_json_sha256', case.get('source_artifact_sha256'))})
code = '''import base64,gzip,hashlib,json,pathlib
root=pathlib.Path('/data/researcher/attention-audit-20261031')
selections=SELECTIONS
links={}
for line in gzip.open(root/'members.jsonl.gz','rt'):
 n,size,typ,link=json.loads(line)
 if '/_embedded-input-images/' in n and typ=='1': links[pathlib.PurePosixPath(n).stem]=link
out=[]
for item in selections:
 h=item['image_sha256']; matches=[]
 for folder in ['campaign/assets','source-campaign/assets','inputs/mirage-trace/_shared/input-images/_embedded-input-images']:
  d=root/folder
  if d.is_dir(): matches.extend(d.glob('*/'+h+'.*'))
 if h in links and (root/'inputs'/links[h]).is_file():matches.append(root/'inputs'/links[h])
 matches=sorted(set(p.resolve() for p in matches))
 assert matches, h
 raw=matches[0].read_bytes(); assert hashlib.sha256(raw).hexdigest()==h
 source=root/'inputs'/item['original_source_artifact']
 assert source.is_file(),str(source)
 source_raw=source.read_bytes(); assert hashlib.sha256(source_raw).hexdigest()==item['original_source_artifact_sha256']
 out.append({'id':item['id'],'image_remote':str(matches[0]),'image_base64':base64.b64encode(raw).decode(),
  'source_remote':str(source),'source_base64':base64.b64encode(source_raw).decode()})
print(json.dumps(out,separators=(',',':')))
'''.replace('SELECTIONS', repr(selections))
(OUT / 'remote-readonly.py').write_text(code, encoding='utf-8')
reply = module.remote(code, timeout=180, host='4090')
records = []
for row, selected in zip(json.loads(reply), selections):
    assert row['id'] == selected['id']
    image_raw, source_raw = base64.b64decode(row['image_base64']), base64.b64decode(row['source_base64'])
    assert sha(image_raw) == selected['image_sha256']
    assert sha(source_raw) == selected['original_source_artifact_sha256']
    image = Image.open(io.BytesIO(image_raw)); image.load()
    (OUT / (selected['id'] + '.png')).write_bytes(image_raw)
    (OUT / (selected['id'] + '-source.json')).write_bytes(source_raw)
    records.append(dict(selected, image_path=selected['id']+'.png', source_path=selected['id']+'-source.json',
        image_size=list(image.size), image_format=image.format, image_remote=row['image_remote'],
        source_remote=row['source_remote'], original_source_artifact_reverified=True,
        source_export_not_claimed_full_wire=True, history_or_prediction_used_as_visual_gold=False))
(OUT / 'inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for start in range(0, len(records), 12):
    rows = records[start:start+12]
    sheet = Image.new('RGB', (1200, ((len(rows)+2)//3)*257), '#dddddd')
    draw = ImageDraw.Draw(sheet)
    for j, row in enumerate(rows):
        im=Image.open(OUT/row['image_path']).convert('RGB'); im.thumbnail((396,223))
        x,y=(j%3)*400,(j//3)*257
        sheet.paste(im,(x,y+30)); draw.text((x+4,y+4),row['id']+' '+row['app']+' '+str(row['step']),fill='black')
    sheet.save(OUT / f'contact-{start//12+1:02d}.png')
receipt={'status':'source_assets_copied_readonly_not_labels_or_new_predictions', 'images':len(records),
    'previous_zero_result_source_sha256':sha((ROOT/'inspect_archived_image_sources.py').read_bytes()),
    'prior_missing_source_failure_seal_sha256':sha((ROOT/'source-discovery-linked02/failure-seal.json').read_bytes()),
    'previous_zero_result_inventory_sha256':sha((ROOT/'source-discovery-01/inventory.json').read_bytes()),
    'repair':'source_scope_limited_to_existing_campaign_original_artifacts_after_missing_propagation_export' , 'source_sha256':sha(Path(__file__).read_bytes()),
    'remote_reply_sha256':sha(reply.encode()), 'new_model_GPU_GUI_scorer_calls':0}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(OUT/'seal.json').write_text(json.dumps({p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':receipt['status'],'images':len(records),'receipt_sha256':sha((OUT/'receipt.json').read_bytes())}))
