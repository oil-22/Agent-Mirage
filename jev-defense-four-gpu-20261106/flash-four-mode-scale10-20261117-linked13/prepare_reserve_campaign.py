"""Gated future reserve preparation; never starts models or GUI.

Only a completed, fully reviewed and released campaign may yield one child.
The next task and deficient conditions must come from the frozen reserve order.
"""
import ast
import json
import re
import secrets
import sys
import time
from pathlib import Path

from remote_util import HERE, remote, save, sha
from join_reviewed_results import verify
from reserve_cumulative_accounting import MODES, counts_from_rows

READER_DRAFT = HERE / 'reserve-reader-metadata-staging-1794841585726283000'
JOIN_DRAFT = HERE / 'reserve-join-metadata-staging-1794847763748042900'

PARENT_CODE = r'''
import hashlib,json,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 q=Path('/proc',str(pid))
 if not q.exists():return None
 s=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
p=Path(P);o=Path(O)
assert sha(p/'manifest.json')==EXPECTED
files={};processes=[]
paths=[p/'manifest.json']+([o/n for n in ['launcher-process.json','lease.json','primary/process.json','primary/status.json','primary/terminal.json','exit.json','released.json','postexit-seal.json']]+[p/'flash/service/process.json',p/'flash/service/terminal.json'] if HOST=='3090' else [p/n for n in ['batch/status.json','control/process.json','control/runner-process.json','control/exit.json','control/postexit-seal.json','control/batch-terminal-seal.json']])
if HOST=='4090':
 paths+=list((p/'batch/runs').glob('*/attempt-*/terminal.json'))+list((p/'batch/runs').glob('*/attempt-*/seal.json'))
 for q in(p/'batch').rglob('*process*.json'):
  if q not in paths:paths.append(q)
for q in paths:
 v=json.loads(q.read_bytes());files[str(q)]={'sha256':sha(q)}
 if isinstance(v,dict)and all(k in v for k in ['pid','uid','command','start_ticks']):
  a=identity(v['pid']);assert a is None or a['state']in['X','Z']or any(a[k]!=v[k]for k in ['uid','command','start_ticks'])
  processes.append({'saved':v,'actual':a})
 if q.name=='status.json':assert v['phase']=='completed'and v['expected']==COUNT
 if q.name=='released.json':assert v['fresh_lease_locks_closed']==17
if HOST=='4090':assert len(list((p/'batch/runs').glob('*/attempt-*/terminal.json')))==COUNT
print(json.dumps({'host':HOST,'time':time.time(),'files':files,'processes':processes,
 'completed_parent_manifest_sha256':EXPECTED,'expected_trajectories':COUNT,
 'parent_all_terminal_and_original_processes_exited':True,'read_only':True,'new_model_GUI_calls':0}))
'''


def load_plan(plan_root):
    plan_root = verify(Path(plan_root).resolve())
    plan = json.loads((plan_root / 'plan.json').read_bytes())
    parent = Path(plan['completed_campaign_report']['root']).parent
    assert (parent / 'completed-report-current.json').exists(), 'A running campaign cannot prepare a reserve child'
    current = json.loads((parent / 'completed-report-current.json').read_bytes())
    assert current == plan['completed_campaign_report'], 'A stale parent plan must not create another branch'
    report_root = verify(current['root'], current['seal_sha256'])
    report = json.loads((report_root / 'report.json').read_bytes())
    rows = report.get('cumulative_rows', report['rows'])
    counts = counts_from_rows(rows)
    assert counts == report['cumulative_counts'] == plan['verified_cumulative_successes']
    deficits = {mode: max(0, 10 - counts[mode]) for mode in MODES}
    assert deficits == plan['deficits'] and any(deficits.values())
    selection_root = verify(plan['selection_binding']['root'], plan['selection_binding']['seal_sha256'])
    selection = json.loads((selection_root / 'selection.json').read_bytes())
    used = {int(re.search(r'(?:^|-)T([0-9]+)(?:-|$)', row['run_id']).group(1)) for row in rows}
    remaining = [task for task in selection['reserve_task_ids'] if task not in used]
    assert remaining and remaining[0] == plan['next_task_id']
    assert remaining == plan['remaining_frozen_reserve_order']
    conditions = [mode for mode in selection['conditions'] if mode == 'clean_control' or deficits.get(mode, 0) > 0]
    assert conditions == plan['conditions'] and 2 <= len(conditions) <= 5
    binding_rows = json.loads((selection_root / 'structural-bindings.json').read_bytes())['result']['rows']
    task = next(row for row in binding_rows if row['task_id'] == remaining[0])
    assert task == plan['task_binding'] and task['eligible']
    assert task['private_scorer_answers_or_reference_urls_exported'] is False
    assert task['require_reset'] is False and task['image'] is None and task['eval_types'] == ['url_match']
    assert report['group']['all_model_GUI_launcher_processes_verified_exited']
    assert report['group']['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    release = report['release_binding']
    release_root = verify(release['root'], release['seal_sha256'])
    assert json.loads((release_root / 'result.json').read_bytes())['all_17_kernel_locks_absent']
    site = report['site_lock_release_binding']
    site_root = verify(site['root'], site['seal_sha256'])
    assert json.loads((site_root / 'result.json').read_bytes())['original_holder_absent']
    prep = json.loads((parent / 'preparation-current.json').read_bytes())
    prep_root = verify(prep['root'], prep['seal_sha256'])
    package = Path(prep['package'])
    assert sha(package / 'manifest.json') == prep['manifest_sha256'] == report['manifest_sha256']
    assert not (parent / 'reserve-child-intent.json').exists(), 'Inspect the already prepared child; never prepare a duplicate'
    return plan_root, plan, parent, report, prep_root, package


def main():
    plan_root, plan, parent, report, parent_prep, oldp = load_plan(sys.argv[1])
    name = sys.argv[2]
    assert re.fullmatch(r'flash-four-mode-scale10-reserve-[a-z0-9-]{1,70}', name)
    dest = HERE.parent / name
    assert not dest.exists()
    count, task = len(plan['conditions']), plan['task_binding']
    old = json.loads((oldp / 'manifest.json').read_bytes())
    for member, digest in old['files'].items():
        assert sha(oldp / member) == digest, member
    verify(READER_DRAFT, '133b3d5dc9ec04f7900fa329c1b7a80b1675eea158147df5acf775534fd5c5e0')
    verify(JOIN_DRAFT, '055c3e655dd5a920eb88014136bc5ec32f4d3b728af202b4c3ea39f9453e545a')
    proofs = {}
    for host in ['3090', '4090']:
        code = ('HOST=' + repr(host) + '\nP=' + repr(old['package' + host])
                + '\nO=' + repr(old['output3090']) + '\nEXPECTED=' + repr(sha(oldp / 'manifest.json'))
                + '\nCOUNT=' + repr(old['trajectories']) + '\n' + PARENT_CODE)
        raw, operation = remote(host, code, 'bind-completed-reserve-parent-' + host)
        proofs[host] = {'operation': str(operation), 'result': json.loads(raw)}
    # A single durable claim prevents two concurrent children of one report.
    save(parent / 'reserve-child-intent.json', {
        'time': time.time(), 'plan_root': str(plan_root), 'plan_seal_sha256': sha(plan_root / 'seal.json'),
        'child_study': str(dest), 'same_protocol_one_child_only': True,
        'new_model_GUI_calls': 0, 'failure_requires_linked_preservation_not_duplicate_prepare': True,
    })
    dest.mkdir()
    root = dest / ('preparation-' + str(time.time_ns()))
    root.mkdir()
    package = root / 'package'
    package.mkdir()
    for member in old['files']:
        target = package / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((oldp / member).read_bytes())
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')
    reserve_binding = {'root': str(plan_root), 'seal_sha256': sha(plan_root / 'seal.json')}
    version = 'trusted-native-capture-quality-v3-scale10-reserve-T%03d-v1' % task['task_id']
    auth = {
        'direct_human_instruction': '现在我要把拦截成功的轨迹数目增加到每种注入十条',
        'new_trusted_capture_protocol_authorized': True, 'same_protocol_scaleup_authorized': True,
        'cumulative_target_per_mode': 10, 'prior_cumulative_successes': plan['verified_cumulative_successes'],
        'reserve_plan_binding': reserve_binding, 'new_GUI_count': count,
        'same_single_image_Flash_and_full_primary_history_budgets': True,
        'no_old_terminal_rerun': True, 'no_expanded_per_trajectory_or_paid_budget': True,
    }
    (package / 'user-current-authorization.json').write_text(json.dumps(auth, ensure_ascii=False, indent=2), encoding='utf8')
    queue = [{'run_id': 'scale10r%d-T%03d-%s-gate' % (task['task_id'], task['task_id'], condition),
              'task_id': task['task_id'], 'condition': condition, 'gate_enabled': True}
             for condition in plan['conditions']]
    runtime_plan = json.loads((oldp / 'plan.json').read_bytes())
    public_task = {key: task[key] for key in ['task_id', 'intent', 'image', 'sites', 'require_reset', 'source_member', 'source_config_sha256']}
    public_task.update(private_evaluator_fields_exported=False, not_experiment_results=True,
                       pilot_task_id='classifieds_' + str(task['task_id']))
    runtime_plan.update(
        version=version, protocol_version=old.get('protocol_version', old['version']), created=time.time(),
        tasks=[public_task], queue=queue, expected_trajectories=count,
        current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
        reserve_plan_binding=reserve_binding, prior_verified_per_condition=plan['verified_cumulative_successes'],
        acceptance={**runtime_plan['acceptance'], 'per_condition_target': 1,
                    'prior_verified_per_condition': plan['verified_cumulative_successes'], 'cumulative_target': 10},
        interpretation='Next unused presealed reserve task; deficient modes plus matched clean only. All older terminals immutable; no population Mirage or Flash freshness claim.')
    (package / 'plan.json').write_text(json.dumps(runtime_plan, ensure_ascii=False, indent=2), encoding='utf8')
    native = json.loads((oldp / 'native-bindings-public.json').read_bytes())
    native.update(time=time.time(), tasks=[task], prospective_plan_SHA=sha(package / 'plan.json'),
                  reserve_plan_binding=reserve_binding)
    (package / 'native-bindings-public.json').write_text(json.dumps(native, ensure_ascii=False, indent=2), encoding='utf8')
    analysis = json.loads((oldp / 'analysis-plan.json').read_bytes())
    analysis.update(queue=queue, prior_success_per_condition=plan['verified_cumulative_successes'],
                    cumulative_target_per_condition=10, initial_new_required_per_condition=1,
                    previous_completed_report=plan['completed_campaign_report'], reserve_plan_binding=reserve_binding,
                    precommitted_before_any_GUI=True)
    (package / 'analysis-plan.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf8')
    (package / 'previous-completed-campaign.json').write_text(json.dumps({
        'report': plan['completed_campaign_report'], 'manifest_sha256': sha(oldp / 'manifest.json'),
        'parent_campaign_complete_and_released': True, 'goal_may_still_be_active': True,
    }, ensure_ascii=False, indent=2), encoding='utf8')
    (package / 'source-parent-manifest.json').write_bytes((oldp / 'manifest.json').read_bytes())
    (package / 'current-reserve-plan.json').write_bytes((plan_root / 'plan.json').read_bytes())
    proof_names = {}
    for host in ['3090', '4090']:
        filename = 'completed-reserve-parent-' + sha(oldp / 'manifest.json')[:12] + '-' + host + '.json'
        proof_names[host] = filename
        save(package / filename, proofs[host])
    guard = (oldp / 'continuation_guard.py').read_text('utf8')
    before = "manifest['study'] == %r and manifest['trajectories'] == %d" % (old['study'], old['trajectories'])
    after = "manifest['study'] == %r and manifest['trajectories'] == %d" % (version, count)
    assert guard.count(before) == 1
    guard = guard.replace(before, after)
    extra = (
        "    reserve = json.loads((package / (%r + host + '.json')).read_bytes())['result']\n"
        "    assert reserve['parent_all_terminal_and_original_processes_exited'] and reserve['expected_trajectories'] == %d\n"
        "    assert reserve['completed_parent_manifest_sha256'] == %r\n"
        "    for path, row in reserve['files'].items():\n"
        "        assert sha(Path(path)) == row['sha256'], path\n"
        "    for row in reserve['processes']:\n"
        "        saved = row['saved']; proc = Path('/proc', str(saved['pid']))\n"
        "        actual = identity(saved['pid']) if proc.exists() else None\n"
        "        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])\n"
    ) % ('completed-reserve-parent-' + sha(oldp / 'manifest.json')[:12] + '-', old['trajectories'], sha(oldp / 'manifest.json'))
    anchor = "    return {'host': host,"
    assert guard.count(anchor) == 1
    (package / 'continuation_guard.py').write_text(guard.replace(anchor, extra + anchor), encoding='utf8')
    launcher = (oldp / 'launch_group.py').read_text('utf8')
    lock_names = {node.value for node in ast.walk(ast.parse(launcher))
                  if isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and node.value.endswith('.lock') and '/' not in node.value and len(node.value) > 5}
    assert len(lock_names) == 1
    old_lock = lock_names.pop()
    assert launcher.count(repr(old_lock)) == 1
    (package / 'launch_group.py').write_text(launcher.replace(repr(old_lock), repr('jev-' + name + '.lock')), encoding='utf8')
    invariants = json.loads((parent_prep / 'source-invariance.json').read_bytes())['unchanged_runtime_files']
    for member, digest in invariants.items():
        assert sha(package / member) == sha(oldp / member) == digest, member
    for source in package.rglob('*.py'):
        ast.parse(source.read_text('utf8'))
    members = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*')
               if p.is_file() and p.name not in ['manifest.json', 'private.token']}
    m = {**old, 'created': time.time(), 'version': version, 'study': version, 'files': members,
         'remaining_queue': queue, 'trajectories': count, 'auth_token_sha256': sha(package / 'private.token'),
         'current_user_authorization_sha256': sha(package / 'user-current-authorization.json'),
         'same_protocol_reserve_metadata_only': True, 'source_parent_manifest_sha256': sha(oldp / 'manifest.json'),
         'source_prior_manifest_sha256': sha(oldp / 'manifest.json'),
         'unchanged_runtime_source_names': list(invariants), 'reserve_plan_binding': reserve_binding,
         'prior_verified_per_condition': plan['verified_cumulative_successes'],
         'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + name,
         'package4090': '/data/researcher/jev-defense-four-gpu-20261106/' + name + '/runtime',
         'output3090': '/data/researcher/jev-defense-four-gpu-20261106/' + name + '/model-attempt-01'}
    save(package / 'manifest.json', m)
    save(root / 'source-invariance.json', {'unchanged_runtime_files': invariants,
        'parent_manifest_sha256': sha(oldp / 'manifest.json'), 'new_tasks_and_queue_operational_metadata_only': True})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    save(dest / 'preparation-current.json', {'root': str(root), 'package': str(package),
        'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')})
    (dest / 'task-selection-current.json').write_bytes((parent / 'task-selection-current.json').read_bytes())
    unchanged_managers = [
        'remote_util.py', 'collect_progress.py', 'inspect_owned_runtime.py', 'audit_finished_trajectory.py',
        'protocol_audit_components.py', 'export_examples_sealed.py', 'audit_resource_interval.py',
        'audit_released_resources.py', 'audit_gui_site_lock.py', 'export_review_frames.py',
        'export_sealed_capture_prefix.py', 'build_review_sheets.py', 'bind_terminal_image_reviews.py',
        'review_checkpoint.py', 'watch_campaign_review_linked.py', 'plan_reserve_after_terminal.py',
        'reserve_cumulative_accounting.py', 'write_reserve_report.py', 'qualify_reserve_campaign.py',
    ]
    for member in unchanged_managers:
        (dest / member).write_bytes((HERE / member).read_bytes())
    for member in ['control.py', 'audit_completed_group_bound_reuse.py', 'bound_request_audit_reuse.py']:
        (dest / member).write_bytes((READER_DRAFT / ('count-%d' % count) / member).read_bytes())
    (dest / 'join_reviewed_results.py').write_bytes((JOIN_DRAFT / ('count-%d' % count) / 'join_reviewed_results.py').read_bytes())
    (dest / 'README.md').write_text('备用包仅准备，未提交或启动；先运行qualify_reserve_campaign.py，再按control.py独占新租约启动。旧终局不重跑。\n', encoding='utf8')
    print(json.dumps({'study': str(dest), 'package': str(package), 'trajectories': count,
                      'next_frozen_task': task['task_id'], 'conditions': plan['conditions'],
                      'manifest_sha256': sha(package / 'manifest.json'), 'new_model_GUI_calls': 0,
                      'CPU_qualification_still_required': True, 'nothing_staged_submitted_or_launched': True}))


if __name__ == '__main__':
    main()
