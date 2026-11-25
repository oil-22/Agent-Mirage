"""Prepare a local, nonlaunchable full-GUI candidate and exact frozen-source comparison."""
import ast,base64,difflib,hashlib,json,shutil,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'live-candidate-current.json').exists(),'Do not repeat preparation'
done=json.loads((PREP/'completed-current.json').read_bytes())
assert sha((Path(done['directory'])/'review.json').read_bytes())==done['review_sha256']
original=json.loads((BASE/'v3.9.9-scroll-validation-resume.json').read_bytes())
names=['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py']
code='RELEASE='+repr(original['release'])+'\nNAMES='+repr(names)+r'''
import base64,hashlib,json
from pathlib import Path
r=Path(RELEASE);out={}
for n in NAMES:
 p=r/n;assert p.is_file() and p.resolve().parent!=p.resolve()
 p.resolve().relative_to(r.resolve())
 b=p.read_bytes();out[n]={'base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
print(json.dumps(out))
'''
files=json.loads(remote(code,host='4090',timeout=90))
out=PREP/('live-candidate-'+str(time.time_ns()));out.mkdir();frozen=out/'original-full-validation';candidate=out/'candidate-release'
for n,d in files.items():
 b=base64.b64decode(d['base64']);assert sha(b)==d['sha256']==original['bindings'][n],n
 p=frozen/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
stage=json.loads((PREP/'current.json').read_bytes());source=Path(stage['release'])
shutil.copytree(source,candidate,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json']:
 shutil.copy2(frozen/n,candidate/n)
# Require an explicit new decision receipt through a separate future launcher.
# This preparation contains no GPU/browser/model startup or launcher.
def defs(p):
 return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
changes={};diffs=[]
for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py']:
 a=(frozen/n).read_text(encoding='utf-8');b=(candidate/n).read_text(encoding='utf-8')
 before,after=defs(frozen/n),defs(candidate/n)
 changes[n]={'original_sha256':sha((frozen/n).read_bytes()),'candidate_sha256':sha((candidate/n).read_bytes()),'changed_top_level_functions_or_classes':[k for k in before if k in after and before[k]!=after[k]],'added_top_level_functions_or_classes':[k for k in after if k not in before],'removed_top_level_functions_or_classes':[k for k in before if k not in after]}
 diffs.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='original/'+n,tofile='candidate/'+n))
(out/'original-to-candidate.diff').write_text(''.join(diffs),encoding='utf-8')
olddefs,newdefs=defs(frozen/'defense/core.py'),defs(candidate/'defense/core.py')
assert olddefs['Limits']==newdefs['Limits'],'Original Limits must be identical'
for n in ['defense/schema.py','defense/qwen_backend.py','defense/http_backend.py']:
 assert (frozen/n).read_bytes()==(candidate/n).read_bytes(),n
plan=json.loads((candidate/'plan80.json').read_bytes());item=next(x for x in plan['queue']if x['run_id']=='vwa--classifieds_112--stale_replace--joint')
proposal={'status':'PREPARED_NOT_AUTHORIZED_FOR_FORMAL_EXECUTION','candidate_release':str(candidate),'original_release':original['release'],
 'scope':'One NEW independent fullGUI joint/stale development trajectory on the original known task; not rerunning old terminal, no baseline/post_only queue, no formal efficacy estimate',
 'proposed_run':item,'original_runner_unchanged':True,'original_plan80_unchanged':True,'original_native_request_unchanged':True,
 'original_limits_AST_unchanged':True,'original_schema_and_backends_byte_unchanged':True,'source_changes':changes,
 'deployment':'Current verified original27B/BF16/SDPA fiveGPU development service; different from historical7GPU, no bitwise/cost equivalence claim',
 'original_parameters':{'seed':20261011,'native_resolution':[1280,720],'actor_max_output':2048,'verifier_max_output':4096,'max_steps':50,'max_actor_calls':70,'max_verifier_calls':140,'max_regenerations_per_decision':2,'max_recaptures_per_decision':2,'max_format_retries':1},
 'max_model_calls_for_single_trajectory':210,'new_paid_API_calls':0,'same_live_recapture':'original env._get_obs, no archived-frame substitution','scoring':'original URL-match official evaluator, private expected URL excluded from public inputs',
 'input_history':'Original complete native history and original injection trigger unchanged; no truncation/resizing/actionJSON edits',
 'tradeoff':'Broader scene usability can allow exploratory recovery at a coherent off-target footer, but can admit a coherent wrong destination. Every candidate retains its own checks; scope hints/source inventory/direction checks can alter verifier replies and spend existing format/regeneration budgets, potentially adding false blocks. Focus/history/status-strength failures remain.',
 'release_blockers':['User decision on this concrete new fullGUI condition per explicit experimental protocol','Same-live logged-in environment preflight in a NEW owned root with source seals and official scorer transport binding','Independent preflight review of combined changed Controller plus original full-task probes; observer-only tests do not cover full history/point/completion paths','Once-only launcher with actual UID/full command/task browser locks/active receipt and no old roots/queues','Final human source review of original-to-candidate diff before treating validators as unchanged relative to historical full trial'],
 'launcher_created':False,'remote_allocation':False,'browser_started':False,'new_model_calls':0,'formal_release':False,'old_terminals_immutable':True}
(out/'proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()}
(out/'sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'proposal_sha256':sha((out/'proposal.json').read_bytes()),'manifest_sha256':sha((out/'sha256.json').read_bytes()),'status':proposal['status'],'launcher_ready':False,'model_calls':0}
(PREP/'live-candidate-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(pointer,ensure_ascii=False))
