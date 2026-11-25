import collections
import gzip
import json
import pathlib
import re
import subprocess
import tarfile
import time

ARCHIVE = '/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'
OUT = pathlib.Path('/data/researcher/attention-audit-20261031')
OUT.mkdir(exist_ok=True)
groups = collections.Counter()
selected = collections.Counter()
started = time.time()
proc = subprocess.Popen(['pigz', '-dc', ARCHIVE], stdout=subprocess.PIPE)
count = 0
with gzip.open(OUT / 'members.jsonl.gz', 'wt') as index, tarfile.open(fileobj=proc.stdout, mode='r|') as tar:
    for m in tar:
        count += 1
        index.write(json.dumps([m.name, m.size, m.type.decode(errors='replace'), m.linkname], ensure_ascii=False) + '\n')
        p = pathlib.PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts:
            continue
        if m.name.startswith('attention-experiment/'):
            key = '/'.join(p.parts[:4])
            groups[key] += 1
        else:
            key = '/'.join(p.parts[:3])
        base = p.name.lower()
        want = m.name.startswith('_admin/') or base.endswith('.md')
        if m.name.startswith('attention-experiment/') and m.size < 8_000_000:
            want |= base.endswith(('.csv', '.tsv')) or (base.endswith('.json') and any(s in base for s in ['summary','manifest','status','aggregate','metrics','report','coverage','analysis','plan','result']))
            if base.endswith('.json') and selected[key] < 5:
                want = True
        if want and m.isfile() and m.size < 200_000_000:
            target = OUT / 'extracted' / p
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as src, target.open('wb') as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            selected[key] += 1
        if count % 20000 == 0:
            status = {'members': count, 'seconds': round(time.time()-started), 'current': m.name, 'groups':dict(groups), 'selected':sum(selected.values())}
            (OUT / 'scan-progress.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
            print(json.dumps({k:v for k,v in status.items() if k != 'groups'}, ensure_ascii=False), flush=True)
rc = proc.wait()
result = {'complete':rc == 0,'members':count,'seconds':round(time.time()-started),'groups':dict(groups),'selected':dict(selected)}
(OUT / 'scan-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False),flush=True)
