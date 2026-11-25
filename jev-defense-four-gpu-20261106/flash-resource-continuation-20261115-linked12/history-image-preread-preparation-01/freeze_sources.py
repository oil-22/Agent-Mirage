"""Copy ten selected, already terminal legal sources. No model or GUI calls."""
import base64
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))
from control import remote

SELECTED = [
    ('flash14-T089-stale_replace-baseline', 15),
    ('flash14-T114-clean-baseline', 16),
    ('flash14-T114-stale_replace-gate', 20),
    ('flash14-T125-clean-gate', 2),
    ('flash14-T058-clean-baseline', 1),
    ('flash14-T058-clean-baseline', 10),
    ('flash14-T094-clean-baseline', 1),
    ('flash14-T114-clean-baseline', 13),
    ('flash14-T125-stale_replace-gate', 1),
    ('flash14-T089-stale_replace-baseline', 16),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    assert not (HERE / 'frozen-sources-current.json').exists(), 'Do not repeat a completed freeze'
    roots = [PARENT / 'fresh-exited-parent-raw-1794674765901374600',
             PARENT / 'fresh-exited-continuation-raw-1794681237647187300']
    available = []
    for root in roots:
        seal = json.loads((root / 'seal.json').read_bytes())
        assert sha(root / '3090.json') == seal['3090.json']
        for row in json.loads((root / '3090.json').read_bytes())['sealed_main_requests']:
            available.append({'prior_raw_audit': str(root),
                              'prior_raw_audit_seal_sha256': sha(root / 'seal.json'), **row})
    rows = []
    for index, (run, decision) in enumerate(SELECTED, 1):
        matches = [r for r in available if r['run_id'] == run and r['decision'] == decision]
        assert len(matches) == 1, (run, decision, len(matches))
        rows.append({'case_id': 's%02d' % index, **matches[0]})
    code = 'ROWS=' + repr(rows) + '\n' + r'''
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
def digest(data):return hashlib.sha256(data).hexdigest()
files={};index=[]
for row in ROWS:
 d=Path(row['folder']);seal_data=(d/'seal.json').read_bytes();seal=json.loads(seal_data)
 assert digest(seal_data)==row['seal_sha256']
 names=['wire-request.bin','body.json','response.json','actual-generation.json','prepared.json','first-forward.json']
 for name in names:
  data=(d/name).read_bytes();assert digest(data)==seal[name],str(d/name)
  files[row['case_id']+'/source/'+name]=data
 files[row['case_id']+'/source/seal.json']=seal_data
 wire=json.loads(files[row['case_id']+'/source/wire-request.bin'])
 body=json.loads(files[row['case_id']+'/source/body.json'])
 response=json.loads(files[row['case_id']+'/source/response.json'])
 generation=json.loads(files[row['case_id']+'/source/actual-generation.json'])
 assert digest(files[row['case_id']+'/source/wire-request.bin'])==row['wire_sha256']
 assert wire['body']==body and wire['request_id']==row['request_id']
 assert wire['run_id']==row['run_id']and wire['decision_index']==row['decision']
 assert response['text']==row['native_text']and generation['natural_EOS']
 images=[]
 for mi,message in enumerate(body['messages']):
  if not isinstance(message['content'],list):continue
  for bi,block in enumerate(message['content']):
   if block.get('type')!='image_url':continue
   url=block['image_url']['url'];assert url.startswith('data:image/png;base64,')
   data=base64.b64decode(url.split(',',1)[1],validate=True)
   assert data.startswith(b'\x89PNG\r\n\x1a\n')
   h=digest(data);name='images/'+h+'.png';files[name]=data
   images.append({'message_index':mi,'block_index':bi,'sha256':h,'file':name})
 assert images[-1]['sha256']==row['current_image_sha256']
 index.append({**row,'source_body_file_sha256':digest(files[row['case_id']+'/source/body.json']),
  'raw_audit_body_SHA_is_canonical_object_not_file_SHA':True,'image_occurrences':images,
  'complete_legal_body_preserved':True,'new_model_GUI_calls':0})
files['PRIVATE-source-index.json']=json.dumps(index,ensure_ascii=False,indent=2).encode()
files['summary.json']=json.dumps({'time':time.time(),'cases':len(index),
 'unique_original_PNGs':sum(k.startswith('images/')for k in files),
 'image_occurrences_per_case':{r['case_id']:len(r['image_occurrences'])for r in index},
 'selection':'known-source nonblind development; no independent-task or efficacy claim',
 'new_model_GUI_calls':0,'prior_full_raw_audits_referenced_at_their_original_times':True},indent=2).encode()
files['seal.json']=json.dumps({k:digest(v)for k,v in files.items()},indent=2).encode()
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as z:
 for k,v in files.items():z.writestr(k,v)
archive=stream.getvalue()
print(json.dumps({'archive_base64':base64.b64encode(archive).decode(),
 'archive_sha256':digest(archive),'bytes':len(archive),'files':len(files),'new_model_GUI_calls':0}))
'''
    raw, operation = remote('3090', code, 'freeze-ten-distinct-history-preread-sources-readonly', timeout=55)
    value = json.loads(raw)
    archive = base64.b64decode(value.pop('archive_base64'), validate=True)
    assert hashlib.sha256(archive).hexdigest() == value['archive_sha256']
    dest = HERE / ('frozen-sources-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'export.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            target = dest / name
            assert target.resolve().is_relative_to(dest.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(z.read(name))
    for name, expected in json.loads((dest / 'seal.json').read_bytes()).items():
        assert sha(dest / name) == expected, name
    save(dest / 'export-receipt.json', {**value, 'operation': str(operation)})
    save(HERE / 'frozen-sources-current.json', {'root': str(dest), 'seal_sha256': sha(dest / 'seal.json')})
    print(json.dumps({'root': str(dest), **json.loads((dest / 'summary.json').read_bytes())}))


if __name__ == '__main__':
    main()
