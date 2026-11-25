from pathlib import Path
import ast, json, subprocess
import deploy_scale100 as d

P=Path(__file__).resolve().parent
tree=ast.parse((P/'deploy_scale100.py').read_text())
snippets=[n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets)]
extract=next(s for s in snippets if 'tarfile.open' in s)
smoke=next(s for s in snippets if 'REFERENCE_AND_NATIVE_CHECK_OK' in s)
r=subprocess.run(d.SSH+['3090','/opt/whz/conda-envs/webmall-vlm/bin/python -'],input='ROOT='+repr(d.ROOT)+'\n'+extract,text=True,capture_output=True,timeout=90)
assert r.returncode==0,r.stderr[-3000:]
results={'3090':json.loads(r.stdout),'4090':d.remote('4090',smoke,timeout=90)}
(P/'deployment-verification.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))
