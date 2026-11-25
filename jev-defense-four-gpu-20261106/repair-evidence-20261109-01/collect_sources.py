from pathlib import Path
import base64
import hashlib
import json
import sys
from ops import HERE, GUI_ROOT, remote, save

def main():
    code='ROOT='+repr(GUI_ROOT+'/source-stage/source-controls')+'\n'+r'''
from pathlib import Path
import base64,hashlib,json
r=Path(ROOT);seal=json.loads((r/'seal.json').read_bytes());out={}
for n,h in seal.items():
 p=r/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
 if n.endswith('original.png')or n.endswith('source.json')or n=='receipt.json':out[n]=base64.b64encode(p.read_bytes()).decode()
print(json.dumps({'files':out,'seal_sha256':hashlib.sha256((r/'seal.json').read_bytes()).hexdigest(),'seal':seal}))
'''
    raw, target=remote('4090',code,'collect-source-images',timeout=60)
    data=json.loads(raw);out=HERE/'source-images';out.mkdir(exist_ok=False)
    for name,encoded in data['files'].items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(base64.b64decode(encoded))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==data['seal'][name]
    save(out/'collection.json',{'remote_root':GUI_ROOT+'/source-stage/source-controls','remote_seal_sha256':data['seal_sha256'],'files_verified':len(data['files']),'operation':str(target),'original_images_not_modified':True})
    print(json.dumps({'images':[str(p)for p in out.rglob('original.png')],'model_calls':0}))

if __name__=='__main__':main()
