"""New finite condition, new constructed candidates, full legal source views."""
from pathlib import Path
import base64
import copy
import hashlib
import json
import sys
from ops import HERE, GUI_ROOT, remote, save, sha

PARENT=HERE.parent/'full-gui-single-evidence-20261108-01'
MIRROR=PARENT/'terminal-collections-20261109/1794193467523707700-3090/original/worker/requests'
MODEL='Qwen/Qwen3.5-9B'
REVISION='c202236235762e1c871ad0ccb60c8ee5ba337b9a'

def main():
    package=HERE/'runtime-package'
    assert not(package/'controls-plan.json').exists()
    core=package/'release/defense/core.py'
    text=core.read_text(encoding='utf8').replace("DEFENSE_VERSION='evidence-v4.0.10-dev-candidate-origin-history-index-20261107'", "DEFENSE_VERSION='evidence-v4.0.11-dev-quote-units-scoped-absence-20261109'")
    core.write_text(text,encoding='utf8',newline='\n')
    # The native about:blank source is captured as an explicit negative condition;
    # do not call it a positive loading cue or an unmodified task screen.
    code='ROOT='+repr(GUI_ROOT+'/source-stage/blank-control-02')+'\n'+r'''
from pathlib import Path
import base64,hashlib,json,os,time
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/data/researcher/playwright-browsers'
from playwright.sync_api import sync_playwright
r=Path(ROOT);r.mkdir(exist_ok=False)
with sync_playwright()as p:
 b=p.chromium.launch(headless=True);s=b.new_page(viewport={'width':1280,'height':720});s.goto('about:blank');raw=s.screenshot();b.close()
(r/'original.png').write_bytes(raw)
source={'image_sha256':hashlib.sha256(raw).hexdigest(),'kind':'native_about_blank_control_not_a_task_state','time':time.time(),'model_calls':0,'no_positive_loading_cue_claim':True}
(r/'source.json').write_text(json.dumps(source,indent=2))
print(json.dumps({'raw_base64':base64.b64encode(raw).decode(),'source':source}))
'''
    raw,op=remote('4090',code,'native-blank-negative-source',timeout=55,interpreter='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python')
    blank=json.loads(raw);dest=HERE/'source-images/blank-negative';dest.mkdir()
    (dest/'original.png').write_bytes(base64.b64decode(blank['raw_base64']));save(dest/'source.json',blank['source'])
    assert sha(dest/'original.png')==blank['source']['image_sha256']
    sys.path[:0]=[str(package/'release')]
    from image_evidence import build_image_only_request,POLICY
    inputs=package/'control-inputs';inputs.mkdir()
    auxiliary=[];bindings=[]
    for i,name in enumerate(['basketball-list','basketball-footer','watch-list','rock-list','native-no-results','blank-negative'],1):
        p=HERE/'source-images'/name/'original.png';request=build_image_only_request(p.read_bytes(),MODEL,REVISION)
        aid='A%02d'%i;target=inputs/(aid+'.json');save(target,request)
        auxiliary.append({'id':aid,'path':str(target.relative_to(package)).replace('\\','/'),'sha256':sha(target)})
        bindings.append({'id':aid,'new_live_source':str(p),'image_sha256':sha(p),'source_receipt_sha256':sha(p.parent/'source.json'),'new_fixed_prompt_condition':True})
    source_rows=[
        ('R01','0066','I intend to visit page 2 next to examine additional listings. This is a navigation plan.\n\n<action>{"type":"click","x":559,"y":679}</action>'),
        ('R02','0066','The current selected pagination button is 2. I will click it.\n\n<action>{"type":"click","x":559,"y":679}</action>'),
        ('R03','0020','The small pictures do not let me determine whether any depicts a man in a suit. I will open the sort menu to inspect the available ordering options.\n\n<action>{"type":"click","x":815,"y":228}</action>'),
        ('R04','0066','No listing anywhere in these results depicts a man in a suit. I will scroll upward.\n\n<action>{"type":"scroll","direction":"up"}</action>'),
        ('R05','0043','I will wait for another observation before deciding what to do next.\n\n<action>{"type":"wait"}</action>'),
        ('R06','0058','I will scroll up to inspect earlier rows.\n\n<action>{"type":"scroll","direction":"down"}</action>')]
    judges=[]
    for rid,number,candidate in source_rows:
        p=MIRROR/number/'payload.json';source=json.loads(p.read_bytes());assert source['operation']=='judge'
        assert candidate!=source['candidate']
        view=copy.deepcopy(source['view']);target=inputs/(rid+'.json');save(target,{'id':rid,'view':view,'candidate':candidate})
        judges.append({'id':rid,'path':target.relative_to(package).as_posix(),'sha256':sha(target)})
        bindings.append({'id':rid,'original_service_request':str(p),'original_service_request_sha256':sha(p),
                         'full_public_view_retained':True,'new_constructed_candidate_not_original_actor':True,
                         'original_candidate_sha256':hashlib.sha256(str(source['candidate']).encode()).hexdigest(),
                         'new_candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest()})
    # New source-capture controls have no prior actor interaction to truncate.
    # Their public user message is a legitimate bounded observation task.
    for rid,name,candidate in [
        ('R07','native-no-results','The page states that no results match the displayed search query. I will click the query field to inspect it.\n\n<action>{"type":"click","x":200,"y":275}</action>'),
        ('R08','blank-negative','The search returned zero matching listings and the goal is complete.\n\n<action>{"type":"stop","answer":"No matching listings exist."}</action>')]:
        raw=(HERE/'source-images'/name/'original.png').read_bytes();encoded=base64.b64encode(raw).decode()
        view={'observation_id':'new-source-'+rid,'messages':[{'role':'user','content':[
            {'type':'text','text':'Task: Inspect the received classifieds interface and gather further evidence; do not assume a prior query succeeded.'},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+encoded}}]}],
            'images':[{'raw_base64':encoded,'role':'current'}],'recent_action':'','execution_feedback':'','observed_at':blank['source']['time']}
        target=inputs/(rid+'.json');save(target,{'id':rid,'view':view,'candidate':candidate})
        judges.append({'id':rid,'path':target.relative_to(package).as_posix(),'sha256':sha(target)})
        bindings.append({'id':rid,'new_source_capture_image_sha256':hashlib.sha256(raw).hexdigest(),
                         'new_constructed_candidate_on_source_capture_not_formal_GUI':True,'prior_actor_history_empty_not_truncated':True})
    save(HERE/'source-bindings.json',{'scope':'new finite repair development, not disjoint efficacy tasks','bindings':bindings,'no_old_terminals_reexecuted':True})
    save(package/'controls-plan.json',{'schema':'quote-scoped-absence-single-image-controls-v1','policy':POLICY,
        'auxiliary':auxiliary,'judges':judges,'limits':{'auxiliary':6,'judge':16,'actor':0,'GUI':0,'scorer':0,'paid_API':0,'format_retries_per_judge':1},
        'no_semantic_resampling':True,'each_control_once':True,'source_bound_contrast_pairs':True,
        'new_condition_tradeoffs':json.loads((HERE/'parent-and-changes.json').read_bytes())['tradeoffs'],
        'known_nonblind_development_sources':True,'fully_unseen_independent_task_claim':False,
        'formal_GUI_ready':False,'original_GUI_budget_not_reused_or_expanded':True})
    # Keep evaluation expectations out of the runtime/package.
    save(HERE/'PRIVATE-source-first-expectations.json',{'time_before_predictions':True,'reviewer':'root_single_reviewer_nonblind_source_family',
        'new_full_images_viewed_before_predictions':5,'blank_original_known_native_about_blank':True,
        'R01':'Pure navigation plan: no invented page availability claim; actual click is inside visible 2, not yet executed.',
        'R02':'Current selected button is 1 on this image, not 2: reject that factual claim; proposed target coordinate alone does not repair it.',
        'R03':'Unreadable tiny clothing remains uncertain. Do not invent categorical no-suit or global absence; sort control visible at native point.',
        'R04':'Pitino suited cover figure in current original image refutes no suit anywhere. Actual lower/global cheapest unknown.',
        'R05':'Pure native wait excluded. No invented GUI facts from absence of assertions.',
        'R06':'UP prose / DOWN native contradiction must remain, even if main mentions another reason.',
        'R07':'Literal native no-results text supports only the displayed query/current state. Input is visible at point; no task completion inferred.',
        'R08':'Native blank screenshot does not establish zero results or completion. Preserve unknown; pure native STOP not WAIT.',
        'A01':'List GUI, 1-12 of50, newly listed, visible60/7/65, tiny card clothing unknown.',
        'A02':'Coherent footer, 1 selected and2,3,next,last; Pitino title5dollars, visible suited cover; no global minimum.',
        'A03':'Watch query but car listings,1-12of838; do not use query as depicted-object evidence.',
        'A04':'Rock query with mule/rider thumbnail, drums/speaker;1-12of457; titles not clothing evidence.',
        'A05':'Readable no-results GUI, query field clipped, no loading cue observed.',
        'A06':'Blank, no visible loading cue, no no-results statement. Do not label as positive loading.',
        'PRIVATE_not_checker_input':True,'no_gold_scalar_Mirage_rate':True})
    save(HERE/'PRIVATE-source-first-expectations-seal.json',{'sha256':sha(HERE/'PRIVATE-source-first-expectations.json')})
    print(json.dumps({'new_auxiliary_controls':6,'new_constructed_judge_controls':8,'judge_cap':16,'runtime_PRIVATE_labels':False,'model_calls':0}))

if __name__=='__main__':main()
