"""Read-only source inventory for unchanged native benchmark adapters."""
import json
from pathlib import Path
from remote import remote

HERE = Path(__file__).resolve().parent
CODE = r'''
import pathlib,json,ast,hashlib,subprocess,os
base=pathlib.Path('/data/researcher')
names=['osworld-qwen27-2026-10-13','androidworld-uitars7-2026-10-15','vwa-qwen27-2026-10-12','webmall-vlm-responses']
rows=[]
for name in names:
 p=base/name
 if not p.exists():continue
 files=[]
 for f in sorted(p.glob('*.py')):
  raw=f.read_bytes()
  try:
   tree=ast.parse(raw)
   definitions=[{'name':n.name,'line':n.lineno,'end':n.end_lineno,'type':type(n).__name__}for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef))]
   imports=[ast.unparse(n)for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
  except Exception:definitions=[];imports=[]
  files.append({'path':str(f),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'definitions':definitions,'imports':imports})
 rows.append({'directory':str(p),'files':files,'children':[x.name for x in sorted(p.iterdir())][:80]})
# Process identities only. Never print command arguments belonging to other tasks.
ps=subprocess.check_output(['ps','-u','whz','-o','pid=,comm='],text=True)
print(json.dumps({'directories':rows,'owned_process_identities':ps}))
'''
data=json.loads(remote(CODE,host='4090'))
(HERE/'adapter-source-inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for row in data['directories']:
 print(json.dumps({'directory':row['directory'],'files':[{'path':f['path'],'size':f['size']}for f in row['files']],'children':row['children']},ensure_ascii=False))
