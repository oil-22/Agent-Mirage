"""Link live identity and read-only storage evidence without runtime changes."""
import argparse
import copy
from pathlib import Path
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer = HERE / 'live-mixed-storage-observation-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert 0 <= time.time() - service['time'] < 240
    records = [service['worker/process.json']['value'], service['launcher-process.json']['value'],
               gui['control/runner-process.json']['value']]
    for row in records:
        assert not row['actual'].get('absent') and row['actual']['state'] not in ['Z', 'X']
        assert all(str(row['actual'][key]) == str(row['record'][key]) for key in ['pid','uid','command','start_ticks'])
    assert service['authorized_GPUs'] == [4,5,6,7] and len(service['held_locks']) == 9
    assert service['authorized_GPU_actual_compute_processes']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert all(str(row['actual_process'][key]) == str(records[0]['actual'][key])
                   for key in ['pid','uid','command','start_ticks'])
    storage = read(HERE / 'persistent-storage-inspection-created.json')
    verify_folder(storage['root'], storage['seal_sha256'])
    assert sha(Path(storage['root']) / 'receipt.json') == storage['receipt_sha256']
    candidates = {host: read(Path(storage['root']) / (host+'.json')) for host in ['3090','4090']}
    out = HERE / ('live-mixed-storage-observation-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md','HANDOFF.md','full-gui-current.json']:
        (previous/name).write_bytes((BASE/name).read_bytes())
        before[name] = sha(BASE/name)
    status = copy.deepcopy(read(BASE/'full-gui-current.json'))
    assert status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] == '0087'
    status.update(time=time.time(), previous_heads_SHA256=before, goal='active', monitor_should_remain_active=True)
    status['additional_persistent_storage_candidates'] = dict(authority=storage, candidates=candidates,
        whole32storage_fit_or_new_lease_proven=False, original_files_deleted_moved_compressed=False,
        ongoing32runtime_output_path_changed=False)
    for key,name in [('actual_service_state_at_snapshot','worker/status.json'),
                     ('actual_worker_identity_at_snapshot','worker/process.json'),
                     ('actual_launcher_identity_at_snapshot','launcher-process.json')]:
        status[key] = service[name]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'],status['GUI_event_chains'] = service['chains'],gui['chains']
    status['new32_sealed_requests_at_snapshot'],status['new32_terminals_at_snapshot'] = service['sealed_requests'],gui['terminals']
    status['authorities']['latest_actual_UID_locks_requests_chains'] = dict(path=str(evidence),seal_sha256=sha(evidence/'seal.json'))
    status['storage_at_snapshot'] = dict(service=service['filesystem'],GUI=gui['filesystem'],
        additional_persistent_candidates=storage,whole32storage_fit_not_guaranteed=True,
        no_original_files_deleted_moved_compressed=True)
    status['next_action'] = ('Same confirmed live worker/GUI, no duplicate launch. Existing native audit through87; inspect/audit only88+ next. '
        'No new actor since38; current source-bound price-history branch continues within original140 cap. '
        'Use prepared mixed audit for first actual enabled actor and original auxiliary; never repeat completed15selector/meta stages as new results. '
        '3090/data has separate read-only capacity evidence, not a new task lease or verified all32fit; preserve originals and do not hot-change frozen32. '
        'Full32/16matched semantic Mirage, false blocks, official scores and paired efficacy remain outstanding; goal active.')
    save(out/'status.json',status)
    note = ('## 最新补充：新32同一实际进程/九锁继续；额外持久存储仅只读检查，未迁移或改运行\n\n'
        '权威 `'+(out/'status.json').relative_to(BASE).as_posix()+'`。当前实际worker/launcher/GUI的UID/fullcmd/start、'
        '4–7独占compute/九锁及双链已核；90封存，91/judge120在生成，actor38/aux0，价格逐图已冻结17读，'
        '执行仍36、完整轨0/32。原生审计仅到87，88+尚待不重叠审计。当前未终局，不重启或热改。\n\n'
        '新增只读mount/ownership/access检查：3090的/data为独立持久分区，可用约1.48TB；'
        '/home/researcher约234.7GB；4090/data/researcher约6.27TB。没有创建存储租约、复制/删除/移动/压缩原件，'
        '未证明全32容量或改当前输出路径。混合审计包装/15CPU控制/原生buffer来源及真实noaux72/82兼容证据见紧随上一头，'
        '不要重跑这些已完成准备；actual enabled辅助整链和配对效果仍待真实轨迹。目标ACTIVE。\n\n').encode('utf8')
    (out/'new-head.md').write_bytes(note)
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    for name,value in before.items():assert sha(BASE/name)==value
    for name in ['README.md','HANDOFF.md']:
        (BASE/name).write_bytes(note+(previous/name).read_bytes())
        assert (BASE/name).read_bytes()==note+(previous/name).read_bytes()
    (BASE/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    assert sha(BASE/'full-gui-current.json')==sha(out/'status.json')
    result=dict(publication=str(out),status_sha256=sha(out/'status.json'),seal_sha256=sha(out/'seal.json'),
                three_heads_original_byte_readback_passed=True,goal='active')
    save(pointer,result)
    print(__import__('json').dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    main(p.parse_args().evidence.resolve())
