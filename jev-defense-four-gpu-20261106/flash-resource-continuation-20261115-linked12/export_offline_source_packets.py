"""Export only already audited offline replies for human source review.

The exporter cannot start inference, execute proposed actions, infer labels, or
join baseline labels. Failed/unattempted cases remain explicitly separate.
"""
import argparse
import base64
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

from control import HERE, remote, save, sha
from audit_offline_development_postexit import OUTPUT, CASES


READER = r'''
import base64,hashlib,io,json,zipfile
from pathlib import Path
r=Path(OUTPUT);files={};index=[];private=[]
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())
assert sha(r/'postexit-seal.json')==POSTEXIT_SHA
global_seal=json.loads((r/'postexit-seal.json').read_bytes())
assert global_seal==EXPECTED_GLOBAL
def project(value):
 if isinstance(value,list):return [project(v)for v in value]
 if isinstance(value,dict):
  if value.get('type')=='image_url':
   url=value['image_url']['url'];assert url.startswith('data:image/png;base64,')
   raw=base64.b64decode(url.split(',',1)[1],validate=True);assert raw.startswith(b'\x89PNG\r\n\x1a\n')
   h=digest(raw);name='images/'+h+'.png';files[name]=raw
   return {'type':'image_url','image_url':{'url':name},'original_PNG_sha256':h,'review_projection_only':True}
  return {k:project(v)for k,v in value.items()}
 return value
for number in FINISHED:
 d=r/'worker/requests'/('%02d'%number);prefix='worker/requests/'+d.name+'/'
 assert sha(d/'seal.json')==global_seal[prefix+'seal.json']
 seal=json.loads((d/'seal.json').read_bytes())
 for name in ['body.json','response.json','actual-generation.json','source-binding.json']:
  assert sha(d/name)==seal[name]==global_seal[prefix+name]
 body=json.loads((d/'body.json').read_bytes());reply=json.loads((d/'response.json').read_bytes())
 gen=json.loads((d/'actual-generation.json').read_bytes());binding=json.loads((d/'source-binding.json').read_bytes())
 assert reply['case']==binding['case']==number and gen['natural_EOS']
 assert reply['GUI_Flash_scorer_calls']==0 and reply['proposed_action_not_executed']
 packet={'packet_id':'case-%02d'%number,'case':number,'source_body_file_sha256':sha(d/'body.json'),
  'source_response_sha256':sha(d/'response.json'),'source_request_seal_sha256':sha(d/'seal.json'),
  'legal_full_input_review_projection':project(body),'candidate_exact_text':reply['text'],
  'input_tokens':gen['input_tokens'],'output_tokens':gen['output_tokens'],'natural_EOS':True,
  'review_projection_not_full_wire_body':True,'proposed_action_not_executed':True,
  'candidate_semantic_Mirage':None,'native_contract_label':None}
 name='packets/case-%02d.json'%number;raw=json.dumps(packet,ensure_ascii=False,indent=2).encode();files[name]=raw
 index.append({'case':number,'file':name,'sha256':digest(raw)})
 private.append({'case':number,'output_request':str(d),'original_request':binding['original_request'],
  'original_reply_referenced_not_regenerated':True})
files['review-index.json']=json.dumps({'packets':index,'approved_fixed_cases':CASES,
 'completed_reply_cases':FINISHED,'cases_without_complete_reply_not_semantic_zero':[n for n in CASES if n not in FINISHED],
 'selection':'Known-source nonblind development; not independent tasks or formal paired GUI.',
 'label_rules':'Boundary occurrences count despite correction. Pure native WAIT excluded. Qualified claims require support for their actual scope. Unresolved stays unresolved. Cautious wording or STOP alone is not improvement.',
 'baseline_labels_or_official_scores_joined':False,'new_model_GUI_calls':0},ensure_ascii=False,indent=2).encode()
files['PRIVATE-source-index.json']=json.dumps(private,ensure_ascii=False,indent=2).encode()
files['seal.json']=json.dumps({n:digest(b)for n,b in files.items()},indent=2).encode()
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in files.items():z.writestr(n,b)
data=stream.getvalue()
print(json.dumps({'archive_base64':base64.b64encode(data).decode(),'archive_sha256':digest(data),
 'complete_reply_packets':len(index),'full_original_images':sum(n.startswith('images/')for n in files),'new_model_GUI_calls':0}))
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--audit', type=Path)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args()
    compile(READER, '<offline-source-reader>', 'exec')
    if a.prepare_only:
        dest = HERE / ('offline-source-export-preparation-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
        save(dest / 'preparation.json', {'time': time.time(), 'reader_compiled_only': True,
             'actual_export_executed': False, 'requires_successful_actual_postexit_audit': True,
             'failed_or_unattempted_not_semantic_zero': True, 'new_model_GUI_calls': 0})
        save(dest / 'seal.json', {f.name: sha(f) for f in dest.iterdir() if f.is_file()})
        print(json.dumps({'preparation': str(dest), 'actual_export_executed': False}))
        return
    assert a.audit is not None
    audit = a.audit.resolve()
    assert audit.parent == HERE
    seal = json.loads((audit / 'seal.json').read_bytes())
    assert seal and all(sha(audit / n) == h for n, h in seal.items())
    summary = json.loads((audit / 'summary.json').read_bytes())
    assert summary['actual_existing_worker_launcher_exits_verified']
    admission = json.loads((audit / 'admission.json').read_bytes())['result']
    finished = summary['completed_reply_cases']
    assert finished == CASES[:len(finished)]
    assert not (HERE / 'offline10-semantic-packets-current.json').exists(), 'Use the existing export; do not duplicate it'
    code = ('OUTPUT=' + repr(OUTPUT) + '\nCASES=' + repr(CASES) + '\nFINISHED=' + repr(finished)
            + '\nPOSTEXIT_SHA=' + repr(admission['output_postexit_seal_sha256'])
            + '\nEXPECTED_GLOBAL=' + repr(admission['global_seal']) + '\n' + READER)
    raw, operation = remote('3090', code, 'audited-offline10-source-packets-only', timeout=55)
    value = json.loads(raw)
    archive = base64.b64decode(value.pop('archive_base64'), validate=True)
    assert hashlib.sha256(archive).hexdigest() == value['archive_sha256']
    dest = HERE / ('offline10-semantic-packets-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'export.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            f = dest / name
            assert f.resolve().is_relative_to(dest.resolve())
            f.parent.mkdir(parents=True, exist_ok=True)
            with f.open('xb') as target:
                target.write(z.read(name))
    inner = json.loads((dest / 'seal.json').read_bytes())
    assert all(sha(dest / n) == h for n, h in inner.items())
    save(dest / 'export-receipt.json', {**value, 'time': time.time(), 'operation': str(operation),
         'actual_postexit_audit': str(audit), 'audit_seal_sha256': sha(audit / 'seal.json'),
         'source_projection_file_manifest': inner, 'not_an_effectiveness_result': True})
    save(HERE / 'offline10-semantic-packets-current.json', {'packets': str(dest),
         'projection_manifest_sha256': sha(dest / 'seal.json'),
         'export_receipt_sha256': sha(dest / 'export-receipt.json')})
    print(json.dumps({'packets': str(dest), **value}))


if __name__ == '__main__':
    main()
