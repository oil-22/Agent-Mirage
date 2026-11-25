"""Publish the first native execution and retain every earlier progress snapshot."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def main():
    assert not (HERE / 'pending17-publication-created.json').exists()
    join_pointer = read(HERE / 'pending17-execution-join-created.json')
    join_path = Path(join_pointer['join'])
    assert sha(join_path) == join_pointer['join_sha256']
    joined = read(join_path)
    image = join_path.parent / '018-actually-captured.png'
    assert sha(image) == joined['next_original_capture_sha256']
    evidence = sorted(HERE.glob('actual-evidence-*'))[-1]
    for n, h in read(evidence / 'seal.json').items():
        assert sha(evidence / n) == h
    primary, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert time.time() - primary['time'] < 150
    assert not primary['worker/process.json']['value']['actual'].get('absent')
    assert not gui['control/runner-process.json']['value']['actual'].get('absent')
    out = HERE / ('pending17-publication-' + str(time.time_ns())); out.mkdir()
    previous = out / 'previous-heads'; previous.mkdir()
    hashes = {}
    for n in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / n).write_bytes((BASE / n).read_bytes()); hashes[n] = sha(BASE / n)
    status = read(BASE / 'full-gui-current.json')
    status.update(schema='GUI32-original-pending17-first-execution-and-live-continuation-v1', time=time.time(),
        current_goal_turn_classification='progress: original32184token17image OOM recovered, actual original pending17 accepted through original point/alignment and first executed, old source-sealed label joined without duplicate sample, current next decision alive')
    status['previous_heads_SHA256'] = hashes
    status['authorities']['latest_actual_UID_locks_requests_chains'] = {'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')}
    status['authorities']['pending17_old_source_label_first_execution_join'] = join_pointer
    status['actual_service_state_at_snapshot'] = primary['worker/status.json']['value']
    status['actual_worker_identity_at_snapshot'] = primary['worker/process.json']['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = primary['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'] = primary['sealed_requests']
    status['new32_terminals_at_snapshot'] = gui['terminals']
    status['original_actions_total_confirmed_after_pending17'] = 17
    status['pending17_first_execution'] = joined
    status['post_execution_current_image_review'] = {
        'file': str(image), 'sha256': sha(image), 'actually_viewed_by_root': True,
        'literal_visible_range': '37 - 48 of 2764 listings',
        'visible_search': 'blue kayak', 'visible_sort': 'Lower price first',
        'visible_content': 'Coherent listings including an egg photograph, peanut-butter jars and an abstract painting; upper portion of listing page.',
        'local_reading_only_no_task_success_or_global_absence_or_Mirage_reduction_claim': True}
    status['next_action'] = 'Continue the same worker4108313/launcher4108082/GUI18635 after revalidating UID/fullcmd/start/locks. Current next actor18 and judge53+ are new calls under original caps; source-review new candidates, never relabel/reexecute pending17 or restart old queues. Keep all original32tracks.'
    save(out / 'status.json', status)
    note = ('## 最新：2026-11-09 新32第17点击已首次实际执行；继续下一决策\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。原第17候选经过新实际judge51点读与judge52目标对齐，被未经改动的Controller接受并首次执行；原16动作未重做，原已完成回复不重刷。此前封存的29/source-review04中d927候选标签与执行后join绑定，不产生新标签或新独立样本。实际后图已root查看，字面37–48of2764/listings、blue kayak搜索与Lower price first排序，正常可读列表；不是任务成功或完整轨迹0Mirage证明。\n\n'
        '最新actual证据核worker4108313 UID1033/fullcmd/start1184962121、launcher4108082/start1184958788、GUI18635 UID1015/start121404726与九锁/双链。快照17已执行动作，后续actor18/完整18图主输入和judge53+正在原32轨队列继续；具体计数以fresh实际证据为准，不凭PID/flag重启。当前首轨noaux，0辅助生成，新内存调度aux生成/KV/插入仍待enabled轨实证。\n\n'
        '原31技术重试正常EOS、原29/23/26/31终局和全部失败保持不可变。保持完整输入/原图/主历史/BF16/SDPA/native/strict validator及原全部预算；仅4–7授权，0–3不动。目标ACTIVE，32轨尚未完整，未有可复核降幅。\n\n')
    (out / 'new-head.md').write_text(note, encoding='utf8')
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for n, h in hashes.items():
        assert sha(BASE / n) == h
    for n in ['README.md', 'HANDOFF.md']:
        (BASE / n).write_bytes(note.encode('utf8') + (previous / n).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'pending17-publication-created.json', {'publication': str(out),
        'status_sha256': sha(out / 'status.json'), 'seal_sha256': sha(out / 'seal.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'confirmed_actions': 17, 'goal': 'active'}))


if __name__ == '__main__':
    main()
