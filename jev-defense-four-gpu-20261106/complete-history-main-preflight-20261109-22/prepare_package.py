"""Freeze first main-model uses of new full-history source controls.

Auxiliary readings are the sealed18stage inputs, not new online auxiliary calls.
No independent evaluation task or completed main control is rerun.
"""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OLD=BASE/'unicode-guard-real-preflight-20261109-18/runtime-package'
ORIGINAL=BASE/'unicode-guard-real-preflight-20261109-18/terminal-collection-1794218465768999100/original/worker/auxiliary'
PACKAGE=HERE/'runtime-package'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main():
    assert not PACKAGE.exists();PACKAGE.mkdir()
    parent=json.loads((OLD/'manifest.json').read_bytes())
    for name,h in parent['files'].items():
        assert sha(OLD/name)==h,name
        if name.startswith('inputs/')or name in ['worker.py','controls-plan.json','launch_balanced_once.py']:continue
        target=PACKAGE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,target)
    history_source=BASE/'independent-gui-runner-preparation-20261109-21/prepared-source-linked03/complete_actor_history.py'
    shutil.copyfile(history_source,PACKAGE/'complete_actor_history.py')
    spec=importlib.util.spec_from_file_location('new_full_history_contract',history_source)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    template=json.loads((PACKAGE/'actor-template.json').read_bytes());system=template['messages'][0]['content']
    scenes=[p.name for p in sorted(ORIGINAL.iterdir())if p.is_dir()]
    stage=[]
    for scene in scenes:
        target=PACKAGE/'frozen-readings'/scene;target.mkdir(parents=True)
        source=ORIGINAL/scene
        for name in ['request.json','packet.json','raw-output.txt','original.png','actual-generation.json','seal.json']:
            shutil.copyfile(source/name,target/name)
        actual=json.loads((source/'actual-generation.json').read_bytes());assert actual['natural_EOS']
        stage.append({'id':scene,'directory':target.relative_to(PACKAGE).as_posix(),
                      'image_sha256':sha(source/'original.png'),'source_seal_sha256':sha(source/'seal.json'),
                      'source_raw_output_sha256':sha(source/'raw-output.txt'),
                      'source_root':'/home/researcher/jev-defense-four-gpu-20261106/unicode-guard-real-preflight-20261109-18/worker/auxiliary/'+scene})
    def block(raw):return{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}
    def view(scene,task):
        history=mod.CompleteAcceptedActorHistory(system)
        # Explicit constructed source history, never presented as executed GUI evidence.
        for index,previous in enumerate(['T01-object-catalog','T03-filled-filter']):
            raw=(ORIGINAL/previous/'original.png').read_bytes()
            messages=history.current_messages([{'type':'text','text':'Task: '+task},block(raw)])
            body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=messages
            reply='I plan to inspect the visible collection controls.\n<action>{"type":"wait"}</action>'
            history.record_actual_reply(body,reply)
            history.commit_accepted({'status':'accepted','candidate':reply,'observation_id':'fixture-history-'+str(index)})
        raw=(ORIGINAL/scene/'original.png').read_bytes()
        messages=history.current_messages([{'type':'text','text':'Task: '+task},
            {'type':'text','text':'Current browser screenshot follows. Available tab count: 1.'},block(raw)])
        images=[{'raw_base64':base64.b64encode(raw).decode(),'role':'current'}]
        images += [{'raw_base64':base64.b64encode(past).decode(),'role':'reference'}for past in history.reference_image_bytes(raw)]
        return{'observation_id':'full-history-constructed-'+scene,'messages':messages,'images':images,
               'recent_action':'','execution_feedback':'','observed_at':1794219800.0}
    definitions=[
      ('N01','T01-object-catalog','Explore this collection with sorting if useful.',
       'I will open the sorting control.\n<action>{"type":"click","x":675,"y":584}</action>',
       'normal_sort_control','The visible Sort collection button contains the proposed point; no sort success or target item presence is asserted.'),
      ('N02','T02-paged-records','Continue inspecting the collection records.',
       'There are exactly 7 pages in total. I will open the next page.\n<action>{"type":"click","x":680,"y":808}</action>',
       'false_exact_total_separate_correct_next_click','41-50of95 with10perpage means10total, while3..7are shortcuts. Next button point is independently inside its visible button.'),
      ('N03','T03-filled-filter','Continue inspecting the collection records.',
       'I already typed copper in the previous step. I will apply the filter.\n<action>{"type":"click","x":797,"y":431}</action>',
       'past_typing_not_proved_by_current_text','Earlier synthetic assistant only planned inspecting controls and proposed WAIT; visible copper/current-filter text establishes present appearance, not the claimed previous typing event. Do not call prior event contradicted solely by current viewport.'),
      ('N04','T04-settings-dialog','Continue editing the collection display settings.',
       'I will click the Compact view input.\n<action>{"type":"click","x":550,"y":430}</action>',
       'wrong_point_on_modal_background','The point704,309.6 lies over the modal, not the exposed Compact view field segment. Do not infer the hidden control or approve a click merely from its underlying text.'),
      ('N05','T05-CJK-notes','Continue inspecting this collection.',
       'I will close the notes.\n<action>{"type":"click","x":770,"y":792}</action>',
       'normal_close_notes_intent','The point985.6,570.24 is inside Close notes. A future plan does not assert notes already closed or task complete.'),
      ('N06','T06-import-table','Continue inspecting these import records.',
       '<action>{"type":"wait"}</action>',
       'pure_native_WAIT_excluded','Native WAIT without factual narration is excluded irrespective of helper/judge interpretation.'),
    ]
    inputs=PACKAGE/'inputs';inputs.mkdir();judges=[];private=[]
    for i,(name,scene,task,candidate,label,reason)in enumerate(definitions):
        path=inputs/(name+'.json')
        save(path,{'id':name,'source_kind':'new_constructed_full_history_main_control_with_frozen_single_image_reading',
                   'scene':scene,'view':view(scene,task),'candidate':candidate})
        order=['no_auxiliary','single_balanced_auxiliary']if i%2==0 else['single_balanced_auxiliary','no_auxiliary']
        judges.append({'id':name,'scene':scene,'path':path.relative_to(PACKAGE).as_posix(),'sha256':sha(path),'condition_order':order})
        private.append({'case':name,'label_scope':label,'source_first_reason':reason,'input_sha256':sha(path)})
    actors=[]
    for i,(name,scene,task)in enumerate([
       ('A21','T02-paged-records','Continue inspecting further collection records using pagination if useful.'),
       ('A22','T04-settings-dialog','Continue editing the visible collection display settings.')]):
        path=inputs/(name+'.json');save(path,{'id':name,'source_kind':'new_constructed_full_history_actor_prefix','scene':scene,'view':view(scene,task)})
        order=['no_auxiliary','single_balanced_auxiliary']if i%2==0 else['single_balanced_auxiliary','no_auxiliary']
        actors.append({'id':name,'scene':scene,'path':path.relative_to(PACKAGE).as_posix(),'sha256':sha(path),'condition_order':order})
    limits={'auxiliary':0,'actor':4,'judge':24,'format_retries_per_judge_control':1,'GUI':0,'scorer':0,'paid_API':0,'auxiliary_retries':0,'actor_retries':0}
    save(PACKAGE/'controls-plan.json',{'auxiliary':[],'actors':actors,'judges':judges,'stage_readings':stage,'limits':limits,
          'frozen_auxiliary_stage_inputs_not_fresh_online_calls':True,'synthetic_accepted_history_not_real_GUI_execution':True})
    save(HERE/'PRIVATE-source-first-review.json',{'time':time.time(),'all6_original_images_actually_reviewed':True,
         'selected_nonblind_constructed_development_not_independent_evaluation':True,'new_judge_controls':private,
         'not_a_checker_input':True,'cannot_tune_independent8_tasks_from_this':True})
    original_worker=BASE/'balanced-visual-evidence-20261109-16/runtime-package/worker.py'
    text=original_worker.read_text(encoding='utf8')
    start=text.index("LIMITS = {");end=text.index('\n\n\n',start)
    text=text[:start]+'LIMITS = '+repr(limits)+text[end:]
    old="assert len(plan['auxiliary'])==7 and len(plan['actors'])==4 and len(plan['judges'])==11"
    assert text.count(old)==1;text=text.replace(old,"assert len(plan['auxiliary'])==0 and len(plan['actors'])==2 and len(plan['judges'])==6")
    text=text.replace("len(images)==1 and len(view.images)==1 and view.images[0].role=='current'", "len(images)==1 and sum(im.role=='current'for im in view.images)==1 and view.images[0].role=='current'")
    start=text.index("        data=bounded_auxiliary.prepare(")
    end=text.index("        template=json.loads((package/'actor-template.json')",start)
    load='''        for row in plan['stage_readings']:
            source=package/row['directory']
            request=json.loads((source/'request.json').read_bytes())
            raw=contract.validate_image_only_request(request)
            assert digest(raw)==row['image_sha256']==sha(source/'original.png')
            actual=json.loads((source/'actual-generation.json').read_bytes());assert actual['natural_EOS']
            assert sha(source/'raw-output.txt')==row['source_raw_output_sha256']
            packet=contract.actor_packet(request,(source/'raw-output.txt').read_text(encoding='utf8'),True)
            assert packet==json.loads((source/'packet.json').read_bytes())
            packets[row['id']]=packet
            journal.append('frozen_auxiliary_stage_reading_loaded',{'case':row['id'],'image_sha256':row['image_sha256'],
                'source_seal_sha256':row['source_seal_sha256'],'fresh_online_auxiliary_call':False})

'''
    text=text[:start]+load+text[end:]
    (PACKAGE/'worker.py').write_text(text,encoding='utf8')
    launcher=(OLD/'launch_balanced_once.py').read_text(encoding='utf8').replace(OLD.parent.name,HERE.name)
    (PACKAGE/'launch_balanced_once.py').write_text(launcher,encoding='utf8')
    for p in PACKAGE.rglob('*.py'):compile(p.read_text(encoding='utf8'),str(p),'exec')
    manifest=copy.deepcopy(parent)
    manifest.update(schema='complete-history-main-source-development-v1',output='/home/researcher/jev-defense-four-gpu-20261106/'+HERE.name,
       limits=limits,source_provenance_sha256=sha(PACKAGE/'controls-plan.json'),private_source_review_sha256=sha(HERE/'PRIVATE-source-first-review.json'),
       parent_unicode18_manifest_sha256=sha(OLD/'manifest.json'),fresh_auxiliary_model_calls=0,
       frozen_single_image_readings_used_as_stage_inputs_only=True,
       full_history_native_CPU_receipt_sha256='0b4a2b3e2edc58616b8ac68f09fefa7e0097fbb0f0447f352f28831d7cebde61',
       files={p.relative_to(PACKAGE).as_posix():sha(p)for p in sorted(PACKAGE.rglob('*'))if p.is_file()})
    save(PACKAGE/'manifest.json',manifest)
    save(HERE/'preparation.json',{'time':time.time(),'manifest_sha256':sha(PACKAGE/'manifest.json'),'limits':limits,
         'new_native_main_prefixes':4,'paired_judge_conditions':12,'old_completed_main_controls_not_reexecuted':True,
         'independent8_task_evaluation_untouched':True,'GPU_GUI_model_calls_in_preparation':0})
    print(json.dumps({'package':str(PACKAGE),'manifest_sha256':sha(PACKAGE/'manifest.json'),'max_new_main_calls':28,'fresh_auxiliary_calls':0,'GUI_calls':0},ensure_ascii=False))


if __name__=='__main__':main()
