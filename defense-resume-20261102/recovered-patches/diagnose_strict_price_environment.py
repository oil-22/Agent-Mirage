"""Preserve zero-call failed environment and inspect login load without credentials/actions."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote import remote
B=Path(__file__).resolve().parent;P=B/'strict-price-fullgui-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
stage=json.loads((P/'fullgui-staging-current.json').read_bytes());assert stage['environment_returncode']!=0
code=r'''
import base64,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
root=Path(ROOT);assert root.stat().st_uid==1015
proc=json.loads((root/'actual-process.json').read_bytes());p=Path('/proc')/str(proc['pid'])
assert not p.exists()or[p for p in(p/'cmdline').read_bytes().split(b'\0')if p]!=[x.encode()for x in proc['command']]
seal=json.loads((root/'terminal-sha256.json').read_bytes())
for n,h in seal.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
files={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()for f in root.rglob('*')if f.is_file()and'__pycache__'not in str(f)}
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for n in files:
  if not n.startswith('release/'):z.writestr(n,(root/n).read_bytes())
out=Path('/data/researcher/mirage-defense-pilot-20261023')/('strict-price-login-diagnostic-'+str(time.time_ns()));out.mkdir()
script=r"""
import hashlib,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent;pending={};events=[]
with sync_playwright()as p:
 browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':720})
 page.on('request',lambda r:pending.update({r.url:time.time()}))
 def finished(r):pending.pop(r.url,None)
 page.on('requestfinished',finished)
 def failed(r):events.append({'url':r.url,'failure':r.failure});finished(r)
 page.on('requestfailed',failed)
 start=time.time();error=None
 try:response=page.goto('http://192.0.2.10:29980/index.php?page=login',timeout=30000)
 except Exception as e:error=str(e)
 body=page.content();(root/'page.html').write_text(body);page.screenshot(path=str(root/'login.png'))
 row={'error':error,'elapsed':time.time()-start,'actual_url':page.url,'pending':pending,'failed':events,'HTML_sha256':hashlib.sha256(body.encode()).hexdigest(),'model_calls':0,'login_or_environment_actions':0,'diagnostic_only':True}
 (root/'result.json').write_text(json.dumps(row,indent=2));browser.close()
"""
(out/'probe.py').write_text(script)
env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
p=subprocess.run(['/data/researcher/vwa100-2026-10-09/venv/bin/python',str(out/'probe.py')],env=env,capture_output=True,text=True,timeout=55)
(out/'probe.log').write_text(p.stdout+p.stderr)
result=json.loads((out/'result.json').read_bytes())if(out/'result.json').exists()else {'returncode':p.returncode}
print(json.dumps({'failed_root':str(root),'failed_files':files,'zip':base64.b64encode(buf.getvalue()).decode(),'probe_root':str(out),'probe_result':result,'probe_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in out.iterdir()if f.is_file()}}))
'''
row=json.loads(remote('ROOT='+repr(stage['remote_preparation_root'])+'\n'+code,host='4090',timeout=65))
out=P/('environment-failure-preservation-'+str(time.time_ns()));out.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(row.pop('zip'))))as z:
    for n in z.namelist():(out/n).resolve().relative_to(out.resolve())
    z.extractall(out)
for n,h in row['failed_files'].items():
    if(out/n).exists():assert sha((out/n).read_bytes())==h,n
(out/'preservation.json').write_text(json.dumps(row,indent=2))
(P/'environment-failure-preservation-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'preservation.json').read_bytes()),'probe_root':row['probe_root'],'probe_result':row['probe_result'],'model_calls':0},indent=2))
print(json.dumps({'directory':str(out),'probe_root':row['probe_root'],'probe_result':row['probe_result']}))
