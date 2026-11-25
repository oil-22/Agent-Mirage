"""Replay recorded source patches as data, never execute historic commands."""
import json,pathlib,re,hashlib
ROOT=pathlib.Path(__file__).parent
OUT=ROOT/'recovered-patches';OUT.mkdir(exist_ok=True)
VERSIONS=ROOT/'source-versions';VERSIONS.mkdir(exist_ok=True)
rows=json.loads((ROOT/'history-tool-calls.json').read_text(encoding='utf-8'))
audit=[];failures=[];dec=json.JSONDecoder()

def target(path):
    path=path.replace('\\','/')
    marker='mirage-defense-pilot-20261023/'
    if marker not in path:return None
    rel=path.split(marker,1)[1]
    p=pathlib.PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts:raise ValueError(path)
    return OUT/p

def apply(patch,j):
    lines=patch.splitlines();i=1
    while i<len(lines):
        line=lines[i]
        m=re.match(r'\*\*\* (Add|Update|Delete) File: (.*)',line)
        if not m:i+=1;continue
        op,path=m.groups();p=target(path);i+=1;chunk=[]
        while i<len(lines) and not lines[i].startswith(('*** Add File:','*** Update File:','*** Delete File:','*** End Patch')):
            chunk.append(lines[i]);i+=1
        if p is None:continue
        try:
            if op=='Add':
                data='\n'.join(x[1:] for x in chunk if x.startswith('+'))+'\n'
                if p.exists() and p.read_text(encoding='utf-8')!=data:raise ValueError('Add already exists different')
            elif op=='Delete':
                # Deletions describe historical source replacement within this isolated directory.
                if p.exists():p.unlink()
                continue
            else:
                if not p.exists():raise ValueError('Missing base')
                data=p.read_text(encoding='utf-8');oldlines=data.splitlines();cursor=0
                hunks=[];h=[]
                for x in chunk:
                    if x.startswith('@@'):
                        if h:hunks.append(h);h=[]
                    elif x.startswith((' ','+','-')):h.append(x)
                if h:hunks.append(h)
                for h in hunks:
                    before=[x[1:] for x in h if x[0] in ' -'];after=[x[1:] for x in h if x[0] in ' +']
                    found=[k for k in range(cursor,len(oldlines)-len(before)+1) if oldlines[k:k+len(before)]==before]
                    if not found:
                        found=[k for k in range(cursor,len(oldlines)-len(before)+1) if [x.rstrip() for x in oldlines[k:k+len(before)]]==[x.rstrip() for x in before]]
                    if not found:raise ValueError('Hunk mismatch '+repr(before[:2]))
                    k=found[0];oldlines[k:k+len(before)]=after;cursor=k+len(after)
                data='\n'.join(oldlines)+'\n'
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8',newline='\n')
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            if p.suffix=='.py' and not (VERSIONS/(h+'.py')).exists():(VERSIONS/(h+'.py')).write_bytes(p.read_bytes())
            audit.append({'call':j,'operation':op,'file':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        except Exception as e:failures.append({'call':j,'operation':op,'file':str(p.relative_to(OUT)),'error':str(e)})

for j,row in enumerate(rows):
    if row['timestamp']>='2026-10-30':continue
    payload=row['payload'];s=payload.get('input',payload.get('arguments',''))
    if not isinstance(s,str):continue
    if payload.get('name')=='apply_patch' and s.startswith('*** Begin Patch'):apply(s,j);continue
    for m in re.finditer(r'(?:tools\.)?apply_patch\(\s*',s):
        tail=s[m.end():]
        if tail.startswith('"'):
            try:p,_=dec.raw_decode(tail)
            except Exception as e:failures.append({'call':j,'error':'literal parse '+str(e)});continue
            apply(p,j)

(ROOT/'source-reconstruction-audit.json').write_text(json.dumps({'patches':audit,'failures':failures},ensure_ascii=False,indent=2),encoding='utf-8')
print('Restored',len(list(OUT.rglob('*'))),'entries;',len(audit),'patch operations;',len(failures),'failures')
for f in failures:print(json.dumps(f,ensure_ascii=False))
