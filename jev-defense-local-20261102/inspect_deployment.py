"""Read actual service identity, inherited locks, local replies and their SHA seals."""
import hashlib,json,os,pathlib,time,urllib.request,subprocess
B=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'time':time.time(),'uid':os.getuid(),'services':[],'gpu_query':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory','--format=csv'],text=True)}
for run in sorted((B/'services').glob('*')):
    if not (run/'launch.json').exists():continue
    launch=json.loads((run/'launch.json').read_bytes());pid=launch['pid'];proc=pathlib.Path('/proc')/str(pid)
    row={'run':str(run),'launch':launch,'exists':proc.exists(),'reserved_gpu_seconds_if_still_owned':None}
    gpu_pids={int(line.split(',')[1].strip()) for line in out['gpu_query'].splitlines()[1:] if line.split(',')[0].strip()==launch['gpu']['uuid']}
    row['exclusive_gpu']=gpu_pids=={pid}
    row['actual_gpu_pids']=sorted(gpu_pids)
    if proc.exists():
        command=proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
        row.update(uid=proc.stat().st_uid,full_command=command,command_matches=command==' '.join(launch['command']),fd_locks=[])
        for f in proc.joinpath('fdinfo').iterdir():
            text=f.read_text()
            if 'lock:' in text:row['fd_locks'].append({'fd':f.name,'info':text,'target':os.readlink(proc/'fd'/f.name)})
        if row['command_matches'] and row['uid']==launch['uid'] and len(row['fd_locks'])==len(launch['locks']):row['reserved_gpu_seconds_if_still_owned']=time.time()-launch['time']
        port=int(launch['command'][-1])
        try:
            with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/health',timeout=5) as r:row['health']=json.load(r)
        except Exception as e:row['health_error']=str(e)
    receipts=[]
    for d in sorted((run/'runtime/requests').glob('*')):
        if not d.is_dir():continue
        check={'request':d.name,'sealed':(d/'seal.json').exists()}
        if check['sealed']:
            seal=json.loads((d/'seal.json').read_bytes());check['sha_ok']=all(sha(d/n)==h for n,h in seal.items());assert check['sha_ok'],d
        if(d/'response.json').exists():
            r=json.loads((d/'response.json').read_bytes());check.update(status=r['status'],image_sha256=r['image_sha256'],query=json.loads((d/'request.json').read_bytes())['query_key'],answer=r['answer'])
            assert sha(d/'original.image')==r['image_sha256'] and sha(d/'request.json')==r['request_sha256'] and sha(d/'forward-trace.json')==r['forward_trace_sha256']
        elif(d/'failure.json').exists():check['status']='technical_failure'
        else:check['status']='pending'
        receipts.append(check)
    row['receipts']=receipts;row['service_log_sha256']=sha(run/'service.log');out['services'].append(row)
target=B/('inspection-'+str(time.time_ns())+'.json');target.write_text(json.dumps(out,indent=2))
print(json.dumps({'inspection':str(target),'services':[{'model':r['launch']['model'],'exists':r['exists'],'uid':r.get('uid'),'command_matches':r.get('command_matches'),'held_lock_count':len(r.get('fd_locks',[])),'ready':r.get('health',{}).get('phase'),'replies':sum(x.get('status')=='ok' for x in r['receipts']),'failures':sum(x.get('status')=='technical_failure' for x in r['receipts'])} for r in out['services']]}))
