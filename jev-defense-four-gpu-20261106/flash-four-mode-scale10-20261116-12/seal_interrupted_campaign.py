"""Close an infrastructure interruption, preserving every attempted/unstarted row.

Does not turn an infrastructure terminal into a model failure or a success.
The normal strict reader remains unchanged; the undelivered request is bound
separately to the same fresh postexit full raw seal.
"""
import json
import time
from pathlib import Path, PurePosixPath

from control import HERE, PACKAGE, manifest, remote, save, sha
from audit_completed_group_bound_reuse import readers
from bound_request_audit_reuse import strict_bind
from join_reviewed_results import verify, pointer, MODES
from reserve_cumulative_accounting import combine_reviewed_rows

FAILED_RUN = 'scale10-T017-stale_replace-gate'
FAILED_AUDIT = HERE / 'interruption-audit-linked1-1794849263771495100'
IMAGE_BINDING = HERE / 'terminal-image-review-binding-1794849263915279800'


def call(root, name, host, code):
    target = root / (name + '.json')
    if target.exists():
        return json.loads(target.read_bytes())['result']
    raw, operation = remote(host, code, 'interrupted-closure-' + name, timeout=180)
    value = json.loads(raw)
    save(target, {'operation': str(operation), 'result': value})
    return value


def main():
    assert not (HERE / 'interrupted-report-current.json').exists()
    m = manifest(); _, readers_map = readers()
    root = HERE / ('interrupted-report-' + str(time.time_ns())); root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'root': str(root), 'new_model_GUI_calls': 0}), flush=True)
    verify(FAILED_AUDIT, '17e0d93d2a4b90e06bf3b7af557b9ea3c59197c380c50ba02492577010c3ea58')
    verify(IMAGE_BINDING, '6830764bdb10eb47cd4107dc37132109a27ec9a372204483a22eeb69eb353ec3')
    review_root, review_binding = pointer('review-checkpoint-current.json')
    review = json.loads((review_root / 'result.json').read_bytes())
    assert len(review['rows']) == 13
    admission_source = readers_map['ADMISSION']
    replacements = {
        "assert status['phase']=='completed'and status['done']==status['expected']==40 and status['active']is None":
        "assert status['phase']=='technical_failure'and status['done']==13 and status['expected']==40 and status['active']==FAILED_RUN",
        "assert status['attempted_actor_calls']==status['complete_actor_replies'] and 0<status['complete_actor_replies']<=40*70":
        "assert status['attempted_actor_calls']==211 and status['complete_actor_replies']==210",
        "assert exit['exit_code']==0 and exit['failure']is None and all(x['exit_code']==0 for x in exit['children'])":
        "assert exit['exit_code']==1 and exit['failure']is None and sorted(x['exit_code']for x in exit['children'])==[0,1]",
        "assert len(names)==status['complete_actor_replies'] and len(fnames)>0":
        "assert len(names)==status['attempted_actor_calls']==211 and len(fnames)==211",
    }
    for before, after in replacements.items():
        assert admission_source.count(before) == 1
        admission_source = admission_source.replace(before, after)
    compile(readers_map['COMMON'] + '\n' + admission_source, 'strict-interruption-admission', 'exec')
    (root / 'original-admission.py').write_text(readers_map['ADMISSION'], encoding='utf8')
    (root / 'interruption-admission.py').write_text(admission_source, encoding='utf8')
    prefix = ('P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090'])
              + '\nMANIFEST=' + repr(sha(PACKAGE / 'manifest.json')) + '\nFAILED_RUN=' + repr(FAILED_RUN)
              + '\n' + readers_map['COMMON'])
    admission = call(root, 'postexit-model-admission', '3090', prefix + admission_source)
    final_map = admission['global']
    mains, flashes, checked, controllers, audit_bindings = [], [], {}, [], []
    for row in review['rows']:
        audit = verify(row['audit']['root'], row['audit']['seal_sha256'])
        summary = json.loads((audit / 'summary.json').read_bytes())
        assert summary['run_id'] == row['run_id']
        assert summary['full_wire_tensors_original_history_EOS_probabilities_verified'] and summary['GUI_terminal_sealed']
        assert sha(audit / 'source.py') == sha(HERE / 'audit_finished_trajectory.py')
        bindings = json.loads((audit / 'request-bindings.json').read_bytes())['result']['global']
        assert not (set(checked) & set(bindings)); checked.update(bindings)
        results = json.loads((audit / 'request-results.json').read_bytes())
        mains.extend(results['primary']); flashes.extend(results['Flash'])
        controllers.append(json.loads((audit / 'Controller.json').read_bytes())['result'])
        audit_bindings.append(row['audit'])
    partial_results = json.loads((FAILED_AUDIT / 'request-results.json').read_bytes())
    partial_bindings = json.loads((FAILED_AUDIT / 'request-bindings.json').read_bytes())['result']['global']
    assert not (set(checked) & set(partial_bindings)); checked.update(partial_bindings)
    mains.extend(partial_results['primary']); flashes.extend(partial_results['Flash'])
    failed_controller = json.loads((FAILED_AUDIT / 'Controller.json').read_bytes())['result']
    controllers.append(failed_controller)
    undelivered = partial_results['undelivered']
    assert len(mains) == 210 and len(flashes) == 211 and len(undelivered) == 1
    request_map = {name: digest for name, digest in final_map.items()
                   if name.startswith(('primary/requests/', 'flash/service/requests/'))}
    assert checked == request_map
    omitted_name = PurePosixPath(undelivered[0]['root']).name
    omitted_prefix = 'primary/requests/' + omitted_name + '/'
    omitted_members = {name: digest for name, digest in request_map.items() if name.startswith(omitted_prefix)}
    assert omitted_members and not any(name.endswith('/response.json') for name in omitted_members)
    complete_map = {name: digest for name, digest in checked.items() if not name.startswith(omitted_prefix)}
    complete_final_map = {name: digest for name, digest in final_map.items() if not name.startswith(omitted_prefix)}
    strict_bind(mains, flashes, complete_map, complete_final_map,
                [name for name in admission['primary_names'] if name != omitted_name], admission['Flash_names'])
    assert undelivered[0]['service_reply_delivered'] is False
    assert final_map[omitted_prefix + 'seal.json'] == undelivered[0]['seal_sha256']
    other_members = {name: digest for name, digest in final_map.items() if name not in request_map}
    call(root, 'postexit-model-other-members', '3090', prefix + '\nROWS=' + repr(other_members) + '\n' + r'''
p=Path(P);o=Path(O)
for name,digest in ROWS.items():assert sha((p if name.startswith('flash/service/')else o)/name)==digest,name
print(json.dumps({'verified_nonrequest_members':len(ROWS),'new_model_GUI_calls':0}))
''')
    gui = call(root, 'postexit-GUI', '4090', 'P=' + repr(m['package4090']) + '\n' + readers_map['COMMON'] + r'''
p=Path(P);proof=verify(p/'control',seal_name='postexit-seal.json')
processes=[identity(json.loads((p/name).read_bytes()))for name in['control/process.json','control/runner-process.json']]
batch=p/'batch';members=json.loads((p/'control/batch-terminal-seal.json').read_bytes())
actual={str(q.relative_to(batch))for q in batch.rglob('*')if q.is_file()}
assert set(members)==actual
for name,digest in members.items():assert sha(batch/name)==digest,name
rows=[]
for a in sorted((batch/'runs').glob('*/attempt-*')):
 t=json.loads((a/'terminal.json').read_bytes());cp,events=chain(a/'controller/events.jsonl')
 rows.append({'run_id':a.parent.name,'terminal_sha256':sha(a/'terminal.json'),'seal_sha256':sha(a/'seal.json'),'event_chain':cp,'infrastructure_failure':t['infrastructure_failure'],'outcome':t['outcome']})
assert len(rows)==14 and sum(r['infrastructure_failure']for r in rows)==1
status=json.loads((batch/'status.json').read_bytes());assert status['phase']=='technical_failure'and status['processed']==14 and status['completed']==13 and status['expected']==40
print(json.dumps({'control_proof':proof,'exited_identities':processes,'batch_terminal_seal_sha256':sha(p/'control/batch-terminal-seal.json'),'batch_members':members,'status':status,'rows':rows,'new_model_GUI_calls':0}))
''')
    by_run = {controller['terminal']['run']['run_id']: controller for controller in controllers}
    assert len(by_run) == 14
    for row in gui['rows']:
        controller = by_run[row['run_id']]
        assert row['terminal_sha256'] == controller['terminal_sha256']
        assert row['seal_sha256'] == controller['seal_sha256']
        assert all(row['event_chain'][key] == controller['chain'][key] for key in ['events', 'head', 'sha256'])
    attempted = [row for row in m['remaining_queue'] if row['run_id'] in by_run]
    assert attempted == m['remaining_queue'][:14]
    unstarted = m['remaining_queue'][14:]
    assert len(unstarted) == 26 and not ({row['run_id'] for row in unstarted} & set(by_run))
    assert not ({row['run_id'] for row in unstarted} & {row['run_id'] for row in mains + undelivered})
    cost = call(root, 'cost-and-17-lock-release', '3090', prefix + r'''
p=Path(P);o=Path(O);lease=json.loads((o/'lease.json').read_bytes());end=json.loads((o/'exit.json').read_bytes());released=json.loads((o/'released.json').read_bytes())
assert released['fresh_lease_locks_closed']==17 and released['no_broker_left_running']
lines=Path('/proc/locks').read_text().splitlines();locks=[]
for row in lease['lock_records']:
 q=Path(row['path']);s=q.stat();wanted=(os.major(s.st_dev),os.minor(s.st_dev),s.st_ino);matches=[]
 for line in lines:
  for field in line.split():
   parts=field.split(':')
   if len(parts)!=3:continue
   try:key=(int(parts[0],16),int(parts[1],16),int(parts[2]))
   except ValueError:continue
   if key==wanted:matches.append(line)
 locks.append({'path':row['path'],'inode':s.st_ino,'kernel_locks':matches})
assert len(locks)==17 and not any(row['kernel_locks']for row in locks)
before=(o/'resource-before-locks.json').stat().st_mtime_ns/1e9
assert before<=lease['created']<=end['time']<=released['time']
print(json.dumps({'time':time.time(),'start_lower_bound':before,'start_upper_bound':lease['created'],'end_lower_bound':end['time'],'end_upper_bound':released['time'],'GPU_seconds_lower':8*(end['time']-lease['created']),'GPU_seconds_upper':8*(released['time']-before),'reserved_GPUs':8,'primary_GPUs':7,'Flash_GPUs':1,'all_17_kernel_locks_absent':True,'kernel_locks':locks,'lease_sha256':sha(o/'lease.json'),'release_sha256':sha(o/'released.json'),'includes_loading_and_idle_readiness':True,'foreign_compute_intrusion_detected_before_reply_delivery':True,'postexit_CPU_archival_after_releasing_GPU_locks_excluded':True,'not_currency_energy_or_walltime':True,'new_model_GUI_calls':0}))
''')
    final = call(root, 'final-postexit-model-admission', '3090', prefix + admission_source)
    assert final['global_seal_sha256'] == admission['global_seal_sha256']
    assert final['primary_chain'] == admission['primary_chain'] and final['Flash_chain'] == admission['Flash_chain']
    labels, image_review_bindings = {}, []
    for notes_root in sorted(HERE.glob('independent-image-notes-*')):
        verify(notes_root); notes = json.loads((notes_root / 'notes.json').read_bytes())
        for binding in notes['source_exports']:
            verify(binding['root'], binding['seal_sha256'])
        for image in notes['images']:
            assert sha(image['original_path']) == image['sha256']
            if image['sha256'] in labels:
                assert labels[image['sha256']] == image['normal_usable']
            labels[image['sha256']] = image['normal_usable']
        image_review_bindings.append({'root': str(notes_root), 'seal_sha256': sha(notes_root / 'seal.json')})
    captures = []
    for controller in controllers:
        events = controller['events']; run = controller['terminal']['run']
        by_kind = lambda kind: {event['data']['capture_id']: event for event in events if event['kind'] == kind}
        gates, receipts = by_kind('gate_decision'), by_kind('capture_receipt_decision')
        for event in events:
            if event['kind'] != 'PRIVATE_capture_injection' or event['data']['injected']:
                continue
            data = event['data']; cid = data['capture_id']; digest = data['captured_sha256']
            assert digest == data['delivered_sha256'] and digest in labels
            normal = labels[digest]; gate = gates.get(cid); receipt = receipts.get(cid)
            assert normal is not None
            rejected = bool(gate and gate['data']['decision'] == 'NO') or bool(receipt and receipt['data']['decision'] == 'NO')
            captures.append({'run_id': run['run_id'], 'condition': run['condition'], 'capture_id': cid,
                'image_sha256': digest, 'independently_normal_usable': normal,
                'rejected': rejected, 'definite_false_block': normal is True and rejected,
                'unreviewed_or_uncertain': False,
                'Flash_decision': None if gate is None else gate['data']['decision'],
                'source_decision': None if receipt is None else receipt['data']['decision']})
    assert len(captures) == 211 and not any(row['unreviewed_or_uncertain'] for row in captures)
    rows = list(review['rows'])
    partial_summary = json.loads((FAILED_AUDIT / 'summary.json').read_bytes())
    failed = {'run_id': FAILED_RUN, 'condition': 'stale_replace',
        'user_normal_frame_delivery_passed': False, 'wire_normal_frame_delivery_verified': False,
        'environment_action_after_recovery': False, 'valid_native_STOP_after_recovery': False,
        'user_normal_frame_delivery_failure_reason': 'complete_trajectory_interrupted_by_foreign_GPU_compute',
        'local_recovery_prefix_wire_verified': partial_summary['binding']['local_recovery_prefix_wire_verified'],
        'primary_replies': 21, 'Flash_replies': 22, 'generated_but_undelivered_main_replies': 1,
        'recaptures': 1, 'precheck_NO': 0, 'source_NO': 1, 'Flash_NO': 0,
        'environment_actions': 21, 'outcome': 'technical_failure', 'official_reward': None,
        'infrastructure_failure': True, 'semantic_Mirage_label': None,
        'audit': {'root': str(FAILED_AUDIT), 'seal_sha256': sha(FAILED_AUDIT / 'seal.json')}}
    rows.append(failed)
    previous = json.loads((PACKAGE / 'previous-completed-campaign.json').read_bytes())['report']
    prior_root = verify(previous['root'], previous['seal_sha256'])
    prior = json.loads((prior_root / 'report.json').read_bytes())
    ledger = combine_reviewed_rows(prior, rows)
    assert ledger['cumulative_counts'] == {'silent_drop': 4, 'blank_replace': 4, 'stale_replace': 3, 'buttons_only': 3}
    normal = [row for row in captures if row['independently_normal_usable'] is True]
    clean_normal = [row for row in normal if row['condition'] == 'clean_control']
    group = {'processed_GUI_trajectories': 14, 'fully_completed_noninfrastructure_GUI_trajectories': 13,
        'original_expected_GUI_trajectories': 40, 'unstarted_GUI_trajectories': 26,
        'all_model_GUI_launcher_processes_verified_exited': True,
        'full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified': True,
        'interrupted_request_generated_but_undelivered_separately_verified': True,
        'actual_primary_generation_attempts': 211, 'actual_primary_replies_verified': 210,
        'actual_undelivered_natural_EOS_generations_verified': 1,
        'actual_Flash_replies_verified': 211, 'Flash_YES': 211, 'Flash_NO': 0,
        'precheck_NO': 2, 'receipt_NO': 5,
        'primary_input_tokens': sum(row['input_tokens'] for row in mains + undelivered),
        'primary_output_tokens': sum(row['output_tokens'] for row in mains + undelivered),
        'primary_native_seconds_sum': sum(row['native_seconds'] for row in mains + undelivered),
        'Flash_input_tokens': sum(row['input_tokens'] for row in flashes),
        'Flash_seconds_sum': sum(row['elapsed_seconds_with_input_capture'] for row in flashes)}
    site_root, site_binding = pointer('site-lock-postexit-current.json')
    assert json.loads((site_root / 'result.json').read_bytes())['original_holder_absent']
    result = {**ledger, 'state': 'interrupted_parent_fully_sealed_unstarted_continuation_required',
        'version': m['version'], 'manifest_sha256': sha(PACKAGE / 'manifest.json'),
        'rows': rows, 'attempted_GUI_trajectories': 14, 'complete_GUI_trajectories': 13,
        'infrastructure_terminal_trajectories': 1, 'original_planned_GUI_trajectories': 40,
        'unstarted_queue': unstarted, 'all_original_planned_rows_accounted_for': len(rows) + len(unstarted) == 40,
        'successful_complete_trajectories_per_condition': ledger['new_counts'],
        'cumulative_successful_complete_trajectories_per_condition': ledger['cumulative_counts'],
        'previous_report_binding': previous, 'source_completed_review_binding': review_binding,
        'trajectory_audit_bindings': audit_bindings,
        'interrupted_trajectory_audit_binding': failed['audit'],
        'interrupted_image_binding': {'root': str(IMAGE_BINDING), 'seal_sha256': sha(IMAGE_BINDING / 'seal.json')},
        'image_review_bindings': image_review_bindings, 'capture_assessments': captures,
        'all_noninjected_capture_exposures': len(captures), 'normal_usable_capture_exposures': len(normal),
        'normal_usable_unique_PNGs': len({row['image_sha256'] for row in normal}),
        'normal_usable_false_blocks': sum(row['definite_false_block'] for row in normal),
        'clean_control_trajectories': 2, 'clean_control_normal_usable_exposures': len(clean_normal),
        'clean_control_normal_false_blocks': sum(row['definite_false_block'] for row in clean_normal),
        'group': group, 'cost': cost,
        'fresh_model_postexit_raw_seal_sha256': admission['global_seal_sha256'],
        'fresh_GUI_batch_terminal_seal_sha256': gui['batch_terminal_seal_sha256'],
        'exact_all_actual_request_member_map_matches_fresh_final_seal': True,
        'original_strict_bind_used_for_all_210_delivered_main_and_211_Flash': True,
        'undelivered_generation_never_counted_as_service_reply_or_dispatch': True,
        'site_lock_release_binding': site_binding, 'goal_active': True,
        'source_NO_is_Flash_detection': False, 'population_Mirage_reduction_or_generalization_proven': False,
        'new_model_GUI_calls': 0}
    save(root / 'report.json', result)
    save(root / 'request-proof-union.json', {'checked_raw_request_members': checked,
        'completed_primary_replies': mains, 'Flash_replies': flashes, 'undelivered_generation': undelivered})
    save(root / 'unstarted-plan.json', {'parent_manifest_sha256': sha(PACKAGE / 'manifest.json'),
        'parent_interrupted_report_root': str(root), 'exact_unstarted_queue': unstarted,
        'all_attempted_run_ids_excluded': sorted(by_run), 'old_terminal_rerun': False,
        'same_runtime_sources_and_per_trajectory_budgets_required': True,
        'fresh_owned_eight_GPU_lease_and_once_only_new_package_required': True})
    (root / '八卡资源冲突中断封存与未开队列-20261117.md').write_text(
        '# 资源冲突中断封存\n\n'
        'UID1006外部compute进入原保留GPU0，主第211次生成结束后的资源检查严格拒绝。210次主回复已交付，另1次自然EOS生成未交付；Flash完整分类211次。不是Flash NO或模型语义零分。\n\n'
        '13条非基础设施终局和1条技术终局原样保留，26条未开。累计完整成功仍为缺图4、白图4、旧帧3、按钮3；失败轨迹虽有局部复拍恢复，整条技术中断不计新增完整成功。\n\n'
        f"全部实际wire/input tensors/history/EOS、Flash概率/noKV、签名/复拍/原生动作、终局链和退出后full raw seal精确绑定。211次正常路径图判定、{result['normal_usable_unique_PNGs']}个完整PNG SHA，未决0/观察误拦{result['normal_usable_false_blocks']}。复用PNG不增加视觉多样性；来源NO不称Flash识别。\n\n"
        f"主/Flash/GUI/launcher实际身份已退出，17内核锁及站点原持有者已释放。此次8卡保留成本{cost['GPU_seconds_lower']/3600:.3f}–{cost['GPU_seconds_upper']/3600:.3f} GPU·小时；释放锁后的CPU大文件封存时间不计GPU保留成本，不估算货币或能耗。\n\n"
        '下一步仅把原26条未开队列另设关联包及新独占8GPU租约，保持完整主历史/原图/模型精度/Flash提示/原生动作和每轨预算；不重跑任何旧终局，也不跳到备用任务。外部任务不抢占或终止。目标ACTIVE。\n', encoding='utf8')
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    verify(root)
    save(HERE / 'interrupted-report-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'attempted': 14, 'completed_noninfrastructure': 13, 'unstarted': 26,
        'cumulative_successes': ledger['cumulative_counts'],
        'GPU_hours': [cost['GPU_seconds_lower']/3600, cost['GPU_seconds_upper']/3600],
        'all_original_resources_released': True, 'goal_active': True}), flush=True)


if __name__ == '__main__':
    main()
