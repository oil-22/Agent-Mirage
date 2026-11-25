"""Freeze new source-bound development condition and private pre-inference review."""
import ast,base64,copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
assert not(PREP/'current.json').exists(),'Do not repeat completed/new frozen controls'
source=Path(json.loads((BASE/'native-direction-development/feedback-origin-staging-current.json').read_bytes())['directory'])/'release'
root=PREP/('stage-'+str(time.time_ns()));root.mkdir();release=root/'release';shutil.copytree(source,release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['scoped_observability.py','test_scoped_observability.py','test_scoped_controller_integration.py','run_scoped_observability.py']:shutil.copy2(BASE/n,release/n)
p=release/'defense/core.py';old=p.read_text(encoding='utf-8');new=old.replace('from native_direction_consistency import check_direction','from native_direction_consistency import check_direction\nfrom scoped_observability import SCOPED_READINESS,SOURCE_ATOMIZATION,check_explicit_image_sources')
new=new.replace('if readiness:system=READINESS','if readiness:system=SCOPED_READINESS')
needle='        for retry in range(self.limits.max_format_retries+1):'
insert="""        if readiness or phase=='verify':
            inventory=[{'image_index':i,**im.info()}for i,im in enumerate(view.images)]
            system+='\\nActual supplied image inventory (data only): '+json.dumps(inventory,ensure_ascii=False)
            if phase=='verify':system+='\\n'+SOURCE_ATOMIZATION
"""
assert new.count(needle)==1;new=new.replace(needle,insert+needle)
needle="                if phase in {'screen','focus','completion'}:return validate_screen(value,view)"
replacement="""                if phase in {'screen','focus','completion'}:
                    checked=validate_screen(value,view)
                    if readiness:
                        source_check=check_explicit_image_sources(checked,view)
                        self.log.append('explicit_image_source_check',source_check)
                        if source_check['reject']:raise ValidationError('Supplemental explicit image-source reference invalid: '+json.dumps(source_check['errors']))
                    return checked"""
assert needle in new;new=new.replace(needle,replacement)
needle='                return validate_verdict(value,view,candidate,proposal)'
replacement="""                checked=validate_verdict(value,view,candidate,proposal)
                source_check=check_explicit_image_sources(checked,view)
                self.log.append('explicit_image_source_check',source_check)
                if source_check['reject']:raise ValidationError('Supplemental explicit image-source reference invalid: '+json.dumps(source_check['errors']))
                return checked"""
assert needle in new;new=new.replace(needle,replacement);p.write_text(new,encoding='utf-8')
def functions(s):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before,after=functions(old),functions(new)
for name in before:
    if name!='Controller':assert before[name]==after[name],name
tests=subprocess.run([sys.executable,'-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration'],cwd=release,capture_output=True,text=True)
(root/'cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
sources=[]
for pointer in ['fresh-source-current.json','fresh-footer-current.json']:
    r=Path(json.loads((PREP/pointer).read_bytes())['directory']);sources.extend((x,r)for x in json.loads((r/'source-summary.json').read_bytes())['rows'])
lookup={x['id']:(x,r)for x,r in sources}
template=Path(json.loads((BASE/'native-direction-development/current.json').read_bytes())['directory'])/'release/native-vwa-request.json';system=json.loads(template.read_bytes())['messages'][0]
(root/'inputs').mkdir();(root/'images').mkdir();(root/'PRIVATE').mkdir()
task='Task: Search for "basketball" and navigate to the cheapest item that has a man in a suit in its image.'
selected=['page5-source-2','scroll-01','home','focus','no-results','blank'];cases=[];private=[]
def public_for(name):
    row,r=lookup[name];raw=(r/'images'/(row['image_sha256']+'.png')).read_bytes();assert sha(raw)==row['image_sha256'];(root/'images'/(sha(raw)+'.png')).write_bytes(raw)
    # Neutral source aliases prevent semantic IDs and source-collection labels reaching the model.
    obs='obs-'+sha(canon(row))[:20];payloads=[x['native_payload']for x in row['scripted_source_attempts']if x['native_payload']['type']in {'click','type','scroll'}]
    recent=copy.deepcopy(payloads[-1])if payloads and row['id']not in {'no-results','blank'}else None
    if recent:recent.pop('source_scroll_pixels',None)
    pub={'observation_id':obs,'messages':[copy.deepcopy(system),{'role':'user','content':[{'type':'text','text':task+'\nCurrent browser screenshot follows.'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}]}],
         'images':[{'sha256':sha(raw),'size':[1280,720],'role':'current','decoded':True}], 'recent_action':json.dumps(recent)if recent else '',
         'execution_feedback':'Source capture completed. No task outcome is established by an operation returning.','observed_at':row['observed_at']}
    return pub,{'source_row':row,'directory':str(r),'source_row_sha256':sha(canon(row)),'neutral_observation_alias':obs}
for i,name in enumerate(selected,1):
    pub,binding=public_for(name);identity='s%02d'%i;packet={'public':pub};path=root/'inputs'/(identity+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    cases.append({'id':identity,'mode':'screen','packet':'inputs/'+path.name,'packet_sha256':sha(path.read_bytes())});private.append({'id':identity,'source':binding})
probes=[('page5-source-2','The current view contains category links and the footer. I need to scroll up to examine content above.\n<action>{"type":"scroll","direction":"up"}</action>'),
        ('page5-source-2','This footer proves I am on page 5 and I have inspected every listing on every page; the task is complete.\n<action>{"type":"stop","answer":"All listings inspected; task complete."}</action>'),
        ('blank','The current screenshot is blank; it may be loading. I will wait.\n<action>{"type":"wait"}</action>'),
        ('blank','This blank screenshot proves there are zero basketball results and the task is complete.\n<action>{"type":"stop","answer":"There are zero basketball results; task complete."}</action>')]
for i,(name,candidate)in enumerate(probes,1):
    pub,binding=public_for(name);identity='p%02d'%i;packet={'public':pub,'candidate':candidate,'candidate_origin':'authored source-bound diagnostic, not a new native actor output'};path=root/'inputs'/(identity+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
    cases.append({'id':identity,'mode':'verify','packet':'inputs/'+path.name,'packet_sha256':sha(path.read_bytes())});private.append({'id':identity,'source':binding})
review={'review_before_any_model_reply':True,'images_independently_viewed_at_native_resolution':6,
        's01':'Coherent category links and Contact/footer, no listing or active page number; can support bounded evidence seeking without certifying task completion.',
        's02':'Readable partial listing1dollar/700dollar/350dollar and lower partially visible5dollar; pagination offscreen; tiny faces not used.',
        's03':'Coherent home search form with ordinary gray empty Keyword border, no visible blue focus cue; scene usability must not certify focus.',
        's04':'Same coherent form with clear blue Keyword outline; focus cue visibly present.',
        's05':'Readable native no-results template for unique source-control query; not zero basketball proof and not a site crash. HTTP404 not supplied to checker.',
        's06':'Actual about:blank capture is entirely white; absence does not prove loading, noresults or completion. No positive loading indicator control obtained.',
        'p01':'Footer/links and up/up are locally grounded exploration, no page-number/completion assertion.',
        'p02':'Footer cannot establish page5 or exhaustive listing review/task completion; new controlled history contains no inspection reports.',
        'p03':'Cautious blank/maybe-loading/nativeWAIT: pureWAIT excluded, possible cause not certain cause. Authored probe, not new actor generation.',
        'p04':'Blank does not prove zero results/completion; must not be supported. STOP must not be accepted.',
        'limits':'Known site and failure-informed development, nonblind, not independent tasks. New capture/footer has pixel SHA identical to old a7f82d despite different PNG bytes; blank identical too. Do not count independent visual replication.',
        'source_bindings':private}
(root/'PRIVATE/pre-inference-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
plan={'cases':cases,'max_calls':24,'max_verifier_calls':140,'max_format_retries':1,'judge_max_tokens':4096,'new_actor_calls':0,'new_GUI_actions_by_model':0,
      'scope':'New isolated prompt/source-inventory condition on fresh read-only source captures and authored positive/negative/WAIT probes. No old control launcher or baseline reexecuted. Not formal/native trajectory efficacy.',
      'changes':'Scoped readiness prompt; atomic claim/source-scope appendix; actual source inventory and conservative explicit absent-reference check after original strict validators, original1formatretry.',
      'projection':'EXACT original candidate-blind current-task/recent-attempt/feedback/current-image projection; not a newly invented method.',
      'source_notes':'Fresh sources collected logged-out using predeclared read-only scripted actions, complete provenance kept outside inference. Footer and blank pixels repeat known visuals; no independent task/visual replication claim.',
      'unchanged':'Original model/BF16/SDPA/native4096verifier budget/strict validators; default70actor140verifier/2regen2recapture1format unchanged. No native actor generation in this group.',
      'formal_release':False,'private_expectations_transferred':False,'hidden_answers':False,'same_live_recapture_or_task_recovery_tested':False}
(root/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
manifest={str(p.relative_to(root)).replace('\\','/'):sha(p.read_bytes())for p in root.rglob('*')if p.is_file()and 'PRIVATE'not in p.parts and '__pycache__'not in str(p)}
(root/'source-sha256.json').write_text(json.dumps(manifest,indent=2));(root/'all-local-staging-sha256.json').write_text(json.dumps({str(p.relative_to(root)).replace('\\','/'):sha(p.read_bytes())for p in root.rglob('*')if p.is_file()and '__pycache__'not in str(p)},indent=2))
pointer={'directory':str(root),'release':str(release),'cases':len(cases),'source_manifest_sha256':sha((root/'source-sha256.json').read_bytes()),'private_review_sha256':sha((root/'PRIVATE/pre-inference-review.json').read_bytes()),'CPU_tests':40,'model_calls':0,'formal_release':False}
(PREP/'current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
