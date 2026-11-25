from pathlib import Path
import base64
import io
import json
import zipfile
from ops import HERE,remote,save,sha

def main():
    r=HERE/'runtime-package';blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED)as z:
        for p in sorted((r/'grammar-vendor').rglob('*')):
            if p.is_file():z.writestr(p.relative_to(r).as_posix(),p.read_bytes())
        for n in ['bounded_schema.py','native_format_bridge.py']:z.writestr(n,(HERE/n).read_bytes())
        z.writestr('native_tokenizer_check.py',(HERE/'native_tokenizer_check.py').read_bytes())
    code=r'''
from pathlib import Path
import base64,hashlib,io,json,os,subprocess,zipfile
r=Path('/home/researcher/jev-defense-four-gpu-20261106/bounded-CPU-native-20261109-linked04');r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():assert(r/n).resolve().is_relative_to(r.resolve())
 z.extractall(r)
x=subprocess.run(['/opt/whz/conda-envs/webmall-vlm/bin/python','-B',str(r/'native_tokenizer_check.py')],capture_output=True,timeout=240,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'})
(r/'stdout.txt').write_bytes(x.stdout);(r/'stderr.txt').write_bytes(x.stderr)
print(json.dumps({'root':str(r),'returncode':x.returncode,'receipt':json.loads((r/'CPU-tokenizer-result/receipt.json').read_bytes())if(r/'CPU-tokenizer-result/receipt.json').exists()else None,'stderr_tail':x.stderr.decode(errors='replace')[-1500:]}))
'''
    raw,op=remote('3090',code,'native-tokenizer-CPU-check',timeout=270,private_prefix='PAYLOAD='+repr(base64.b64encode(blob.getvalue()).decode())+'\n')
    v=json.loads(raw);save(HERE/'CPU-native-tokenizer-linked04-result.json',{'operation':str(op),'result':v});print(json.dumps(v,ensure_ascii=True))

if __name__=='__main__':main()
