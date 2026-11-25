import pathlib,tarfile
root=pathlib.Path('/home/researcher/attention-20261031');paths=[]
for p in (root/'analysis').glob('*'):
    if p.is_file() and p.name!='query-cache.json':paths.append(p)
for name in ['campaign','source-campaign']:
    paths += [p for p in (root/name).glob('*') if p.is_file() and p.name not in ['raw.json','future-snapshots.json']]
for model in ['qwen27','qwen9','glm']:
    for prefix in ['', 'source-', 'preflight-']:
        folder=root/(prefix+model)
        if not folder.exists():continue
        paths += [p for p in folder.glob('*.json') if p.is_file()]
        if prefix=='source-':
            paths += list(folder.glob('*/input.json'))+list(folder.glob('*/output.txt'))
paths += [p for p in root.glob('*.json') if p.is_file()]
for folder in root.glob('glm-tail-T*'):
    paths += [p for p in folder.glob('*.json') if p.is_file()]
target=root/'results-summary.tar.gz'
with tarfile.open(target,'w:gz') as archive:
    for p in sorted(set(paths)):archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
print(str(target),target.stat().st_size,'bytes',len(set(paths)),'files')
