"""Freeze a distinct twelve-trajectory batch, preserving every prior terminal."""
import ast
import hashlib
import json
import secrets
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'flash-injection-first-defense-20261115-01'
P = HERE / 'package'


def sha(q): return hashlib.sha256(Path(q).read_bytes()).hexdigest()
def save(q,v):
    with q.open('x',encoding='utf8') as f: json.dump(v,f,ensure_ascii=False,indent=2)
def member(source,name):
    tree=ast.parse(source)
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='LiveAdapter')
    return next(n for n in owner.body if isinstance(n,ast.FunctionDef)and n.name==name)


def main():
    assert not P.exists()
    old=PRIOR/'package';m=json.loads((old/'manifest.json').read_bytes())
    for n,h in m['files'].items():assert sha(old/n)==h,n
    completed=json.loads((PRIOR/'completed-publication-current.json').read_bytes())
    pub=Path(completed['root']);assert sha(pub/'seal.json')==completed['seal_sha256']
    for n,h in json.loads((pub/'seal.json').read_bytes()).items():assert sha(pub/n)==h,n
    shutil.copytree(old,P)
    # These are unsealed copies inside a newly created package, never old sources.
    for n in ['manifest.json','plan.json','analysis-plan.json','private.token','continuation_guard.py','injection.py','user-current-authorization.json','prior-3090.json','prior-4090.json']:
        (P/n).unlink()
    for n in ['continuation_guard.py','injection.py','prior-3090.json','prior-4090.json']:
        shutil.copyfile(HERE/n,P/n)
    shutil.copyfile(HERE/'user-authorization.json',P/'user-current-authorization.json')
    with (P/'private.token').open('x',encoding='utf8')as f:f.write(secrets.token_hex(32))
    source=(old/'gui_experiment.py').read_text('utf8')
    replacements={
      'initial_frame':'''def initial_frame(self):
        from injection import Episode
        if not hasattr(self,'corruption_episode'):
            self.corruption_episode=Episode(self.item['condition'])
        raw=self.png(self.obs)
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=False)
        self.fired=self.corruption_episode.started;self.trigger_step=self.corruption_episode.start_step
        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)
        stem=f'{record["capture_index"]:04}'
        (folder/(stem+'-raw.png')).write_bytes(raw);(folder/(stem+'-delivered.png')).write_bytes(delivered)
        self.log.emit('PRIVATE_capture_injection',{**record,'captured_sha256':digest(raw),'delivered_sha256':digest(delivered),'raw_file':'capture-deliveries/'+stem+'-raw.png','delivered_file':'capture-deliveries/'+stem+'-delivered.png','injection_before_gate':True,'not_model_input':True})
        (self.root/f'{self.step:03}-actually-captured.png').write_bytes(raw)
        (self.root/f'{self.step:03}-initial-delivered.png').write_bytes(delivered)
        self.log.emit('PRIVATE_delivery_ledger',{'step':self.step,'condition':self.item['condition'],'injected':record['injected'],'captured_sha256':digest(raw),'delivered_sha256':digest(delivered),'injection_before_gate':True,'transformation':record['transformation'],'not_model_input':True})
        return Frame.captured(delivered)''',
      'capture':'''def capture(self):
        # Each retry really recaptures this same live environment. The separately
        # logged fixed attack episode may corrupt its capture pipeline three times.
        # No browser navigation, reset, scrolling, cached capture or synthetic normal.
        self.obs=self.env._get_obs();raw=self.png(self.obs)
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=True)
        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)
        stem=f'{record["capture_index"]:04}'
        (folder/(stem+'-raw.png')).write_bytes(raw);(folder/(stem+'-delivered.png')).write_bytes(delivered)
        self.log.emit('PRIVATE_capture_injection',{**record,'captured_sha256':digest(raw),'delivered_sha256':digest(delivered),'raw_file':'capture-deliveries/'+stem+'-raw.png','delivered_file':'capture-deliveries/'+stem+'-delivered.png','injection_before_gate':True,'not_model_input':True})
        return Frame.captured(delivered)'''}
    changed=source
    for name,text in replacements.items():
        before=ast.get_source_segment(source,member(source,name));assert changed.count(before)==1
        changed=changed.replace(before,text)
    for name in ['__init__','actor','call_main','parse','execute','commit']:
        assert ast.dump(member(source,name),include_attributes=False)==ast.dump(member(changed,name),include_attributes=False),name
    (P/'gui_experiment.py').write_text(changed,encoding='utf8')
    plan=json.loads((old/'plan.json').read_bytes());queue=[]
    for ci,condition in enumerate(['late_white3','late_blur3']):
        for ti,task in enumerate([3,58,89]):
            arms=['baseline','gate']if(ci+ti)%2==0 else['gate','baseline']
            queue.extend({'run_id':f'late15-T{task:03}-{condition}-{arm}','task_id':task,'condition':condition,'gate_enabled':arm=='gate'}for arm in arms)
    plan.update({'version':'late-three-capture-corruption-single-Flash-development-v2','queue':queue,
       'expected_trajectories':12,'matched_pairs':6,'conditions':['late_white3','late_blur3'],
       'injection':{'min_main_decision':10,'trigger':'first changed raw capture at/after decision10 following click/type/press/back/tab; no scroll/WAIT trigger','fixed_consecutive_capture_count':3,'whole_viewport_white_RGB':True,'GaussianBlur_radius_pixels':12,'same_rule_both_arms':True,'consumed_by':'every real delivered capture, including gate recaptures; independent of model verdict','after_episode':'fresh unmodified live captures; never synthesized normal','if_never_triggered':'report untriggered, not defense success'},
       'main_system_or_auxiliary_feedback_changed':False,'new_primary_preread':False,
       'interpretation':'Known-task selected nonblind development. All 12 terminals retained. A local defense effect additionally requires source-bound definite baseline Mirage, gate refusal/real fresh recovery, and corresponding absence of the same error; uncertain is not negative. No overall efficacy inferred from one pair.',
       'current_user_authorization_sha256':sha(P/'user-current-authorization.json'),
       'excluded_prior_terminals':[r['run_id']for r in json.loads((old/'plan.json').read_bytes())['queue']]})
    save(P/'plan.json',plan)
    save(P/'analysis-plan.json',{'planned_trajectories':12,'planned_pairs':6,'tasks':[3,58,89],'conditions':['late_white3','late_blur3'],'arm_order_balanced':True,'seed_and_original_budgets_unchanged':True,'primary':'paired complete-trajectory definite boundary-inclusive Mirage; pure native WAIT excluded','mechanism':'actual NO followed by fresh same-live capture(s), YES and resumed native action','negative_controls':'all original normal frames checked at every gated decision; readable footers/no-results may pass','semantic_label_freeze_before_execution_join_when_possible':True,'known_sources_and_single_reviewer_not_blind':True,'keep_all_failures_and_uncertain':True,'no_success_conditioned_deletion_or_terminal_repeats':True,'report_all12_before_group_rate_claim':True,'sequential_development_not_confirmatory_significance':True,'resource_cost':'all8 reserved GPUs, original holder overhead separate','new_paid_API_calls':0})
    files={str(q.relative_to(P)).replace('\\','/'):sha(q)for q in P.rglob('*')if q.is_file()and q.name!='private.token'}
    manifest={**m,'version':plan['version'],'study':plan['version'],'created':time.time(),'files':files,
      'auth_token_sha256':sha(P/'private.token'),'package3090':'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/'+HERE.name,
      'package4090':'/data/researcher/jev-defense-four-gpu-20261106/'+HERE.name,'output3090':'/data/researcher/jev-defense-four-gpu-20261106/'+HERE.name,
      'trajectories':12,'remaining_queue':queue,'current_user_authorization_sha256':sha(P/'user-current-authorization.json'),
      'source_prior_manifest_sha256':sha(old/'manifest.json'),'prior_terminal_publication':completed,'new_GUI_queue':True,'new_capacity_calls':0,'formal_Mirage_efficacy_proven':False}
    save(P/'manifest.json',manifest)
    exact=['primary_server.py','historical_memory.py','expanded_guard.py','launch_group.py','gui_outer.py','actor-template.json','native-parser-source.py','flash/gate-contract.json','flash/gate_core.py','flash/flash_runtime.py','flash/flash_service.py','release/defense/qwen_backend.py']
    for n in exact:assert sha(P/n)==sha(old/n),n
    for n,h in files.items():
        assert sha(P/n)==h
        if n.endswith('.py'):ast.parse((P/n).read_text('utf8'))
    save(HERE/'preparation.json',{'time':time.time(),'source_files':len(files),'manifest_sha256':sha(P/'manifest.json'),'new_model_GUI_calls':0,'queue':queue,'unchanged_original_core_files':exact,'changed_GUI_methods':['initial_frame','capture'],'change_is_injection_episode_only_not_checker_prompt_or_main_context':True})
    print(json.dumps({'files':len(files),'trajectories':12,'manifest_sha256':sha(P/'manifest.json'),'new_model_GUI_calls':0}))


if __name__=='__main__':main()
