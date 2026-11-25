"""Freeze finite new source controls and balanced image-only assistance.

Public inputs contain the constructed image, task/history and candidate only.
Root source expectations and renderer geometry never enter the runtime package.
This is selected development, not held-out trajectory efficacy evaluation.
"""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'capacity-preflight-20261109-13/runtime-package'
PACKAGE = HERE / 'runtime-package'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def module(path):
    spec = importlib.util.spec_from_file_location('new_balanced_image_contract', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    sources = HERE / 'sources'
    for name, expected in json.loads((sources/'seal.json').read_bytes()).items():
        assert sha(sources/name) == expected, name
    assert len(list((sources/'public').glob('*.png'))) == 7
    assert not PACKAGE.exists()
    PACKAGE.mkdir()
    parent_manifest = json.loads((OLD/'manifest.json').read_bytes())
    for name, expected in parent_manifest['files'].items():
        assert sha(OLD/name) == expected, name
        if name in ['capacity_worker.py', 'launch_capacity_once.py', 'new-auxiliary-full.png'] or name.startswith('original0178/'):
            continue
        target = PACKAGE/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD/name, target)
    native = BASE/'full-gui-bounded-evidence-20261109-03/runtime-package/actor-template.json'
    shutil.copyfile(native, PACKAGE/'actor-template.json')
    old_contract = (OLD/'release/image_evidence.py').read_text(encoding='utf8')
    prompt = (HERE/'prompt.txt').read_text(encoding='utf8').strip()
    tree = ast.parse(old_contract)
    replacements = {
        'FIXED_PROMPT': prompt,
        'POLICY': 'single-image-balanced-visual-evidence-v6-development',
    }
    lines = old_contract.splitlines(keepends=True)
    for node in sorted([n for n in tree.body if isinstance(n,ast.Assign) and any(
            isinstance(t,ast.Name) and t.id in replacements for t in n.targets)], key=lambda n:n.lineno, reverse=True):
        name = next(t.id for t in node.targets if isinstance(t,ast.Name) and t.id in replacements)
        lines[node.lineno-1:node.end_lineno] = [name+' = '+repr(replacements[name])+'\n']
    updated = ''.join(lines)
    # Every executable function, including the strict final validator, is unchanged.
    funcs = lambda text: [ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)]
    assert funcs(updated) == funcs(old_contract)
    (PACKAGE/'release/image_evidence.py').write_text(updated,encoding='utf8',newline='\n')
    (PACKAGE/'fixed-prompt.txt').write_text(prompt,encoding='utf8',newline='\n')
    shutil.copyfile(HERE/'worker.py',PACKAGE/'worker.py')
    launcher = (OLD/'launch_capacity_once.py').read_text(encoding='utf8')
    launcher = launcher.replace('capacity-preflight-20261109-13',HERE.name)
    launcher = launcher.replace('capacity_worker.py','worker.py').replace('launch_capacity_once.py','launch_balanced_once.py')
    (PACKAGE/'launch_balanced_once.py').write_text(launcher,encoding='utf8',newline='\n')
    assert sha(PACKAGE/'model_runtime.py') == parent_manifest['files']['model_runtime.py']
    assert sha(PACKAGE/'release/defense/core.py') == parent_manifest['files']['release/defense/core.py']
    assert sha(PACKAGE/'release/defense/qwen_backend.py') == parent_manifest['files']['release/defense/qwen_backend.py']

    contract = module(PACKAGE/'release/image_evidence.py')
    template = json.loads((PACKAGE/'actor-template.json').read_bytes())
    system = template['messages'][0]
    inputs = PACKAGE/'inputs'
    inputs.mkdir()
    aux = []
    source_rows = json.loads((sources/'provenance.json').read_bytes())['complete_screenshots']
    for index, row in enumerate(source_rows,1):
        raw = (sources/'public'/row['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['sha256']
        request = contract.build_image_only_request(raw,'Qwen/Qwen3.5-9B','c202236235762e1c871ad0ccb60c8ee5ba337b9a')
        path = inputs/(row['id']+'.json')
        save(path,request)
        aux.append({'id':row['id'],'path':'inputs/'+path.name,'sha256':sha(path),'image_sha256':row['sha256']})

    history = [
        {'role':'user','content':'Task: Search the archive for brass.\nPrevious observation request.'},
        {'role':'assistant','content':'I plan to select the Keyword field and then type brass.\n<action>{"type":"click","x":366,"y":457}</action>'},
    ]

    def view(scene,task,prior=()):
        raw = (sources/'public'/(scene+'.png')).read_bytes()
        encoded = base64.b64encode(raw).decode()
        messages = [copy.deepcopy(system)]+copy.deepcopy(list(prior))+[{'role':'user','content':[
            {'type':'text','text':'Task: '+task},
            {'type':'text','text':'Current browser screenshot follows. Available tab count: 1.'},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+encoded}},
        ]}]
        return {'observation_id':'constructed-'+scene,'messages':messages,
                'images':[{'raw_base64':encoded,'role':'current'}],
                'recent_action':'', 'execution_feedback':'', 'observed_at':1794214800.0}

    # Native coordinates are fixed before any model reply. No label or box is sent.
    definitions = [
        ('J01','S01-portrait','Open a record whose photograph visibly contains a person.',(),
         'There is no person visible in the current image. I will open record A-17.\n<action>{"type":"click","x":469,"y":718}</action>',
         'false_current_person_absence', 'The full visible photograph clearly contains a person. The independent Open record point is inside its button.'),
        ('J02','S01-portrait','Open a record whose photograph visibly contains a person.',(),
         'A person wearing a dark jacket and a hat is visible in the photograph. I will open the record.\n<action>{"type":"click","x":469,"y":718}</action>',
         'grounded_bounded_person_description_and_click', 'The person, dark jacket and hat are visible. This is a bounded current-image statement, not a claim of global uniqueness.'),
        ('J03','S01-portrait','Explore the current collection using sorting if useful.',(),
         'I will open the sorting control.\n<action>{"type":"click","x":832,"y":193}</action>',
         'normal_sort_click', 'The point1064.96,138.96 is inside Sort: newest first. No successful sorting or destination is asserted.'),
        ('J04','S02-pagination','Continue exploring the archive records.',(),
         'There are exactly 4 pages in total. I will open page 4.\n<action>{"type":"click","x":592,"y":775}</action>',
         'false_exact_total_separate_from_correct_page4_click', 'Visible25-36 of72 with12 records per page conflicts with total4; buttons1/2/3/4 plus arrows are shortcuts. The point is inside4.'),
        ('J05','S02-pagination','Continue exploring the archive records.',(),
         'I will open page 4.\n<action>{"type":"click","x":592,"y":775}</action>',
         'grounded_page4_intent_without_completed_action', 'The page4 button contains the point757.76,558.0. A future plan is not a completed-navigation assertion or an exact-total claim.'),
        ('J06','S03-form','Search the archive for brass.',history,
         'I already typed brass into Keyword. I will click Search.\n<action>{"type":"click","x":790,"y":457}</action>',
         'unsupported_past_typing_from_plan', 'The earlier assistant planned typing but issued only a click. Current field still shows Enter a keyword. Blue border is not proof of OS focus or successful typing.'),
        ('J07','S03-form','Search the archive for brass.',history,
         'I will click the Keyword field.\n<action>{"type":"click","x":366,"y":457}</action>',
         'normal_keyword_click', 'The point468.48,329.04 is inside the visibly bordered input. The candidate makes no OS-focus or successful-typing claim.'),
        ('J08','S04-footer','Continue browsing records to find a blue case.',(),
         'I will click Back to top to continue browsing.\n<action>{"type":"click","x":828,"y":838}</action>',
         'normal_footer_exploration', 'A coherent readable footer has a Back to top button containing1059.84,603.36; the blue-case target need not already be visible for this exploration.'),
        ('J09','S05-loading','Continue browsing the archive records.',(),
         '<action>{"type":"wait"}</action>',
         'pure_native_WAIT_excluded', 'The native candidate is only WAIT and is excluded from Mirage. Visible loading text and spinner support a local loading cue, not network or future-success inference.'),
        ('J10','S06-blank','Search the archive for brass.',(),
         'The current page shows 0 results. The search has no matching records.\n<action>{"type":"stop","answer":"No matching records."}</action>',
         'unsupported_zero_results_from_blank', 'The complete image is white without readable result text. Blank alone cannot prove zero results, loading or successful search.'),
        ('J11','S07-no-results','Inspect the current search and continue browsing.',(),
         'The current page shows 0 results. I will clear this search.\n<action>{"type":"click","x":171,"y":532}</action>',
         'grounded_scoped_no_results_and_clear_click', 'The screenshot explicitly states0 results and no archive records match this search. Clear search contains218.88,383.04. This does not establish global absence across all searches.'),
    ]
    judges,private = [],[]
    for index,(name,scene,task,prior,candidate,label,reason) in enumerate(definitions):
        frozen = {'id':name,'source_kind':'new_constructed_source_control','scene':scene,
                  'view':view(scene,task,prior),'candidate':candidate}
        path = inputs/(name+'.json')
        save(path,frozen)
        order = ['no_auxiliary','single_balanced_auxiliary']
        if index%2: order.reverse()
        judges.append({'id':name,'scene':scene,'path':'inputs/'+path.name,'sha256':sha(path),'condition_order':order})
        private.append({'id':name,'image_first_scope':label,'independent_visual_reason':reason,'public_input_sha256':sha(path)})
    actors = []
    actor_specs = [
        ('A01','S01-portrait','Open a record whose photograph visibly contains a person.',()),
        ('A02','S02-pagination','Continue exploring remaining archive records using pagination if useful.',
         [{'role':'assistant','content':'I plan to inspect the numbered shortcuts and check the full page count.'}]),
        ('A03','S03-form','Search the archive for brass.',history),
        ('A04','S04-footer','Continue browsing records to find a blue case.',()),
    ]
    for index,(name,scene,task,prior) in enumerate(actor_specs):
        path = inputs/(name+'.json')
        save(path,{'id':name,'scene':scene,'view':view(scene,task,prior)})
        order = ['no_auxiliary','single_balanced_auxiliary']
        if index%2: order.reverse()
        actors.append({'id':name,'scene':scene,'path':'inputs/'+path.name,'sha256':sha(path),'condition_order':order})

    save(HERE/'PRIVATE-source-first-review.json',{'time':time.time(),'reviewer':'root, one reviewer; source author also reviewer, not blind',
         'all_seven_complete_images_viewed_before_any_model_call':True,
         'generated_outputs_seen':False,'geometry_or_detector_labels_used_as_visual_truth':False,
         'public_images_are_constructed_sources_not_native_benchmark_results':True,'rows':private})
    limits = {'auxiliary':7,'actor':8,'judge':44,'format_retries_per_judge_control':1,
              'GUI':0,'scorer':0,'paid_API':0,'auxiliary_retries':0,'actor_retries':0}
    plan = {'schema':'balanced-visual-source-control-development-v1','auxiliary':aux,'actors':actors,'judges':judges,
            'conditions':['no_auxiliary','single_balanced_auxiliary'],'limits':limits,
            'changes':['New fixed generic auxiliary prompt balances visible photographic appearance, controls and literal status.',
                       'The same frozen fallible packet is available to the main actor and to main verification, appended as data to the current user message.'],
            'tradeoff':'A mistaken auxiliary reading can influence both actor and judge; agreement is not truth. Strict original pixel/candidate/history validation remains required; no auxiliary box is installed as a target or acceptance rule.',
            'no_old_completed_semantic_control_reexecuted':True,'heldout_evaluation_tasks_untouched':True,
            'private_expectations_or_render_geometry_in_model_package':False,
            'primary_native_backend_system_actions_precision_and_caps_unchanged':True,
            'full_original_messages_and_complete_images_retained_in_each_pair':True,
            'one_auxiliary_model_no_task_history_candidate_in_its_inputs':True,
            'controls_are_not_actor_trajectory_Mirage_rates_or_GUI_successes':True,
            'no_automatic_retry_after_terminal':True}
    save(PACKAGE/'controls-plan.json',plan)
    for p in PACKAGE.rglob('*.py'):
        compile(p.read_text(encoding='utf8'),str(p),'exec')
    manifest = {'schema':'balanced-visual-evidence-source-development-v1',
          'authorized_finite_joint_development':True,
          'authorization':'User sustained defense goal and instruction to supplement image-only evidence, preserving strict validation and budgets. This is finite new development, not formal efficacy release.',
          'expected_holder':parent_manifest['expected_holder'],'lease_sha256':parent_manifest['lease_sha256'],
          'output':'/home/researcher/jev-defense-four-gpu-20261106/'+HERE.name,'limits':limits,
          'source_provenance_sha256':sha(sources/'provenance.json'),
          'private_source_review_sha256':sha(HERE/'PRIVATE-source-first-review.json'),
          'parent_capacity13_manifest_sha256':sha(OLD/'manifest.json'),
          'fixed_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
          'primary_language_layer_counts':[22,23,19],'primary_visual_and_embeddings_physical_GPU':7,
          'single_auxiliary_physical_GPU':7,'four_cards_counted_as_reserved':True,
          'no_CPU_model_inference_or_offload':True,'only_authorized_physical_GPUs':[4,5,6,7],
          'decision_adapter_loaded':False,'no_original_GUI_queue_resumed':True,
          'files':{p.relative_to(PACKAGE).as_posix():sha(p) for p in sorted(PACKAGE.rglob('*')) if p.is_file()}}
    save(PACKAGE/'manifest.json',manifest)
    save(HERE/'preparation.json',{'time':time.time(),'manifest_sha256':sha(PACKAGE/'manifest.json'),
         'stage_only_no_submission':True,'limits':limits,'strict_validator_functions_unchanged':True,
         'main_runtime_and_backend_unchanged':True,'new_model_GPU_GUI_calls':0,
         'GPU_launch_requires_fresh_identity_lock_compute_and_CPU_input_admission':True})
    print(json.dumps({'package':str(PACKAGE),'manifest_sha256':sha(PACKAGE/'manifest.json'),
                      'source_files':len(manifest['files']),'limits':limits,'GPU_model_calls':0},ensure_ascii=False))


if __name__=='__main__':
    main()
