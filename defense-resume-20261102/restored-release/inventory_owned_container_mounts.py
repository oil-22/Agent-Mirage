import subprocess,json,os
from pathlib import Path
ids=subprocess.check_output(['docker','ps','-q']).decode().split();rows=[]
for c in json.loads(subprocess.check_output(['docker','inspect']+ids))if ids else []:
 ms=[]
 for m in c['Mounts']:
  f=Path(m['Source'])
  try:uid=f.stat().st_uid
  except OSError:uid=None
  ms.append({'source':str(f),'uid':uid,'type':m['Type']})
 rows.append({'id':c['Id'],'name':c['Name'],'mounts':ms,'path':c['Path'],'args':c['Args']})
print(json.dumps(rows))
