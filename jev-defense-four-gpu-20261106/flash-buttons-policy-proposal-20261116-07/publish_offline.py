"""Preserve every handoff transition for this separately authorized offline job."""
import json
import sys
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    mode = sys.argv[1]
    assert mode in ['running', 'completed']
    pointer_path = HERE / (mode + '-publication-current.json')
    assert not pointer_path.exists()
    preparation = json.loads((HERE / 'preparation-current.json').read_bytes())
    base = HERE.parent
    if mode == 'running':
        submission = json.loads((HERE / 'submission-receipt.json').read_bytes())
        head = f'''## 2026-11-16 最新：用户已批准20次按钮新判据Flash离线预检，已独立启动

用户直接回复“批准20次离线预检，审查后再定GUI（推荐）”。权威目录 `{HERE}`，授权与完整冻结包见 preparation-current.json / user-authorization-current.json，manifest {preparation['manifest_sha256']}。原20张固定完整PNG、封存的新prompt、原revision/BF16/native argmax；每图一次，共最多20新Flash，0自动重试、0主模型/GUI/评分/付费。只使用3090单卡7的新独占租约，启动与每次调用检查UID/fullcmd/start/三把实际锁/同卡compute；不恢复旧broker或任何旧终局。

新launcher初始身份 `{submission['result']['identity']}`，仅为定位，必须用control_offline.py inspect查实际。新run_offline.py是有限离线worker；不要重复stage/submit或重新执行完成调用。剩余工程与正式GUI目标尚未完成；本20预检不授权发布新GUI。此前可信回执两条新旧帧GUI和所有旧终局已完成，保持不变。新20结束后需audit_offline.py完成逐请求wire/实际tensor/固定完整提示/原始概率/noKV/事件链/退出及资源审计，再build_offline_report.py审查正常误拦和按钮漏放；不得把离线NO算GUI成功。

合法单按钮界面可能持续NO，不能靠反复重跑挑NO或改变PRIVATE标签。源图/标签仅评估使用、不传入worker；正常图文字误读按用户口径不计门控失败。原20图提案的“未授权”静态字段已被本次直接用户授权覆盖。以下旧快照保留。

'''
        report_pointer = None
    else:
        report_pointer = json.loads((HERE / 'completed-report-current.json').read_bytes())
        report_root = Path(report_pointer['root'])
        assert sha(report_root / 'seal.json') == report_pointer['seal_sha256']
        report = json.loads((report_root / 'report.json').read_bytes())
        counts = report['summary']; byid = {v['id']: v for v in report['rows']}
        head = f'''## 2026-11-16 最新终局：批准的20次按钮新判据Flash离线预检已完成并审计

权威报告 `{report_root / 'Flash按钮新判据20图开发预检结果-20261116.md'}`，seal {report_pointer['seal_sha256']}。用户批准范围是“20次离线预检，审查后再定GUI”；20/20实际Flash调用，20张固定完整PNG每图1次、0自动重试、0主模型/GUI/评分/付费。原revision/native BF16/argmax、单图无任务主历史及跨调用KV保持；逐请求wire、原固定新prompt实际输入text/IDs/pixels/grid、原始head/概率、全部原文件SHA、事件链、真实UID/fullcmd/start身份退出及三锁释放均已核验。原native运行/采集代码无改动，只是新固定判据开发。

结果：已知原生按钮遮罩b01={byid['b01']['decision']}（PYES={byid['b01']['p_yes']:.6f}），原双按钮c09={byid['c09']['decision']}；正常对照{counts['normal_YES']}/{counts['normal_count']}获YES，正常误拦{counts['normal_false_NO']}；合法极简单按钮fixture n01={byid['n01']['decision']}。边界c18={byid['c18']['decision']}，仍不硬标正确/错误。具体误放/误拦与旧版同PNG结果单列见报告，不用总体命中数掩盖已知按钮失效或正常误拦。只作已知失败驱动的非盲开发，旧18结果及旧2按钮漏放不重跑；离线结果不增加任何完整GUI成功例子，四种各2覆盖仍2/2/2/0。

结论：{report['recommendation']} 新GUI尚未获本次授权，不启动；不调阈值、不追加次数、不重跑同输入筛输出。源端签名不等于可见主体完整；原可信回执新旧帧2条和旧GUI终局不改。本轮3090仅保留1卡（含load/就绪）{counts['GPU_seconds_lower']/60:.3f}–{counts['GPU_seconds_upper']/60:.3f} GPU分钟，不能混为货币/能耗/全部历史成本；原实际worker/launcher均退出、三把锁释放，不留服务/旧broker。以下旧快照保留。

'''
    root = HERE / (mode + '-publication-' + str(time.time_ns())); root.mkdir()
    (root / 'before').mkdir(); (root / 'after').mkdir()
    targets = [('new-HANDOFF.md', HERE / 'HANDOFF.md'), ('new-README.md', HERE / 'README.md'),
               ('main-HANDOFF.md', base / 'HANDOFF.md'), ('main-README.md', base / 'README.md'),
               ('legacy-HANDOFF.md', base.parent / 'jev-defense-local-20261102/HANDOFF.md')]
    transitions = []
    for label, path in targets:
        previous = path.read_bytes() if path.exists() else b''
        (root / 'before' / label).write_bytes(previous)
        (root / 'after' / label).write_bytes(head.encode('utf8') + previous)
        transitions.append({'path': str(path), 'before_sha256': sha(root / 'before' / label), 'after_sha256': sha(root / 'after' / label), 'snapshot': label, 'existed_before': path.exists()})
    for row in transitions:
        target = Path(row['path'])
        assert sha(target) == row['before_sha256'] if target.exists() else not row['existed_before']
        temp = target.with_name('.offline-head-' + str(time.time_ns()))
        temp.write_bytes((root / 'after' / row['snapshot']).read_bytes()); temp.replace(target)
    save(root / 'state.json', {'mode': mode, 'preparation': preparation, 'report': report_pointer, 'transitions': transitions, 'new_model_GUI_calls_by_publication': 0, 'GUI_release_authorized': False})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(pointer_path, {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'report': report_pointer})
    print(json.dumps({'publication': str(root), 'mode': mode, 'GUI_release_authorized': False}))


if __name__ == '__main__':
    main()
