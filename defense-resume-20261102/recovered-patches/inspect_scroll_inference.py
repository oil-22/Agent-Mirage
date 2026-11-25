from remote import remote
print(remote(r'''
import pathlib,json,pwd,time,subprocess
p=pathlib.Path('/proc/2140814');root=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023/inference-service-v10-1792914231469085180')
rows=[]
for d in sorted((root/'requests').iterdir(),key=lambda d:d.name)[-4:]:
 rows.append({'request':d.name,'files':[{'name':x.name,'bytes':x.stat().st_size,'age':time.time()-x.stat().st_mtime}for x in d.iterdir()]})
print(json.dumps({'process':{'owner':pwd.getpwuid(p.stat().st_uid).pw_name,'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()}if p.exists()else None,'requests':rows,'gpu':subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout}))
''',host='3090'))
