"""Preserve previous handoff bytes and publish a current, evidence-bound checkpoint."""
import json
import os
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    pointer = json.loads((HERE / 'live-progress-current.json').read_bytes())
    progress = Path(pointer['root'])
    assert sha(progress / 'seal.json') == pointer['seal_sha256']
    for name, expected in json.loads((progress / 'seal.json').read_bytes()).items():
        assert sha(progress / name) == expected
    value = json.loads((progress / 'result.json').read_bytes())['result']
    root = HERE / ('progress-publication-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'checkpoint.json', {'progress_pointer': pointer,
         'status': value['status'], 'verified_main_replies_at_checkpoint': sum(v['main_replies'] for v in value['rows']),
         'complete_trajectories': sum(v['complete'] for v in value['rows']),
         'final_success_counts_pending_full_audit_and_image_review': True,
         'new_model_GUI_calls_by_publication': 0})
    status = value['status'] or {}
    head = ('## 最新：新框架四种原始注入各2条，8条GUI已实际启动\n\n'
            f"权威 flash-four-injection-defense-20261115-04/live-progress-current.json；本checkpoint {sum(v['complete'] for v in value['rows'])}/8终局，"
            f"{sum(v['main_replies'] for v in value['rows'])}完整主回复，实际活动 {status.get('run_id')}。"
            'T058/T089×silent_drop/blank_replace/stale_replace/buttons_only，全新once-only轨迹；'
            '缺图前置NO跳过Flash并真复拍，有图进原固定单Flash，NO同live复拍至YES/手停。'
            '首个缺图已实际前置NO→真复拍→YES→原生动作；完整8轨与fresh raw审计/原图复核尚待，不先报每组成功数。\n\n'
            '原始按钮CSS/detail触发与单次替换规则保持；旧帧可读时可能Flash YES，不能用PRIVATE标签强制拒绝。'
            '主27B全史/system/seed42/BF16/SDPA/2048/50步70actor与唯一Flash单图固定prompt/无上下文KV保留；'
            '沿用实际验证继承锁的7主+1Flash充裕方案，全部8卡计成本，无付费API。'
            '11新CPU路由测试通过，不作模型证据；父18缺图测试/4真实旧闭环/旧终局不重跑。'
            '主2741685、Flash2741214、launcher2740930和GUI329818/329833身份已核对；后续必须查实际UID/fullcmd/start/锁，不信旧PID。'
            '不得重复prepare/stage/submit/gui，不恢复旧队列。以下旧快照。\n\n')
    for name in ['README.md', 'HANDOFF.md']:
        target = HERE.parent / name
        raw = target.read_bytes()
        (root / ('previous-' + name)).write_bytes(raw)
        updated = head.encode('utf8') + raw
        (root / ('next-' + name)).write_bytes(updated)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    for name in ['README.md', 'HANDOFF.md']:
        target = HERE.parent / name
        assert target.read_bytes() == (root / ('previous-' + name)).read_bytes()
        temporary = target.with_name('.four-mode-' + str(time.time_ns()))
        with temporary.open('xb') as handle:
            handle.write((root / ('next-' + name)).read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    save(HERE / ('publication-' + str(time.time_ns()) + '.json'), {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'checkpoint': str(root), 'status': value['status']}))


if __name__ == '__main__':
    main()
