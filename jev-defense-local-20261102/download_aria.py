"""Resume owned artifact transfer with bounded connections and publisher SHA checks."""
import hashlib,json,os,pathlib,shutil,subprocess,time
from fetch_models import MODELS,digest
B=pathlib.Path(__file__).resolve().parent
root=B/'models-verified';out=[]
for key,(repo,rev) in MODELS.items():
    meta=json.loads((B/'identities'/(key+'.json')).read_bytes());assert meta['sha']==rev
    dest=root/key;dest.mkdir(parents=True,exist_ok=True);(dest/'HF-identity.json').write_text(json.dumps(meta))
    for s in meta['siblings']:
        if not s.get('lfs') or s['rfilename'].startswith('assets/'):continue
        p=dest/s['rfilename'];p.parent.mkdir(parents=True,exist_ok=True)
        expected=s['lfs']['sha256']
        if p.exists() and p.stat().st_size==s['size'] and digest(p)==expected:continue
        part=p.with_name(p.name+'.partial')
        if not p.exists() and part.exists():os.replace(part,p)
        out.append('https://hf-mirror.com/'+repo+'/resolve/'+rev+'/'+s['rfilename']+'\n  dir='+str(p.parent)+'\n  out='+p.name+'\n  checksum=sha-256='+expected+'\n')
plan=B/('aria-plan-'+str(time.time_ns())+'.txt');plan.write_text(''.join(out))
subprocess.run(['aria2c','--input-file='+str(plan),'--continue=true','--max-concurrent-downloads=3','--split=16','--max-connection-per-server=16','--min-split-size=16M','--auto-file-renaming=false','--file-allocation=none','--max-tries=4','--retry-wait=3','--summary-interval=30','--console-log-level=warn'],check=True)
for key,(repo,rev) in MODELS.items():
    meta=json.loads((B/'identities'/(key+'.json')).read_bytes());dest=root/key;records=[]
    for s in meta['siblings']:
        if s['rfilename'].startswith('assets/'):continue
        p=dest/s['rfilename'];expected=(s.get('lfs') or {}).get('sha256')
        assert p.stat().st_size==s['size'],p
        h=digest(p);assert (h==expected if expected else digest(p,'sha1')==s['blobId']),p
        records.append({'file':s['rfilename'],'bytes':p.stat().st_size,'sha256':h,'publisher_lfs_sha256':expected,'publisher_git_blob':s.get('blobId')})
    (dest/'download-complete-receipt.json').write_text(json.dumps({'repo':repo,'revision':rev,'files':records,'time':time.time(),'small_only':False,'transport':'HF mirror, exact official pinned identities'},indent=2))
    print(json.dumps({'model':key,'verified_files':len(records),'verified_bytes':sum(r['bytes'] for r in records)}),flush=True)
