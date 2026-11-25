import json,subprocess
code="""from pathlib import Path
import json
p=Path('/data/researcher/jev-defense-four-gpu-20261106/independent-service-postexit-mirror-1793983761231132390-gzip-linked01')
a=[f for f in p.rglob('*') if f.is_file()]
print(json.dumps({'files':len(a),'bytes':sum(f.stat().st_size for f in a),'has_receipt':(p/'receipt.json').exists(),'has_seal':(p/'seal.json').exists()}))
"""
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=45)
print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)
