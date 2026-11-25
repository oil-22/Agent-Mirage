"""Additional fresh footer-only source; keeps the first source collection immutable."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
assert not(PREP/'fresh-footer-current.json').exists()
browser=r'''
import hashlib,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
r=Path(ROOT);rows=[];actions=[];(r/'images').mkdir()
with sync_playwright()as pw:
 browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1280,'height':720});page=context.new_page();context.tracing.start(screenshots=True,snapshots=False,sources=False)
 response=page.goto('http://192.0.2.10:29980/index.php?page=search&sPattern=basketball&iPage=5',wait_until='networkidle',timeout=30000)
 for i in range(4):
  if i:page.mouse.wheel(0,650);actions.append({'native_payload':{'type':'scroll','direction':'down','source_scroll_pixels':650},'time':time.time(),'actor':'scripted source collection'});page.wait_for_timeout(500)
  raw=page.screenshot();h=hashlib.sha256(raw).hexdigest();(r/'images'/(h+'.png')).write_bytes(raw)
  rows.append({'id':'page5-source-%d'%i,'observation_id':'fresh-page5-'+str(time.time_ns()),'image_sha256':h,'observed_at':time.time(),'viewport':[1280,720],'url':page.url,'http_status':response.status,'scripted_source_attempts':list(actions),'recent_action':json.dumps(actions[-1]['native_payload'])if actions else '', 'execution_feedback':json.dumps({'source_script_returned':True,'result_state':'current screenshot required; not task success confirmation'})})
 context.tracing.stop(path=str(r/'browser-trace.zip'));browser.close()
(r/'source-summary.json').write_text(json.dumps({'rows':rows,'source':'read-only native searchURL page5 parameter, no answers/DOM/AX/evaluation. No model output or formal task trial.','model_calls':0,'site_reset':False},indent=2))
'''
code=r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/mirage-defense-pilot-20261023');lock=(b/'scoped-observability-source.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=b/'scoped-observability-footer-source-active-20261028.json';assert not active.exists()
c=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds'],text=True))[0];assert c['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'and c['State']['Running']and c['Config']['Labels']['owner']=='whz-qwen27-vwa'
r=b/('scoped-observability-fresh-footer-'+str(time.time_ns()));r.mkdir()
with active.open('x')as f:json.dump({'root':str(r),'model_calls':0},f)
(r/'capture.py').write_text('ROOT='+repr(str(r))+'\n'+BROWSER)
p=subprocess.run(['/data/researcher/vwa100-2026-10-09/venv/bin/python',str(r/'capture.py')],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers'),capture_output=True,text=True,timeout=60)
(r/'stdout.log').write_text(p.stdout);(r/'stderr.log').write_text(p.stderr)
files={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in r.rglob('*')if f.is_file()};(r/'source-seal.json').write_text(json.dumps(files,indent=2));buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in list(files)+['source-seal.json']:z.writestr(n,(r/n).read_bytes())
print(json.dumps({'root':str(r),'returncode':p.returncode,'sha256':files,'zip':base64.b64encode(buf.getvalue()).decode(),'model_calls':0}))
'''
row=json.loads(remote('BROWSER='+repr(browser)+'\n'+code,host='4090',timeout=80));out=PREP/('fresh-footer-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
    for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
    z.extractall(out)
for n,h in row['sha256'].items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h
row['directory']=str(out);(out/'collection-receipt.json').write_text(json.dumps(row,indent=2));(PREP/'fresh-footer-current.json').write_text(json.dumps(row,indent=2));print(json.dumps({k:v for k,v in row.items()if k!='sha256'}));assert row['returncode']==0
