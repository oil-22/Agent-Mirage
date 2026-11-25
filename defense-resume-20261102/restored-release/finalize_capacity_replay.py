"""Validate the already returned capacity reply; never sends a model request."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent
launch=json.loads((here/'v8-capacity-replay-launch.json').read_text())
service=json.loads((here/'v8-service-launch.json').read_text())
code='''import pathlib,json,hashlib,sys,base64,time
sys.path.insert(0,RELEASE)
from defense.core import PublicView,VisibleImage,decode_judge,validate_verdict
root=pathlib.Path(ROOT);assert not(root/'summary.json').exists()
log=pathlib.Path(LOG);assert "ImportError"in log.read_text()
progress=json.loads((root/'progress.json').read_text());assert progress['cases'][0]['passed']
case=root/'preserved_oom_exact_request';response=json.loads((case/'response.json').read_text())
request=(case/'request.json').read_bytes();body=json.loads(request);server=pathlib.Path(response['receipt'])
assert(server/'request.json').read_bytes()==request
v=body['view'];view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role'])for im in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
candidate=body['candidate'];payload=json.loads(candidate.split('<action>')[1].split('</action>')[0]);proposal={'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
value,_=decode_judge(response['verdict'],'verify');value=validate_verdict(value,view,candidate,proposal)
(case/'validated-verdict.json').write_text(json.dumps(value,indent=2))
row={'name':'preserved_oom_exact_request','passed':True,'http_success':True,'protocol_valid':True,'byte_identical_request':True,'request_sha256':hashlib.sha256(request).hexdigest(),'response_sha256':hashlib.sha256((case/'response.json').read_bytes()).hexdigest(),'new_receipt':response['receipt'],'input_tokens':response['input_tokens'],'output_tokens':response['output_tokens'],'seconds':response['seconds'],'semantic_acceptance':value['action']['status']=='supported'and all(c['status']=='supported'for c in value['claims']if c['kind']in {'gui_fact','history_report'})}
preserved={'time':time.time(),'source_script':SCRIPT,'source_script_sha256':hashlib.sha256(pathlib.Path(SCRIPT).read_bytes()).hexdigest(),'failure_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'reason':'Standalone script directory shadowed the immutable defense package during local validation; model inference had already returned successfully. Validation now binds explicit immutable release; no new inference.'}
(root/'validation-import-failure.json').write_text(json.dumps(preserved,indent=2))
summary={'phase':'completed','passed':True,'cases':progress['cases']+[row],'validation_repair':preserved,'scope':'Technical capacity and one frozen native placement control only; original qualified candidate remains semantically insufficient, not full task completion or independent Mirage labels'}
(root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
'''.replace('RELEASE',repr(service['release'])).replace('ROOT',repr(launch['root'])).replace('LOG',repr(launch['log'])).replace('SCRIPT',repr(launch['script']))
runner="import subprocess\np=subprocess.run(['/opt/whz/conda-envs/webmall-vlm/bin/python','-'],input="+repr(code)+",text=True,capture_output=True)\nassert p.returncode==0,p.stderr\nprint(p.stdout)"
data=json.loads(remote(runner,host='3090'))
(here/'v8-capacity-finalization.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
