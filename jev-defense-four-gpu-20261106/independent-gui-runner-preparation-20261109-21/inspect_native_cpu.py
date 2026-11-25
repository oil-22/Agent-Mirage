"""Read the existing native CPU handle; preserve terminal originals, no retries."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha
code=r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path('/home/researcher/jev-defense-four-gpu-20261106/independent-gui-runner-preparation-20261109-21');a=r/'attempt-01'
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
record=json.loads((r/'launch.json').read_bytes());actual=identity(record['pid'])
if not actual.get('absent'):assert all(str(record[k])==str(actual[k])for k in ['pid','uid','command','start_ticks'])
out={'time':time.time(),'read_only':True,'actual':actual,'record':record,'new_model_GPU_GUI_scorer_calls':0}
for name in ['receipt.json','terminal.json','failure.json']:
 if(a/name).is_file():out[name]={'value':json.loads((a/name).read_bytes()),'sha256':sha(a/name)}
log=r/'attempt-01.log'
out['log']={'sha256':sha(log),'bytes':log.stat().st_size,'tail':log.read_text(errors='replace')[-1200:]}
if actual.get('absent')and(a/'seal.json').is_file():
 seal=json.loads((a/'seal.json').read_bytes())
 for name,h in seal.items():assert sha(a/name)==h,name
 selected=[r/'launch.json',log]+list((r/'package').glob('*.py'))+[r/'package/source-seal.json']
 selected += [q for q in a.rglob('*')if q.is_file()and q.suffix=='.json']
 archive=io.BytesIO();exported={}
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for q in sorted(selected):
   name=q.relative_to(r).as_posix();raw=q.read_bytes();exported[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
 out.update(terminal_collected=True,all_terminal_originals=seal,exported_files=exported,archive_sha256=hashlib.sha256(archive.getvalue()).hexdigest(),
            raw_CPU_tensors_preserved_remote_not_deleted=True)
 print(json.dumps({'receipt':out,'archive_base64':base64.b64encode(archive.getvalue()).decode()},ensure_ascii=False))
else:print(json.dumps({'receipt':out},ensure_ascii=False))
'''
output,operation=remote('3090',code,'inspect-native-full-history21-CPU-existing-handle',timeout=55)
value=json.loads(output);receipt=value['receipt'];target=HERE/('native-CPU-inspection-'+str(time.time_ns()));target.mkdir()
if'archive_base64'in value:
    raw=base64.b64decode(value['archive_base64']);assert hashlib.sha256(raw).hexdigest()==receipt['archive_sha256']
    (target/'originals.zip').write_bytes(raw);root=target/'original';root.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        for item in z.infolist():
            q=root/item.filename;assert q.resolve().is_relative_to(root.resolve());raw=z.read(item)
            assert hashlib.sha256(raw).hexdigest()==receipt['exported_files'][item.filename]
            q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
receipt['operation']=str(operation);save(target/'receipt.json',receipt)
save(target/'seal.json',{q.relative_to(target).as_posix():sha(q)for q in target.rglob('*')if q.is_file()})
print(json.dumps({'inspection':str(target),'receipt_sha256':sha(target/'receipt.json'),'actual':receipt['actual'],
                  'terminal':receipt.get('terminal.json'),'result':receipt.get('receipt.json'),
                  'failure':receipt.get('failure.json'),'model_calls':0},ensure_ascii=False))
