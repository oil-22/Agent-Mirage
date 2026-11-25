import hashlib,json,pathlib,sys,time
root=pathlib.Path(sys.argv[1]);result={};started=time.time()
for model in ['Qwen3.5-9B','GLM-4.6V-Flash-411bb4d77144']:
    for p in sorted((root/model).glob('*')):
        if not p.is_file():continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            while b:=f.read(16*1024*1024):h.update(b)
        result[str(p.relative_to(root))]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
pathlib.Path(sys.argv[2]).write_text(json.dumps({'files':result,'seconds':round(time.time()-started)},indent=2))
print('hashed',len(result),'files')
