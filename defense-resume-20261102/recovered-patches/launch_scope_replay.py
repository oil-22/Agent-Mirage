"""Launch fixed-input scope checks once; completed capacity controls are required."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;receipt=here/'v3.7-scope-launch.json';assert not receipt.exists()
stage=json.loads((here/'v2-staging.json').read_text())
formal=json.loads((here/'v3.6.2-vwa-resume.json').read_text())
preserved=json.loads((here/'v3.6.2-online-oom-preservation.json').read_text())
capacity=json.loads((here/'v8-capacity-replay-launch.json').read_text())
passed=json.loads(remote('import pathlib,json\nprint((pathlib.Path('+repr(capacity['root'])+')/"summary.json").read_text())',host='3090'))
assert passed['passed']and passed['cases'][0]['generated_ids_identical']
sources={'source':preserved['formal']['attempt']+'/events.jsonl',
         'sorted-source':formal['previous_failed_attempt']+'/events.jsonl',
         'baseline-source':formal['completed_results_skipped'][0]['attempt']+'/events.jsonl'}
code='''import pathlib,json,time,subprocess,hashlib,fcntl
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');release=pathlib.Path(RELEASE)
proc=pathlib.Path('/proc')/str(FORMALPID);assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
assert json.loads((pathlib.Path(FORMALROOT)/'status.json').read_text())['phase']=='technical_failure'
sources=SOURCES
hashes={path:hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()for path in sources.values()}
out=base/('comparison-scope-v37-'+str(time.time_ns()));log=out.with_suffix('.log')
cmd=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'comparison_scope_replay.py'),'--root',str(out),'--token-file',str(base/'transport.token')]
for flag,path in sources.items():cmd.extend(['--'+flag,path])
with log.open('xb')as stream:p=subprocess.Popen(cmd,cwd=release,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'root':str(out),'release':str(release),'log':str(log),'time':time.time(),'source_hashes':hashes,'capacity_summary_sha256':CAPACITYSHA,'scope':'Changed verifier comparison/scope checks, no GUI, no actor regeneration, no independent Mirage labels or efficacy'}))
'''.replace('FORMALROOT',repr(formal['root'])).replace('FORMALPID',str(formal['pid'])).replace('RELEASE',repr(stage['release'])).replace('SOURCES',repr(sources)).replace('CAPACITYSHA',repr(__import__('hashlib').sha256(json.dumps(passed,indent=2).encode()).hexdigest()))
data=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data))
