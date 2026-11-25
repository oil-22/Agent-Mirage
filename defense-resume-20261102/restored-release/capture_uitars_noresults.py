"""Fresh read-only no-results UI development source; never resets the site or runs a trial."""
import base64,hashlib,json,time
from pathlib import Path
from remote import remote
base=Path(__file__).resolve().parent;dest=base/'uitars-verifier-preparation'/('noresults-source-'+str(time.time_ns()));dest.mkdir()
browser_code=r'''
import pathlib,json,time,hashlib
from playwright.sync_api import sync_playwright
r=pathlib.Path(ROOT);r.mkdir();query='MirageNoResultsSourceControl'+str(time.time_ns())
url='http://192.0.2.10:29980/index.php?page=search&sPattern='+query
with sync_playwright()as pw:
 browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1280,'height':720})
 context.tracing.start(screenshots=True,snapshots=False,sources=False);page=context.new_page();response=page.goto(url,wait_until='networkidle',timeout=25000)
 raw=page.screenshot();(r/'current.png').write_bytes(raw)
 record={'time':time.time(),'query':query,'requested_url':url,'actual_url':page.url,'http_status':response.status,'image_sha256':hashlib.sha256(raw).hexdigest(),'viewport':[1280,720],'scope':'Fresh isolated source capture only; read-only GET search, no original experiment task/seed/history/result changed. No evaluator or DOM content sent to verifier.'}
 (r/'source.json').write_text(json.dumps(record,indent=2));context.tracing.stop(path=str(r/'browser-trace.zip'));browser.close()
print(json.dumps(record))
'''
code=r'''
import pathlib,subprocess,json,time,os,base64,hashlib
assert os.getuid()==1015
c=json.loads(subprocess.check_output(['docker','inspect','qwen27_vwa_classifieds']).decode())[0]
assert c['Id']=='de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd'and c['State']['Running']and'whz-qwen27-vwa'in json.dumps(c['Config'].get('Labels'))
root=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023')/('uitars-noresults-source-'+str(time.time_ns()))
source='ROOT='+repr(str(root))+'\n'+BROWSER
script=root.with_suffix('.py');script.write_text(source)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',OMP_NUM_THREADS='2')
p=subprocess.run(['/data/researcher/vwa100-2026-10-09/venv/bin/python',str(script)],capture_output=True,text=True,env=env,timeout=45)
if not root.exists():root.mkdir()
(root/'capture-stdout.log').write_text(p.stdout);(root/'capture-stderr.log').write_text(p.stderr)
record={'root':str(root),'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
if(root/'current.png').exists():record['image_base64']=base64.b64encode((root/'current.png').read_bytes()).decode();record['source']=json.loads((root/'source.json').read_bytes())
print(json.dumps(record))
'''
result=json.loads(remote('BROWSER='+repr(browser_code)+'\n'+code,host='4090',timeout=60))
if'image_base64'in result:
 raw=base64.b64decode(result.pop('image_base64'));assert hashlib.sha256(raw).hexdigest()==result['source']['image_sha256'];(dest/'current.png').write_bytes(raw)
(dest/'capture.json').write_text(json.dumps(result,indent=2),encoding='utf8')
marker={'folder':str(dest),'sha256':hashlib.sha256((dest/'capture.json').read_bytes()).hexdigest(),'returncode':result['returncode'],'reviewed':False}
(base/'uitars-verifier-preparation/noresults-source-current.json').write_text(json.dumps(marker,indent=2),encoding='utf8')
print(json.dumps(marker));print(json.dumps(result))
