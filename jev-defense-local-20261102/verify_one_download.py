import argparse,json,pathlib,time
from fetch_models import MODELS,digest
p=argparse.ArgumentParser();p.add_argument('model');a=p.parse_args()
B=pathlib.Path(__file__).resolve().parent;key=a.model;repo,rev=MODELS[key];dest=B/'models-verified'/key;meta=json.loads((B/'identities'/(key+'.json')).read_bytes());records=[]
for s in meta['siblings']:
    if s['rfilename'].startswith('assets/'):continue
    f=dest/s['rfilename'];assert not f.with_name(f.name+'.aria2').exists(),'Transfer still active: '+str(f)
    before=f.stat();assert before.st_size==s['size'];expected=(s.get('lfs') or {}).get('sha256')
    h=digest(f);assert (h==expected if expected else digest(f,'sha1')==s['blobId']),f
    after=f.stat();assert(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    records.append({'file':s['rfilename'],'bytes':before.st_size,'sha256':h,'publisher_lfs_sha256':expected,'publisher_git_blob':s.get('blobId')})
target=dest/'download-complete-receipt.json'
with target.open('x') as f:json.dump({'repo':repo,'revision':rev,'files':records,'time':time.time(),'small_only':False,'independently_verified_before_loading':True},f,indent=2)
print(json.dumps({'model':key,'files':len(records),'bytes':sum(r['bytes'] for r in records)}))
