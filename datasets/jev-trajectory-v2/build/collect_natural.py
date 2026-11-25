"""Read existing Classifieds captures and a minimal receipt extract from 4090. No experiment is run.

Run from the original project checkout. Original model text, DOM, history and evaluation answers are not exported.
"""
from pathlib import Path
import io,json,hashlib,re,subprocess,tarfile

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'.tmp/jev-trajectory-v2-review'
def sha(b):return hashlib.sha256(b).hexdigest()

SERVER=r'''
from pathlib import Path
from urllib.parse import urlsplit
import os,re,json,hashlib,zipfile,collections,tarfile,io,sys
os.nice(8)
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p):return json.loads(p.read_bytes())
def route(u):
    v=urlsplit(u or '')
    if v.hostname in ('localhost','127.0.0.1','192.0.2.10') and v.port and v.port%1000==980:
        return v.path+('?'+v.query if v.query else '')
def primitive(t):
    api=t.get('apiName');p=t.get('params',{})
    if api=='Mouse.click':return ('click',[p.get('x'),p.get('y')])
    if api=='Page.go_back':return ('back',None)
    if api=='Keyboard.type':return ('type',p.get('text'))
    if api=='Keyboard.press':return ('press',p.get('key'))
    e=p.get('expression','')
    if api=='Page.evaluate' and '.scrollTop =' in e and 'window.innerHeight' in e:
        for k,d in [('+','down'),('-','up')]:
            if k+' window.innerHeight' in e:return ('scroll',d)
def matches(a,p):
    k,v=p
    if a.get('type')!=k:return False
    if k=='click':
        try:return abs(float(a['x'])*1.28-v[0])<.05 and abs(float(a['y'])*.72-v[1])<.05
        except (TypeError,ValueError):return False
    if k=='press':return a['key'].lower().replace('ctrl','control')==v.lower().replace('ctrl','control')
    return k=='back' or a['text' if k=='type' else 'direction']==v
def parse_trace(p,actions):
    with zipfile.ZipFile(p) as z:data=z.read('trace.trace')
    bef={};aft={};snap={};calls=[];shots=[]
    for l in data.splitlines():
        t=json.loads(l);id=t.get('callId');typ=t.get('type')
        if typ=='before':
            bef[id]=t
            if primitive(t):calls.append(id)
            if t.get('apiName')=='Page.screenshot' and t.get('params',{}).get('caret')=='hide':shots.append(id)
        elif typ=='after':aft[id]=t
        elif typ=='frame-snapshot':
            s=t['snapshot']
            if s['isMainFrame']:snap[s['snapshotName']]=route(s.get('frameUrl'))
    ordered=[(i,a) for i,a in sorted(actions.items()) if a['type'] in ('type','press','scroll','click','back')]
    if len(ordered)!=len(calls) or any(not matches(a,primitive(bef[id])) for (i,a),id in zip(ordered,calls)):return {},sha(data)
    tm=lambda id:bef[id]['startTime']
    def shotroute(id):return snap.get('before@'+id) or snap.get('after@'+id)
    def yoffset(id):
        b=[b for b,t in bef.items() if tm(b)<tm(id) and t.get('apiName')=='Page.evaluate' and t.get('params',{}).get('expression')=='window.pageYOffset' and b in aft]
        if b:return aft[max(b,key=tm)].get('result',{}).get('value')
    result={}
    for (i,a),id in zip(ordered,calls):
        before=[s for s in shots if tm(s)<tm(id)];after=[s for s in shots if tm(s)>tm(id)]
        if not before or not after or id not in aft or aft[id].get('error'):continue
        x=before[-1];y=after[0];b=shotroute(x);e=shotroute(y)
        if not b or not e or (snap.get('before@'+id) and snap['before@'+id]!=b):continue
        result[i]=dict(primitive=bef[id]['apiName'],call_id=id,before_screenshot_call=x,after_screenshot_call=y,
                       before_route=b,after_route=e,scroll_y_before=yoffset(x),scroll_y_after=yoffset(y))
    return result,sha(data)
rawpics={}; records=[];probes=[];skip=collections.Counter()
roots=[Path('/data/researcher/context-length-pilot-20261117/quant-nf4-02'),Path('/data/researcher/context-length-natural-20261117/batch01'),Path('/data/researcher/context-length-natural-20261117/scale100'),Path('/data/researcher/context-length-natural-20261117/scale100-resume01')]
dirs={}
for root in roots:
    for p in sorted((root/'gui-output').glob('T*/clean')):
        if re.fullmatch(r'T[0-9]{3}',p.parent.name) and (p/'terminal.json').is_file():dirs[p.parent.name]=p
for task,p in sorted(dirs.items()):
    if not (p/'browser_trace.zip').is_file():continue
    actions={};frames={};rs={}
    for ap in sorted(p.glob('[0-9][0-9][0-9]-action.json')):
        i=int(ap.name[:3]);obj=js(ap);a=obj['payload'];actions[i]=a
        rp=p/(ap.name[:3]+'-response.json')
        if not rp.is_file():continue
        rb=rp.read_bytes();r=json.loads(rb);rs[i]=r;images=r.get('images',[])
        if not images or not r.get('receipt') or not r.get('input_ids_sha256'):continue
        h=images[-1]['sha256'];im=p/(ap.name[:3]+'-input-manifest.json')
        if im.is_file():
            m=js(im); f=p/Path(m['current_image_path']).name
            if m['current_image_sha256']!=h or m['images']!=images or m['input_ids_sha256']!=r['input_ids_sha256'] or m['model_receipt']!=r['receipt'] or m.get('normal_history_only')!=True:continue
        else:f=p/(ap.name[:3]+'-observed.png')
        if not f.is_file() or sha(f.read_bytes())!=h or (images[-1]['width'],images[-1]['height'])!=(1280,720):continue
        rawpics[h]=f
        frames[i]=dict(png_sha256=h,source_png=f.name,response_sha256=sha(rb),action_file=ap.name,action_sha256=sha(ap.read_bytes()),model_receipt=r['receipt'],input_ids_sha256=r['input_ids_sha256'],manifest_sha256=sha(im.read_bytes()) if im.is_file() else None)
    trace,trace_sha=parse_trace(p/'browser_trace.zip',actions)
    if not trace:skip['trace sequence absent or not bijective']+=1;continue
    for i,t in trace.items():
        if i not in frames or i+1 not in frames:continue
        records.append(dict(source_run=str(p),task=task,step=i,action=actions[i],before=frames[i],after=frames[i+1],trace=t,trace_member_sha256=trace_sha))
    for cp in sorted(p.glob('checkpoint-*')):
        if (cp/'original-state-drift.json').exists() or not (cp/'checkpoint.json').is_file():continue
        ck=js(cp/'checkpoint.json');i=ck['step']
        if i not in frames or i-1 not in trace or i-1 not in frames or ck['fingerprint']['image_sha256']!=frames[i]['png_sha256']:continue
        for name,file in [('stale_replace','stale.png'),('blank_replace','blank.png'),('buttons_only','controls.png')]:
            decision=cp/(name+'-decision.json');f=cp/file
            if not (decision.exists() and f.exists()):continue
            raw=decision.read_bytes();d=json.loads(raw);ims=d.get('images',[]);regular=rs[i]['images'];h=sha(f.read_bytes());meta=d.get('meta',{})
            if not ims or ims[:-1]!=regular[:-1] or ims[-1]['message_index']!=regular[-1]['message_index'] or ims[-1]['sha256']!=h or (ims[-1]['width'],ims[-1]['height'])!=(1280,720) or not d.get('input_ids_sha256') or not d.get('receipt'):continue
            if meta.get('step')!=i or meta.get('condition')!=name or meta.get('bin')!=ck['bin']:continue
            rawpics[h]=f
            probes.append(dict(source_run=str(p),step=i-1,probe_step=i,bin=ck['bin'],condition=name,delivered_sha256=h,normal_sha256=frames[i]['png_sha256'],relative_file=cp.name+'/'+file,decision_file=cp.name+'/'+decision.name,decision_sha256=sha(raw),model_receipt=d['receipt'],input_ids_sha256=d['input_ids_sha256'],same_history_and_message_slot=True))
def send(z,n,b):
    m=tarfile.TarInfo(n);m.size=len(b);z.addfile(m,io.BytesIO(b))
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as z:
    send(z,'extract.json',json.dumps(dict(events=records,probes=probes,completed_sources=len(dirs),skip=dict(skip)),separators=(',',':')).encode())
    needed={v[k]['png_sha256'] for v in records for k in ('before','after')}|{v['delivered_sha256'] for v in probes}
    for h in sorted(needed-set(KNOWN)):send(z,h+'.png',rawpics[h].read_bytes())
'''
def main():
    dest=WORK/'natural';dest.mkdir(parents=True,exist_ok=True)
    known={p.stem for folder in [ROOT/'datasets/jev-trajectory-v1/images',dest] for p in folder.glob('*.png')}
    body=('KNOWN='+repr(sorted(known))+'\n'+SERVER).encode()
    ssh=subprocess.Popen(['D:/Git/usr/bin/ssh.exe','-T','-o','BatchMode=yes','-o','LogLevel=ERROR','-o','ConnectTimeout=8','4090','python3 -B -'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    ssh.stdin.write(body);ssh.stdin.close();n=size=0
    with tarfile.open(fileobj=ssh.stdout,mode='r|',bufsize=262144) as z:
        for m in z:
            assert m.isfile() and (m.name=='extract.json' or re.fullmatch(r'[a-f0-9]{64}\.png',m.name))
            b=z.extractfile(m).read();assert len(b)==m.size
            if m.name=='extract.json':
                d=json.loads(b);print('sources:',d['completed_sources'],'trace events:',len(d['events']),'delivery probes:',len(d['probes']),d['skip'],flush=True)
            else:assert sha(b)==m.name[:-4];n+=1;size+=len(b)
            (dest/m.name).write_bytes(b)
    assert ssh.wait()==0;print('new original PNGs:',n,'bytes:',size,flush=True)
if __name__=='__main__':main()
