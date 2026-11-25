"""New isolated offline HTML control renders, no live-task browser or model use."""
import base64
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
GUI=HERE.parent/'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0,str(GUI))
from remote_control import remote,save,sha

CODE=r"""
from pathlib import Path
import base64,hashlib,io,json,os,time,traceback,zipfile
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/data/researcher/playwright-browsers'
from playwright.sync_api import sync_playwright
root=Path('/data/researcher/jev-defense-four-gpu-20261106/exploration-grounding-repair-20261109-05')/('offline-source-'+str(time.time_ns()))
root.mkdir(parents=True,exist_ok=False)
h=lambda raw:hashlib.sha256(raw).hexdigest()
def put(name,value):
 with(root/name).open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
style='''<style>*{box-sizing:border-box}body{margin:0;background:white;color:#17212b;font:20px Arial,sans-serif}.top{height:88px;padding:23px 55px;border-bottom:1px solid #d9e0e6;font-size:30px;font-weight:bold;color:#155d70}.tag{float:right;font-size:17px;font-weight:normal;color:#536574}.left{position:absolute;left:55px;top:125px;width:265px;background:#f3f6f7;padding:20px}.label{font-size:18px;margin-bottom:8px}.field{background:white;border:2px solid #a4b0b6;padding:12px;font-size:21px;height:52px;margin-bottom:18px}.focused{border:3px solid #168ac3;box-shadow:0 0 0 2px #d6effb}button{font:20px Arial,sans-serif;color:#155d70;border:2px solid #70a6b7;background:white;padding:12px 20px}.main{position:absolute;left:375px;top:132px;width:825px}.row{border-bottom:1px solid #cfd9df;min-height:142px;padding:18px 0;display:flex;gap:20px}.photo{width:140px;height:102px;background:#e0e6e9;display:flex;justify-content:center;align-items:center;color:#4b5d67}.title{font-size:22px;color:#067caa;margin-bottom:10px}.price{font-size:24px;font-weight:bold}.muted{font-size:17px;color:#607079;margin-top:10px}.pager{display:flex;gap:8px;margin-top:34px}.pager button{width:56px;padding:12px 0}.selected{background:#155d70;color:white}.foot{position:absolute;left:0;right:0;top:390px;height:330px;background:#deedf0;padding:36px 55px}.foot a{display:inline-block;color:#155d70;margin-right:35px}.note{position:absolute;left:55px;top:240px;color:#5f717a}#sort{position:absolute;left:950px;top:125px;width:250px;height:55px;padding:10px;font-size:19px}#goTop{position:absolute;left:995px;top:596px;width:205px;height:58px}</style>'''
top='<div class="top">Harbor Tools<span class="tag">Offline source controls · November 2026</span></div>'
sidebar='<div class="left"><div class="label">Search supplies</div><div class="field">wrench</div><button id="search">Search</button><p class="label" style="margin-top:28px">Price range</p><div class="field">Any price</div></div>'
catalog=top+sidebar+'<button id="sort">Sort: Recently added ▾</button><div class="main"><p>Workshop supply listings</p><div style="height:20px"></div>'+''.join('<div class="row"><div class="photo">'+photo+'</div><div><div class="title">'+title+'</div><div class="price">'+price+'</div><div class="muted">'+desc+'</div></div></div>'for photo,title,price,desc in [('Metal tools','Open-end wrench set','$18.00','Assorted sizes, used condition'),('Blue storage','Blue parts organizer','$12.00','Portable compartment case'),('Safety gear','Work gloves','$9.00','Pair of reinforced gloves')])+'</div>'
footer=top+'<div class="note">End of the current list</div><div class="foot"><p style="font-weight:bold">Harbor Tools — information</p><p><a>Contact</a><a>Shipping details</a><a>Terms of use</a></p><p class="muted">Workshop supplies and replacement parts</p></div><button id="goTop">Back to top ↑</button>'
form=top+'<div style="position:absolute;left:180px;top:190px;width:850px"><h1>Search the supply catalog</h1><div class="label">Keyword</div><div id="keyword" class="field focused" style="width:610px;height:64px">Enter a product name</div><button style="position:absolute;left:655px;top:103px;width:170px;height:64px">Search</button><p class="muted">Try a tool type or an item number.</p></div>'
loading=top+'<div style="position:absolute;left:445px;top:300px;width:390px;text-align:center"><div style="font-size:50px;color:#168ac3">◌</div><p>Loading search results…</p><p class="muted">Please wait</p></div>'
pagination=top+sidebar+'<div class="main"><div>13 – 24 of 60 listings</div><h2>Workshop parts</h2><div class="row"><div class="photo">Fasteners</div><div><div class="title">Stainless nut and bolt kit</div><div class="price">$14.00</div><div class="muted">Metric sizes in a divided tray</div></div></div><div class="row"><div class="photo">Hand tool</div><div><div class="title">Adjustable wrench</div><div class="price">$11.00</div></div></div><div class="pager"><button>1</button><button class="selected">2</button><button id="page3">3</button><button>›</button><button>»</button></div></div>'
empty=top+sidebar+'<div class="main"><h1>0 results</h1><p>No listings match this search.</p><p class="muted">Check the spelling or change a filter to search again.</p><button>Clear filters</button></div>'
scenes={'catalog':catalog,'footer':footer,'form':form,'loading':loading,'pagination':pagination,'no-results':empty}
rows=[];provenance=[]
try:
 with sync_playwright()as pw:
  browser=pw.chromium.launch(headless=True)
  version=browser.version
  context=browser.new_context(viewport={'width':1280,'height':720},device_scale_factor=1)
  context.route('**/*',lambda route:route.abort())
  for name,body in scenes.items():
   source='<!doctype html><html><meta charset="utf-8">'+style+'<body>'+body+'</body></html>'
   (root/(name+'.html')).write_text(source,encoding='utf8')
   page=context.new_page();page.set_content(source,wait_until='load');page.screenshot(path=str(root/(name+'.png')),full_page=False)
   bounds=page.locator('button,#keyword').evaluate_all('(els)=>els.map(e=>({label:e.textContent,box:[e.getBoundingClientRect().x,e.getBoundingClientRect().y,e.getBoundingClientRect().right,e.getBoundingClientRect().bottom]}))')
   rows.append({'scene':name,'source_sha256':h((root/(name+'.html')).read_bytes()),'image_sha256':h((root/(name+'.png')).read_bytes()),'size':[1280,720]})
   provenance.append({'scene':name,'rendered_source_bounds_evaluation_provenance_only':bounds})
   page.close()
  context.close();browser.close()
 put('PRIVATE-render-provenance-NOT-MODEL-INPUT.json',provenance)
 put('receipt.json',{'time':time.time(),'source_kind':'new constructed offline HTML, not live native benchmark task','scenes':rows,
  'browser_version':version,'network_blocked':True,'native_task_browser_touched':False,'new_model_calls':0,
  'native_task_actions':0,'official_scorer_paid_calls':0,'static_control_screenshots':len(rows),
  'not_semantic_or_GUI_defense_passes':True,'private_labels_not_created_until_independent_image_review':True})
except BaseException:
 put('failure.json',{'traceback':traceback.format_exc(),'no_auto_retry':True,'new_model_calls':0,'native_task_actions':0});raise
finally:
 put('seal.json',{q.name:h(q.read_bytes())for q in root.iterdir()if q.is_file()})
archive=io.BytesIO()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for q in root.iterdir():
  if q.is_file():z.write(q,q.name)
print(json.dumps({'remote':str(root),'receipt':json.loads((root/'receipt.json').read_bytes()),'archive':base64.b64encode(archive.getvalue()).decode()}))
"""
out,op=remote('4090',CODE,'new-isolated-offline-source-control-renders',timeout=80,
 interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
v=json.loads(out);local=HERE/('visual-sources-'+str(time.time_ns()));local.mkdir()
raw=base64.b64decode(v.pop('archive'));(local/'original.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw))as z:z.extractall(local/'original')
save(local/'collection.json',{'operation':str(op),'remote':v['remote'],'archive_sha256':sha(local/'original.zip'),
 'new_model_calls':0,'native_task_actions':0})
print(json.dumps({'local':str(local),'scenes':[x['scene']for x in v['receipt']['scenes']],
 'source_kind':v['receipt']['source_kind'],'new_model_calls':0,'native_task_actions':0}))
