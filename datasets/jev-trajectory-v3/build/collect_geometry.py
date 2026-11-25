"""Retrieve recorded button rectangles from the existing historical checkpoint directory, read-only."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parents[1]; W=HERE.parents[1]/'.tmp/jev-balanced-v3';N=HERE.parents[1]/'.tmp/jev-trajectory-v2-review/natural'
S=r'''
import sys,json,hashlib
from pathlib import Path
for path in PATHS:
 p=Path(path)
 if not p.is_file():continue
 raw=p.read_bytes();r=json.loads(raw)
 if r.get('not_actor_input') is True and isinstance(r.get('rectangles'),list):
  print(json.dumps([path,hashlib.sha256(raw).hexdigest(),r['rectangles']],separators=(',',':')))
'''
def main():
    obj=json.loads((N/'extract.json').read_bytes())
    probes=[r for r in obj['probes'] if r['condition']=='buttons_only']
    paths={str(Path(r['source_run']+'/'+r['relative_file']).with_name('PRIVATE-mask-geometry.json')).replace('\\','/') for r in probes}
    result=subprocess.run(['D:/Git/usr/bin/ssh.exe','-T','-o','BatchMode=yes','-o','LogLevel=ERROR','-o','ConnectTimeout=8','4090','python3 -B -'],input=('PATHS='+repr(sorted(paths))+'\n'+S).encode(),capture_output=True,check=True)
    g={n:(h,b) for n,h,b in map(json.loads,result.stdout.splitlines())}
    keep={}
    for r in probes:
        loc=r['source_run']+'/'+r['relative_file'].rsplit('/',1)[0]+'/PRIVATE-mask-geometry.json'
        if loc not in g or not g[loc][1]:continue
        key=(r['delivered_sha256'],tuple(map(tuple,g[loc][1])))
        keep.setdefault(key,dict(template=r['delivered_sha256'],normal=r['normal_sha256'],run=r['source_run'],step=r['step'],
            rectangles=g[loc][1],geometry_file=loc,geometry_file_sha256=g[loc][0],source_probe=r))
    (W/'natural-mask-references.json').write_bytes((json.dumps(list(keep.values()),ensure_ascii=False)+'\n').encode())
    print('Archived rectangle files',len(g),'distinct observed masks',len(keep))
if __name__=='__main__':main()
