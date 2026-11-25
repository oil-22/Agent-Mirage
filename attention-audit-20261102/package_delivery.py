import datetime,hashlib,json,pathlib,tarfile
R=pathlib.Path(__file__).parent
audit=json.loads((R/'analysis/delivery-verification.json').read_text(encoding='utf-8'));assert audit['status']=='passed'
report=(R/'多轨迹扩展实验报告.md').read_text(encoding='utf-8');assert '全部计划配置已完成并通过终局审计' in report
archive=R/'attention-expansion-deliverables-20261102.tar.gz';manifest=R/'final-manifest.json'
paths=[p for p in R.rglob('*') if p.is_file() and p not in [archive,manifest] and '__pycache__' not in p.parts]
entries=[]
for p in sorted(paths):entries.append({'path':p.relative_to(R).as_posix(),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest.write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'complete','remote_raw_root':'3090:/home/researcher/attention-20261102','tensors':'Raw NPZ remain on3090; analysis/measurements.json contains per-capture attention SHA and request SHA.','verification':audit,'files':entries},ensure_ascii=False,indent=2),encoding='utf-8')
with tarfile.open(archive,'w:gz') as tar:
 for p in paths+[manifest]:tar.add(p,arcname=p.relative_to(R).as_posix(),recursive=False)
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest_files':len(entries)}))
