"""Fetch only listed historical UI records from the frozen archive, read-only on 4090.

Existing hardlinks are resolved from the archival member index. No models, live
endpoints, browsers, remote files or private application state are operated on.
"""
from collections import Counter
import argparse, gzip, hashlib, json, re, subprocess, sys, tarfile
from pathlib import Path, PurePosixPath

HERE=Path(__file__).resolve().parent
WORK=HERE.parents[1]/'.tmp/jev-trajectory-v1-review'
IDX=WORK/'archive-members.jsonl.gz'
ROOT='/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'
BLOB=WORK/'archive-blobs'
TYPES={'OSWorld','AndroidWorld','VisualWebArena','WebMall'}
LOGS={'model_delivery.jsonl','action_execution.jsonl','coordinate_mapping.jsonl','trajectory.jsonl','agent_trace.jsonl','events.jsonl','intervention.jsonl','agent_visible_trace.jsonl','geometry.json'}

SERVER=r'''
import sys,json,subprocess,tarfile,os,io,hashlib
from pathlib import Path
os.nice(10)
want=set(NAMES); done=set()
def send(t,name,b):
    # Digest-only, flat tar member names. No source path can escape anywhere.
    member=tarfile.TarInfo(hashlib.sha256(name.encode()).hexdigest())
    member.size=len(b);t.addfile(member,io.BytesIO(b));done.add(name)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as out:
    for name in want:
        f=Path('/data/researcher/attention-audit-20261031/inputs')/ALIASES.get(name,name)
        if f.is_file():
            b=f.read_bytes()
            # Only accept pre-restored copies when the content hash is the PNG name.
            if len(f.stem)==64 and f.stem==hashlib.sha256(b).hexdigest():send(out,name,b)
    if done!=want:
        proc=subprocess.Popen(['pigz','-dc',ARCHIVE],stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=proc.stdout,mode='r|',bufsize=1024*1024) as ar:
                for m in ar:
                    if m.name in want and m.name not in done and m.isfile():
                        send(out,m.name,ar.extractfile(m).read())
                        if done==want:break
        finally:
            proc.stdout.close()
            if proc.poll() is None:proc.terminate()
            proc.wait()
if done!=want:sys.exit('Missing %d selected originals'%(len(want-done)))
'''
def content_id(name):return hashlib.sha256(name.encode()).hexdigest()
def index():
    with gzip.open(IDX,'rt',encoding='utf-8') as f:
        return {n:(sz,t,l) for n,sz,t,l in map(json.loads,f)}
def real(idx,n):
    seen=set()
    while idx[n][1]=='1':
        if n in seen:raise ValueError('hardlink cycle')
        seen.add(n);n=idx[n][2]
    if idx[n][1]!='0':raise ValueError(n)
    return n
def logs(n):
    parts=n.split('/')
    return len(parts)>4 and parts[0]=='mirage-trace' and parts[2].split('__')[0] in TYPES and parts[-1] in LOGS and not (parts[2].startswith('WebMall') and parts[-1]=='agent_visible_trace.jsonl')
def fetch(names,idx,aliasfile):
    BLOB.mkdir(parents=True,exist_ok=True)
    resolved={n:real(idx,n) for n in names}
    aliasfile.write_text(json.dumps(resolved,ensure_ascii=False),encoding='utf-8')
    ready={n for n in resolved.values() if (BLOB/content_id(n)).is_file() and (BLOB/content_id(n)).stat().st_size==idx[n][0]}
    todo=sorted(set(resolved.values())-ready)
    print('Selected:',len(names),'distinct archival blobs:',len(set(resolved.values())),'to fetch:',len(todo),'MiB:',round(sum(idx[n][0] for n in todo)/2**20),flush=True)
    if not todo:return
    aliases={v:n for n,v in resolved.items() if '/_embedded-input-images/' in n}
    body=('NAMES='+repr(todo)+'\nALIASES='+repr(aliases)+'\nARCHIVE='+repr(ROOT)+'\n'+SERVER).encode()
    # The (potentially long) remote script is sent before reading any binary data:
    # Python reads all of stdin before executing it.
    lookup={content_id(n):n for n in todo}
    proc=subprocess.Popen(['D:/Git/usr/bin/ssh.exe','-T','-o','BatchMode=yes','-o','ConnectTimeout=9','4090','python3 -B -'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    proc.stdin.write(body);proc.stdin.close()
    with tarfile.open(fileobj=proc.stdout,mode='r|',bufsize=1024*256) as t:
        for m in t:
            n=lookup.pop(m.name)
            if not m.isfile() or m.size!=idx[n][0]:raise ValueError(n)
            raw=t.extractfile(m).read()
            if len(raw)!=m.size:raise ValueError('truncated '+n)
            (BLOB/m.name).write_bytes(raw)
    proc.stdout.close()
    if proc.wait() or lookup:raise ValueError('incomplete archive stream')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('kind',choices=['logs','images'])
    args=parser.parse_args();idx=index()
    want=[n for n in idx if logs(n)] if args.kind=='logs' else json.loads((WORK/'wanted-archive-images.json').read_bytes())
    fetch(want,idx,WORK/('archive-'+args.kind+'-aliases.json'))
