import json
from manage import HERE,remote,save
code=(HERE/'inspect_remote.py').read_text(encoding='utf8').replace('print(json.dumps(out,ensure_ascii=False))','')
code+=r'''
root=B/'binary-gate-comparison-20261112'
launch=json.loads((root/'launch.json').read_bytes())
out['actual_comparison_launcher']=identity(launch['pid'])
assert out['actual_comparison_launcher'].get('absent') is True
out['worker_actual']={}
for model in ['flash','neohorse','style']:
 v=json.loads((root/'results'/model/'process.json').read_bytes());actual=identity(v['pid'])
 assert actual.get('absent') is True
 out['worker_actual'][model]=actual
exitfile=B/'resource-attempt-20261106-01'/('child-'+str(launch['pid'])+'-exit.json')
out['holder_recorded_launcher_exit']=json.loads(exitfile.read_bytes());assert out['holder_recorded_launcher_exit']['exit_code']==0
assert not out['compute'].strip()
out['actual_calls']=json.loads((root/'terminal.json').read_bytes())['attempted_calls'];assert out['actual_calls']==54
print(json.dumps(out))
'''
out,d=remote(code,'final-process-resource-inspection');v=json.loads(out)
save(HERE/'final-resource-inspection.json',{'evidence':str(d),'value':v})
print(json.dumps({'launcher_and_three_workers_absent':True,'holder_nine_locks_verified':len(v['verified_locks'])==9,'compute':v['compute'],'actual_calls':v['actual_calls'],'inspection':str(d)}))
