"""Prepare exactly the sealed 26 unstarted rows after a preserved interruption.

Never launches a model, GUI, or resource lease. Completed and infrastructure
terminals stay immutable; only fresh operational metadata is changed.
"""
import ast
import json
import secrets
import time
from pathlib import Path, PurePosixPath

from remote_util import HERE, remote, save, sha
from join_reviewed_results import verify
from reserve_cumulative_accounting import counts_from_rows
from write_reserve_report import previous_cohorts

CHILD = 'flash-four-mode-scale10-20261117-linked13'
VERSION = 'trusted-native-capture-quality-v3-scale10-unstarted-linked1'
PARENT_SHA = '874a87681734dbe6ca65e2e76f7512638860b40897e3b80fad08e9bbcd23122b'
READER_ROOT = HERE / 'reserve-reader-metadata-staging-1794841585726283000'
JOIN_ROOT = HERE / 'reserve-join-metadata-staging-1794847763748042900'

PROOF_CODE = r'''
import hashlib,json,os,time
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return None
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
files=INPUT['files'];processes=[]
for path,row in files.items():assert sha(path)==row['sha256'],path
for saved in INPUT['identities']:
 actual=identity(saved['pid'])
 assert actual is None or actual['state']in['Z','X']or any(actual[k]!=saved[k]for k in ['uid','command','start_ticks'])
 processes.append({'saved':saved,'actual':actual})
p=Path(INPUT['package']);o=Path(INPUT['output']);unstarted=INPUT['unstarted_run_ids']
if INPUT['host']=='3090':
 s=json.loads((o/'primary/status.json').read_bytes())
 assert s['phase']=='technical_failure'and s['done']==13 and s['expected']==40
 assert s['attempted_actor_calls']==211 and s['complete_actor_replies']==210
 assert not(set(unstarted)&set(s['actor_counts']))
 assert json.loads((o/'released.json').read_bytes())['fresh_lease_locks_closed']==17
else:
 s=json.loads((p/'batch/status.json').read_bytes())
 assert s['phase']=='technical_failure'and s['processed']==14 and s['completed']==13 and s['expected']==40
 runs=list((p/'batch/runs').glob('*/attempt-*/terminal.json'))
 assert len(runs)==14 and {q.parent.parent.name for q in runs}==set(INPUT['attempted_run_ids'])
 assert not any((p/'batch/runs'/name).exists()for name in unstarted)
lines=Path('/proc/locks').read_text().splitlines();lock_rows=[]
for path in INPUT['lock_paths']:
 st=Path(path).stat();wanted=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino);matches=[]
 for line in lines:
  for field in line.split():
   parts=field.split(':')
   if len(parts)!=3:continue
   try:key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
   except ValueError:continue
   if key==wanted:matches.append(line)
 assert not matches,path
 lock_rows.append({'path':path,'inode':st.st_ino,'kernel_locks':matches})
assert len(lock_rows)==(17 if INPUT['host']=='3090'else 1)
print(json.dumps({'host':INPUT['host'],'time':time.time(),'files':files,'processes':processes,
 'lock_checks':lock_rows,'parent_manifest_sha256':INPUT['manifest_sha256'],
 'parent_preserved_interruption_not_completed':True,'attempted':14,'completed_noninfrastructure':13,
 'infrastructure_terminals':1,'exact_unstarted_count':26,'unstarted_run_ids':unstarted,
 'all_original_identities_exited_and_locks_absent':True,'read_only':True,'new_model_GUI_calls':0}))
'''


def replace_exact(text, before, after, count=1):
    assert text.count(before) == count, before
    return text.replace(before, after)


def proof_inputs(report_root, report, old, oldp, queue):
    main = json.loads((report_root / 'final-postexit-model-admission.json').read_bytes())['result']
    gui = json.loads((report_root / 'postexit-GUI.json').read_bytes())['result']
    site_root = verify(report['site_lock_release_binding']['root'], report['site_lock_release_binding']['seal_sha256'])
    site = json.loads((site_root / 'result.json').read_bytes())
    assert site['original_holder_absent'] and site['current_site_lock_free']
    assert main['global_seal_sha256'] == report['fresh_model_postexit_raw_seal_sha256']
    assert gui['batch_terminal_seal_sha256'] == report['fresh_GUI_batch_terminal_seal_sha256']
    result = {}
    for host, admission in [('3090', main), ('4090', gui)]:
        files = {old['package' + host] + '/manifest.json': {'sha256': PARENT_SHA}}
        if host == '3090':
            for member, digest in main['global'].items():
                if member.startswith(('primary/requests/', 'flash/service/requests/')):
                    continue
                prefix = old['package3090'] if member.startswith('flash/service/') else old['output3090']
                files[prefix + '/' + member] = {'sha256': digest}
            files[old['output3090'] + '/postexit-seal.json'] = {'sha256': main['global_seal_sha256']}
            locks = [r['path'] for r in report['cost']['kernel_locks']]
        else:
            for member, digest in gui['batch_members'].items():
                if PurePosixPath(member).name in ['terminal.json', 'seal.json'] or member == 'status.json':
                    files[old['package4090'] + '/batch/' + member] = {'sha256': digest}
            files[old['package4090'] + '/control/postexit-seal.json'] = {'sha256': gui['control_proof']['seal_sha256']}
            files[old['package4090'] + '/control/batch-terminal-seal.json'] = {'sha256': gui['batch_terminal_seal_sha256']}
            locks = [site['lock_path']]
        result[host] = {'host': host, 'package': old['package' + host], 'output': old['output3090'],
                        'manifest_sha256': PARENT_SHA, 'files': files,
                        'identities': [row['saved'] for row in admission['exited_identities']],
                        'lock_paths': locks, 'attempted_run_ids': [row['run_id'] for row in report['rows']],
                        'unstarted_run_ids': [row['run_id'] for row in queue]}
    return result


def manager_sources():
    unchanged = ['remote_util.py', 'collect_progress.py', 'inspect_owned_runtime.py',
        'audit_finished_trajectory.py', 'protocol_audit_components.py', 'export_examples_sealed.py',
        'audit_resource_interval.py', 'audit_released_resources.py', 'audit_gui_site_lock.py',
        'export_review_frames.py', 'export_sealed_capture_prefix.py', 'build_review_sheets.py',
        'bind_terminal_image_reviews.py', 'review_checkpoint.py', 'watch_campaign_review_linked.py',
        'reserve_cumulative_accounting.py', 'write_reserve_report.py', 'plan_reserve_after_terminal.py',
        'prepare_reserve_campaign.py', 'qualify_reserve_campaign.py', 'qualify_unstarted_continuation.py']
    sources = {name: (HERE / name).read_text('utf8') for name in unchanged}
    control = (HERE / 'control.py').read_text('utf8')
    for before, after in [("m['trajectories']==40", "m['trajectories']==26"),
                          ("h['expected']==40", "h['expected']==26"),
                          ("'expected_trajectories':40", "'expected_trajectories':26")]:
        control = replace_exact(control, before, after)
    sources['control.py'] = control
    group = (HERE / 'audit_completed_group_bound_reuse.py').read_text('utf8')
    group = replace_exact(group, "status['expected']==40", "status['expected']==26", 2)
    for before, after in [('<=40*70', '<=26*70'), ('len(controllers)==40', 'len(controllers)==26'),
                          ("'target_per_condition': 8", "'target_per_condition': 5")]:
        group = replace_exact(group, before, after)
    sources['audit_completed_group_bound_reuse.py'] = group
    sources['bound_request_audit_reuse.py'] = replace_exact(
        (HERE / 'bound_request_audit_reuse.py').read_text('utf8'),
        'assert len(run_ids) == 40', 'assert len(run_ids) == 26')
    join = (JOIN_ROOT / 'count-5/join_reviewed_results.py').read_text('utf8')
    for before, after in [("group['processed_GUI_trajectories'] == 5", "group['processed_GUI_trajectories'] == 26"),
                          ("len({v['run_id'] for v in rows}) == 5", "len({v['run_id'] for v in rows}) == 26"),
                          ("len({v['run_id'] for v in clean}) == 1", "len({v['run_id'] for v in clean}) == 6"),
                          ("'complete_GUI_trajectories': 5", "'complete_GUI_trajectories': 26"),
                          ("'clean_control_trajectories': 1", "'clean_control_trajectories': 6")]:
        join = replace_exact(join, before, after)
    sources['join_reviewed_results.py'] = join
    for name, source in sources.items():
        compile(source, name, 'exec')
    return sources


def main():
    dest = HERE.parent / CHILD
    assert not dest.exists() and not (HERE / 'unstarted-child-intent.json').exists()
    binding = json.loads((HERE / 'interrupted-report-current.json').read_bytes())
    report_root = verify(binding['root'], binding['seal_sha256'])
    report = json.loads((report_root / 'report.json').read_bytes())
    interrupted_plan = json.loads((report_root / 'unstarted-plan.json').read_bytes())
    prep = json.loads((HERE / 'preparation-current.json').read_bytes())
    prep_root = verify(prep['root'], prep['seal_sha256'])
    oldp = Path(prep['package'])
    assert sha(oldp / 'manifest.json') == prep['manifest_sha256'] == report['manifest_sha256'] == PARENT_SHA
    old = json.loads((oldp / 'manifest.json').read_bytes())
    for member, digest in old['files'].items():
        assert sha(oldp / member) == digest, member
    queue = interrupted_plan['exact_unstarted_queue']
    assert queue == report['unstarted_queue'] == old['remaining_queue'][14:] and len(queue) == 26
    assert set(interrupted_plan['all_attempted_run_ids_excluded']) == {r['run_id'] for r in report['rows']}
    assert old['remaining_queue'][:14] == [r for r in old['remaining_queue'] if r['run_id'] in interrupted_plan['all_attempted_run_ids_excluded']]
    assert not ({r['run_id'] for r in queue} & set(interrupted_plan['all_attempted_run_ids_excluded']))
    assert len(report['rows']) == report['attempted_GUI_trajectories'] == 14
    assert report['complete_GUI_trajectories'] == 13 and report['infrastructure_terminal_trajectories'] == 1
    assert report['group']['all_model_GUI_launcher_processes_verified_exited']
    assert report['group']['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    assert report['cost']['all_17_kernel_locks_absent']
    cohorts = previous_cohorts(binding)
    assert len(cohorts) == 2 and sum(len(c['report']['rows']) for c in cohorts) == 24
    counts = counts_from_rows(report['cumulative_rows'])
    assert counts == report['cumulative_counts'] == dict(silent_drop=4, blank_replace=4, stale_replace=3, buttons_only=3)
    verify(READER_ROOT, '133b3d5dc9ec04f7900fa329c1b7a80b1675eea158147df5acf775534fd5c5e0')
    verify(JOIN_ROOT, '055c3e655dd5a920eb88014136bc5ec32f4d3b728af202b4c3ea39f9453e545a')
    sources = manager_sources()
    inputs = proof_inputs(report_root, report, old, oldp, queue)
    proofs = {}
    for host in ['3090', '4090']:
        raw, operation = remote(host, 'INPUT=' + repr(inputs[host]) + '\n' + PROOF_CODE,
                                'bind-preserved-interruption-unstarted26-' + host)
        proofs[host] = {'operation': str(operation), 'result': json.loads(raw)}
    save(HERE / 'unstarted-child-intent.json', {'time': time.time(), 'child_study': str(dest),
         'parent_interrupted_report': binding, 'exact_unstarted_count': 26,
         'no_terminal_retry': True, 'one_child_only': True, 'new_model_GUI_calls': 0})
    dest.mkdir()
    root = dest / ('preparation-' + str(time.time_ns())); root.mkdir()
    package = root / 'package'; package.mkdir()
    for member in old['files']:
        target = package / member; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((oldp / member).read_bytes())
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')
    auth = {'direct_human_instruction': '现在我要把拦截成功的轨迹数目增加到每种注入十条',
        'new_trusted_capture_protocol_authorized': True, 'same_protocol_scaleup_authorized': True,
        'cumulative_target_per_mode': 10, 'prior_cumulative_successes': counts,
        'exact_original_unstarted_only': True, 'parent_interrupted_report': binding, 'new_GUI_count': 26,
        'same_single_image_Flash_and_full_primary_history_budgets': True,
        'no_old_terminal_rerun': True, 'no_expanded_per_trajectory_or_paid_budget': True}
    (package / 'user-current-authorization.json').write_text(json.dumps(auth, ensure_ascii=False, indent=2), encoding='utf8')
    task_ids = list(dict.fromkeys(row['task_id'] for row in queue))
    plan = json.loads((oldp / 'plan.json').read_bytes())
    plan.update(version=VERSION, created=time.time(), queue=queue, expected_trajectories=26,
        tasks=[t for t in plan['tasks'] if t['task_id'] in task_ids],
        current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
        unstarted_parent_binding=binding, prior_verified_per_condition=counts,
        acceptance={**plan['acceptance'], 'per_condition_target': 5, 'prior_verified_per_condition': counts},
        interpretation='Exact original 26 unstarted rows after preserved resource interruption; no completed or infrastructure terminal retry. Prior cumulative ledger retained including all failures. Same runtime and per-trajectory budgets.')
    (package / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf8')
    native = json.loads((oldp / 'native-bindings-public.json').read_bytes())
    native.update(time=time.time(), tasks=[t for t in native['tasks'] if t['task_id'] in task_ids],
        prospective_plan_SHA=sha(package / 'plan.json'), unstarted_parent_binding=binding)
    (package / 'native-bindings-public.json').write_text(json.dumps(native, ensure_ascii=False, indent=2), encoding='utf8')
    analysis = json.loads((oldp / 'analysis-plan.json').read_bytes())
    analysis.update(queue=queue, prior_success_per_condition=counts, initial_new_required_per_condition=5,
        previous_completed_report=binding, previous_report_state='preserved_interruption',
        exact_original_unstarted_only=True, precommitted_before_any_GUI=True)
    (package / 'analysis-plan.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf8')
    (package / 'previous-completed-campaign.json').write_text(json.dumps({'report': binding,
        'manifest_sha256': PARENT_SHA, 'parent_state': 'preserved_interruption_not_completed',
        'parent_all_actual_identities_exited_and_locks_released': True,
        'attempted': 14, 'completed_noninfrastructure': 13, 'infrastructure': 1,
        'exact_unstarted_count': 26, 'cumulative_rows_count': 24, 'goal_may_still_be_active': True}, indent=2), encoding='utf8')
    (package / 'source-parent-manifest.json').write_bytes((oldp / 'manifest.json').read_bytes())
    (package / 'current-unstarted-plan.json').write_bytes((report_root / 'unstarted-plan.json').read_bytes())
    for host in ['3090', '4090']:
        save(package / ('interrupted-parent-' + host + '.json'), proofs[host])
    guard = (oldp / 'continuation_guard.py').read_text('utf8')
    guard = replace_exact(guard, "manifest['study'] == %r and manifest['trajectories'] == 40" % old['study'],
                          "manifest['study'] == %r and manifest['trajectories'] == 26" % VERSION)
    extra = '''    interrupted = json.loads((package / ('interrupted-parent-' + host + '.json')).read_bytes())['result']
    assert interrupted['parent_preserved_interruption_not_completed']
    assert interrupted['attempted'] == 14 and interrupted['completed_noninfrastructure'] == 13
    assert interrupted['infrastructure_terminals'] == 1 and interrupted['exact_unstarted_count'] == 26
    assert interrupted['parent_manifest_sha256'] == %r
    assert interrupted['all_original_identities_exited_and_locks_absent']
    assert interrupted['unstarted_run_ids'] == [row['run_id'] for row in manifest['remaining_queue']]
    for path, row in interrupted['files'].items():
        assert sha(Path(path)) == row['sha256'], path
    for row in interrupted['processes']:
        saved = row['saved']; proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        assert actual is None or actual['state'] in ['Z', 'X'] or any(actual[k] != saved[k] for k in ['uid', 'command', 'start_ticks'])
''' % PARENT_SHA
    guard = replace_exact(guard, "    return {'host': host,", extra + "    return {'preserved_interruption_bound': True, 'only_original_unstarted_26': True, 'host': host,")
    (package / 'continuation_guard.py').write_text(guard, encoding='utf8')
    launch = (oldp / 'launch_group.py').read_text('utf8')
    launch = replace_exact(launch, repr('jev-four-mode-scale10-20261116-12.lock'), repr('jev-' + CHILD + '.lock'))
    (package / 'launch_group.py').write_text(launch, encoding='utf8')
    invariants = json.loads((prep_root / 'source-invariance.json').read_bytes())['unchanged_runtime_files']
    for member, digest in invariants.items():
        assert sha(package / member) == sha(oldp / member) == digest, member
    for source in package.rglob('*.py'):
        ast.parse(source.read_text('utf8'))
    files = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*')
             if p.is_file() and p.name not in ['manifest.json', 'private.token']}
    m = {**old, 'version': VERSION, 'study': VERSION, 'created': time.time(), 'files': files,
        'remaining_queue': queue, 'trajectories': 26, 'auth_token_sha256': sha(package / 'private.token'),
        'current_user_authorization_sha256': sha(package / 'user-current-authorization.json'),
        'same_protocol_unstarted_continuation_metadata_only': True,
        'source_parent_manifest_sha256': PARENT_SHA, 'source_prior_manifest_sha256': PARENT_SHA,
        'unchanged_runtime_source_names': list(invariants), 'unstarted_parent_binding': binding,
        'prior_verified_per_condition': counts,
        'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + CHILD,
        'package4090': '/data/researcher/jev-defense-four-gpu-20261106/' + CHILD + '/runtime',
        'output3090': '/data/researcher/jev-defense-four-gpu-20261106/' + CHILD + '/model-attempt-01'}
    save(package / 'manifest.json', m)
    save(root / 'source-invariance.json', {'unchanged_runtime_files': invariants,
        'parent_manifest_sha256': PARENT_SHA, 'original_unstarted_operational_metadata_only': True,
        'original_all_attempts_preserved': True, 'no_new_model_GUI_calls': True})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    save(dest / 'preparation-current.json', {'root': str(root), 'package': str(package),
        'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')})
    (dest / 'task-selection-current.json').write_bytes((HERE / 'task-selection-current.json').read_bytes())
    for member, source in sources.items():
        (dest / member).write_text(source, encoding='utf8')
    (dest / 'README.md').write_text('26条原未开队列已准备；先CPU资格审查，再stage。尚未申请GPU租约/启动模型或GUI。原14条终局不重跑；累计4/4/3/3保持。\n', encoding='utf8')
    print(json.dumps({'study': str(dest), 'package': str(package), 'trajectories': 26,
        'conditions': {c: sum(r['condition'] == c for r in queue) for c in (*counts, 'clean_control')},
        'manifest_sha256': sha(package / 'manifest.json'), 'new_model_GUI_calls': 0,
        'CPU_qualification_still_required': True, 'nothing_staged_submitted_or_launched': True}))


if __name__ == '__main__':
    main()
