"""Seal the incomplete observer publication and complete only its mutable heads."""
import copy
import json
from pathlib import Path
import time

import orchestrate as o
from join_source_reviews import verify_seal


def main():
    pointer = o.HERE / 'stale-aux-closed-terminal-publication-created.json'
    assert not pointer.exists()
    candidates = [p for p in o.HERE.glob('stale-aux-closed-terminal-publication-*') if p.is_dir()]
    assert len(candidates) == 1
    failed = candidates[0]
    assert not (failed / 'seal.json').exists()
    old_report = (failed / 'report.md').read_text(encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (o.BASE / name).read_bytes() == old_report.encode('utf8') + (failed / ('before-' + name)).read_bytes()
    assert (o.BASE / 'full-gui-current.json').read_bytes() == (failed / 'before-full-gui-current.json').read_bytes()
    o.save(failed / 'publication-observer-failure.json', dict(time=time.time(),
        error_type='FileExistsError', location='o.save(o.BASE / full-gui-current.json, status)',
        cause='The shared immutable-file save helper opens with x; a mutable current pointer already exists.',
        model_GUI_or_scorer_failure=False, model_GUI_scorer_calls=0,
        original_logs_requests_and_terminals_unchanged=True,
        heads_prepended_before_status_write=True, original_current_pointer_preserved=True))
    o.save(failed / 'seal.json', {p.name: o.sha(p) for p in failed.iterdir() if p.is_file()})
    verify_seal(failed)
    root = o.HERE / ('closed-terminal-publication-linked02-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    status = copy.deepcopy(json.loads((failed / 'status.json').read_bytes()))
    status['authorities']['closed_terminal_publication'] = str(root)
    status['authorities']['linked_incomplete_publication'] = dict(root=str(failed), seal_sha256=o.sha(failed / 'seal.json'))
    o.save(root / 'status.json', status)
    (root / 'review.json').write_bytes((failed / 'review.json').read_bytes())
    report = old_report.replace(failed.relative_to(o.BASE).as_posix(), root.relative_to(o.BASE).as_posix(), 1)
    report += ('本地发布观察器首次用不可变文件的独占创建函数更新既有current指针而失败，已封存该观察器快照。'
               '新链接仅完成可变头部/指针更新并逐字节回读；模型、GUI、原始终局和实验条件均未改动。\n\n')
    (root / 'report.md').write_text(report, encoding='utf8')
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (root / ('before-' + name)).write_bytes((o.BASE / name).read_bytes())
    # These are explicitly mutable discovery pointers, not any immutable receipt.
    (o.BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        (o.BASE / name).write_bytes(report.encode('utf8') + (failed / ('before-' + name)).read_bytes())
    assert json.loads((o.BASE / 'full-gui-current.json').read_bytes()) == status
    for name in ['README.md', 'HANDOFF.md']:
        assert (o.BASE / name).read_bytes() == report.encode('utf8') + (failed / ('before-' + name)).read_bytes()
    o.save(root / 'receipt.json', dict(passed=True, all_three_mutable_heads_verified=True,
        original_observer_failure_preserved=str(failed), original_failure_seal_sha256=o.sha(failed / 'seal.json'),
        original_model_GUI_terminal_conditions_unchanged=True, new_model_GUI_scorer_calls=0))
    o.save(root / 'seal.json', {p.name: o.sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), status_sha256=o.sha(root / 'status.json'), review_sha256=o.sha(root / 'review.json'),
        seal_sha256=o.sha(root / 'seal.json'))
    o.save(pointer, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
