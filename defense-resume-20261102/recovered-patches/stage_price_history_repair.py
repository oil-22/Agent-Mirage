"""Freeze an isolated controller repair and source-bound counterexamples, zero inference."""
import ast,copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-history-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(BASE/'focus-conflict-fullgui-development/paused-finalization-current.json')
stage=read(BASE/'focus-conflict-fullgui-development/fullgui-staging-current.json');sr=Path(stage['release'])
out=P/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(sr,release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['minimum_price_reason_scope.py','test_minimum_price_reason_scope.py','price_history_binding.py','test_price_history_binding.py','run_price_history_repair.py']:
    shutil.copy2(BASE/n,release/n)
p=release/'defense/core.py';s=p.read_text(encoding='utf-8');original=s
def patch(old,new):
    global s
    assert s.count(old)==1,old;s=s.replace(old,new)
patch('from focus_history_conflict_scope import','from price_history_binding import PRICE_FACT_READ,PRICE_HISTORY_RELATION,needs_price_history,check_price_history,task_text\nfrom minimum_price_reason_scope import minimum_reason_check\nfrom focus_history_conflict_scope import')
patch('evidence-v4.0.3b-dev-focus-plan-report-20261029','evidence-v4.0.4-dev-price-history-binding-20261029')
patch("'completion_relation','history_report'}:view=self.reference_view", "'completion_relation','history_report','price_read','price_relation'}:view=self.reference_view")
patch("        if phase=='focus':system=FOCUS_READ", "        if phase=='focus':system=FOCUS_READ\n        if phase=='price_read':system=PRICE_FACT_READ\n        if phase=='price_relation':system=PRICE_HISTORY_RELATION")
patch("if phase in {'screen','focus','completion'}:","if phase in {'screen','focus','completion','price_read'}:")
patch("if phase in {'alignment','completion_relation'}:return validate_alignment(value,view,candidate,allow_acknowledgment=phase=='completion_relation')", "if phase in {'alignment','completion_relation','price_relation'}:return validate_alignment(value,view,candidate,allow_acknowledgment=phase in {'completion_relation','price_relation'})")
patch("                checked=validate_verdict(value,view,candidate,proposal)", """                checked=validate_verdict(value,view,candidate,proposal)
                minimum_scope=minimum_reason_check(checked,task_text(view))
                self.log.append('minimum_reason_consistency',minimum_scope)
                if minimum_scope['reject']:raise ValidationError('Internal minimum explanation conflict: '+json.dumps(minimum_scope['errors']))""")
patch("                if phase=='point':\n                    system+=", "                if str(error).startswith('Internal minimum explanation conflict:'):\n                    system+='\\nThe previous reason contains a logical conflict, not a new GUI fact: equal prices cannot be strictly cheaper. Reassess the same actual evidence and every other missing premise. Do not infer true prefix coverage from your prior wording or automatically mark minimum supported.'\n                if phase=='point':\n                    system+=")
patch("            point_reason=None;point_needs_evidence=False;focus_reason=None", """            price_history_reason=None
            if self.limits.probe_history_reports and needs_price_history(candidate,proposal):
                try:price_binding=check_price_history(self,candidate_view,candidate)
                except (ValidationError,BudgetExhausted)as e:return blocked('price_history_verifier_error:'+str(e))
                price_history_reason=price_binding['reason']
            point_reason=None;point_needs_evidence=price_history_reason is not None;focus_reason=None""")
patch("or direction_reason is not None\n", "or direction_reason is not None or price_history_reason is not None\n")
patch("completion_reason or direction_reason or point_reason or focus_reason or verdict['action']['reason']", "completion_reason or direction_reason or price_history_reason or point_reason or focus_reason or verdict['action']['reason']")
p.write_text(s,encoding='utf-8')
defs=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(t).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
a,b=defs(original),defs(s);assert set(a)==set(b)and[k for k in a if a[k]!=b[k]]==['Controller']
for n in ['prompts.py','schema.py','qwen_backend.py','http_backend.py']:
    assert (sr/'defense'/n).read_bytes()==(release/'defense'/n).read_bytes()
tests=subprocess.run([sys.executable,'-m','unittest','test_minimum_price_reason_scope','test_price_history_binding'],cwd=release,capture_output=True,text=True)
(out/'new-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
terminal=Path(parent['terminal']['directory']);attempt=next(terminal.glob('runs/*/attempt-*'))
events=[json.loads(x)for x in(attempt/'events.jsonl').read_text(encoding='utf-8').splitlines()]
def before(seq):return copy.deepcopy([e['data']['public']for e in events if e['seq']<seq and e['kind']=='actor_request'][-1])
def actor(seq):return next(e['data']['text']for e in events if e['seq']==seq)
def refs_before(seq):
    refs=[];seen=set()
    for e in events:
        if e['seq']>=seq:break
        if e['kind']=='decision_accepted':
            obs=e['data']['observation_id'];pub=next(x['data']['public']for x in events if x['kind']=='observation'and x['data']['public']['observation_id']==obs)
            for im in pub['images']:
                if im['role']=='current'and im['sha256']not in seen:
                    seen.add(im['sha256']);refs.append({'observation_id':obs,'image_sha256':im['sha256'],'candidate':e['data']['candidate']})
    return refs
(out/'inputs').mkdir();(out/'images').mkdir();(out/'PRIVATE').mkdir();cases=[]
def save(identity,mode,pub,candidate,reference,origin):
    for im in list(pub['images'])+[{'sha256':r['image_sha256']}for r in reference]:
        source=attempt/(im['sha256']+'.image');assert sha(source.read_bytes())==im['sha256'];dest=out/'images'/(im['sha256']+'.png')
        if not dest.exists():shutil.copy2(source,dest)
    packet={'public':pub,'candidate':candidate,'reference_bank':reference,'candidate_origin':origin}
    path=out/'inputs'/(identity+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    cases.append({'id':identity,'mode':mode,'packet':'inputs/'+path.name,'packet_sha256':sha(path.read_bytes())})
pub=before(316);refs=refs_before(316)
save('p01','controller',pub,actor(316),refs,'Exact failed factual price-object claim under NEW blind binding condition; no GUI recapture/action replay')
save('p02','controller',pub,'I saw the cheaper $1.00 and $3.00 listings showing cards or card boxes, and other listings priced $5.00 showing a trash can, pins, binders, and game cartridges. I will go back to the results to inspect more evidence.\n<action>{"type":"back"}</action>',refs,'Authored price-only positive on identical original full legal history/images; not a natural actor or proof of task success')
save('p03','price_binding',pub,'I saw trash cans, pins, binders and game cartridges at $5.00; details of tiny figures and clothing remain uncertain.\n<action>{"type":"back"}</action>',refs,'Authored correct price-only relation with explicit tiny-image uncertainty')
save('p04','price_binding',pub,'I cannot confirm the prices of items I saw; I will inspect the $1.00 and $3.00 entries.\n<action>{"type":"back"}</action>',refs,'Authored uncertainty and future plan, not a claim of confirmed historical price pairing')
save('p05','price_binding',before(17),'I previously saw a trash can priced $1.00.\n<action>{"type":"click","x":302,"y":418}</action>',[],'Authored missing historical source negative on actual original form frame, no synthesized image')
save('w01','routing',pub,'I saw listings with $5.00 prices. I will wait.\n<action>{"type":"wait"}</action>',refs,'Authored pure native WAIT routing control; no new natural WAIT')
save('m01','verify',before(297),actor(297),refs_before(297),'Exact minimum candidate under NEW internal reason consistency, all original source frames bound; no automatic success')
save('m02','verify',before(297),'I cannot verify a global minimum because the tiny cheaper item images do not resolve the clothing detail. I have reached the $5.00 Rick Pitino book with a visible man in a suit; I report this navigation while leaving the comparison unconfirmed.\n<action>{"type":"stop","answer":"Reached the Rick Pitino book at $5.00; the cheaper-item visual exclusions and global minimum remain unconfirmed."}</action>',refs_before(297),'Authored limited progress/cheaper-prefix uncertainty control; only main verification, not official completion')
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':28,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'original_source_terminal_sha256':parent['terminal']['terminal_sha256']},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'p01':'Actual wrong price-object history must not be accepted; native BACK itself lawful','p02':'Correct item-price bindings; no tiny detail/global claim added','p03':'Price-only positive, clothing unknown','p04':'No definite past price assignment','p05':'Historical pairing unavailable, not a proven false observation','w01':'WAIT excluded, authored, route should skip','m01':'Do not certify minimum from acknowledged-prefix/equal-price logical explanation. Tiny cheaper cards still unresolved.','m02':'Limited navigation report only, not task proof','single_known_task_selected_development':True,'private_not_transferred':True},indent=2))
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
pointer={'directory':str(out),'release':str(release),'cases':len(cases),'max_calls':28,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'private_review_sha256':sha((out/'PRIVATE/review-before-inference.json').read_bytes()),'only_Controller_AST_changed':True,'validators_Limits_native_backends_unchanged':True,'formal_release':False}
(P/'current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
