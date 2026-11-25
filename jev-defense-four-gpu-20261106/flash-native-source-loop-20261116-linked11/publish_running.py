"""Current actual GUI launch and repaired-source handoff; no efficacy claim."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    pp = json.loads((HERE / 'preparation-current.json').read_bytes()); package = Path(pp['package'])
    assert sha(package / 'manifest.json') == pp['manifest_sha256']
    assert (HERE / 'GUI-submission.json').exists()
    runtime = sorted(HERE.glob('runtime-evidence-*'))[-1]
    root = HERE / ('running-publication-' + str(time.time_ns())); root.mkdir()
    prior = HERE.parent / 'flash-native-source-loop-20261116-09'
    failure = json.loads((prior / 'startup-failure-preservation-current.json').read_bytes())
    quality = json.loads((HERE.parent / 'flash-quality-only-development-20261116-10/release-readiness-current.json').read_bytes())
    note = f'''## 2026-11-16 当前：同版四种注入8条＋正常对照2条完整GUI已实际启动，尚未终局

最新用户持续目标授权：不断实验，直到完整防御闭环并尽可能减少过度防御；不再重复询问此前已给新迭代的授权。权威目录 `{HERE}`，manifest {pp['manifest_sha256']}。原任务T114/T125×buttons_only/silent_drop/blank_replace/stale_replace/clean_control，共10条预封队列，原每轨50步/70actor/2048输出/full main history/BF16/SDPA/seed42/native parser/actions/scorer保持。NO持续同live真实新挑战复拍至YES/手停。新控制严格有限，不自动重试任何终局，不启旧队列/注意力/旧broker/其他Jev服务，不抢外人GPU。

Flash仍每次只有原完整单图和固定提示，无主任务/历史/旧图/前次回复/KV。本版固定质量提示明确允许可读合法极简/单按钮，已完成独立20PNG预检并逐实际wire/forward tensors/IDs/pixels/grid/完整prompt/raw head/概率/argmax/noKV/源链/退出/三锁审计；11正常全部YES（包括此前原prompt和严格prompt误拒的n01），6不可用全部NO，2稀疏图仅诊断/c18未决。权威 {quality['root']}；不能把开发20图叫GUI成功或泛化0误拦。

缺图前置NO；签名正常原始截图在前，原CSS只在原详情页临时渲染交付替换图后移除，不签名该替换图；来源回执拒绝换图/旧回执，真实同live复拍后来源YES才进Flash。19新真实浏览器/源控制、11路由控制及完整原图/签名/链/真实退出已核验，不等于模型/GUI效果；来源本身签坏图仍是局限。仅PRIVATE攻击选择桥可读URL/固定CSS，guard/Flash/主模型不读PRIVATE评估或URL元数据。来源NO不能说成Flash识别了攻击。

原09 startup因历史capacity源码绑定仍要求旧Flash contract而在加载后严格拒绝，实际0主/0Flash推理/0GUI。38原文件/日志、3实际退出身份及17内核锁释放已保存 {failure['root']}。原历史capacity proof及旧contract未重写；当前仅新增独立绑定已审计新Flash contract，内存算术/安装操作/主generate原source不变，9新CPU元数据边界通过，19/11旧控制精确SHA复用不重跑。此关联尝试linked11独立manifest/路径/租约/轨迹ID；所有09文件终局不改。

新launcher3150967/主3151669/Flash3151214仅首次定位，必须inspect实际UID/fullcmd/start/锁。runtime-evidence {runtime.name}验证3身份UID1033、各17真实继承锁、8卡均只有本主/Flashcompute；GUI outer1490481 UID1015，已一次启动。8张3090=7主＋1Flash均计保留成本；不沿用旧租约。前台只读watcher exec session49839跟进，不重开watcher/prepare/stage/submit/gui。最新collect_progress.py及原始回执优先，running flag/PID不作进展证明。

当前0/10完整GUI终局，成功计数尚未更新。每条需完整wire/实际input与自然EOS/Flash原始概率/noKV/原始图/源回执/链/原生dispatch审计，独立正常图复核后才算闭环；2条clean原图需独立审查，所有非注入NO先审图再判断是否误拦。主模型正常图文字误读按用户口径不计门控失败，官方任务分数独立。最终全组实际退出、源请求集与全raw seal绑定、17锁释放及8卡成本后报告，不因launch/子组完成标goal完成。目标ACTIVE。

'''
    (root / '当前完整GUI实验与误拦修复进展-20261116.md').write_text(note, encoding='utf8')
    for name in ['HANDOFF.md','README.md']:
        target = HERE.parent / name; (root / ('previous-' + name)).write_bytes(target.read_bytes()); target.write_text(note + target.read_text('utf8'), encoding='utf8')
        (HERE / name).write_text(note, encoding='utf8')
    save(root / 'bound.json', {'preparation': pp, 'runtime_evidence': str(runtime), 'runtime_seal_sha256': sha(runtime / 'seal.json'), 'quality': quality, 'linked_failure': failure, 'new_model_GUI_calls': 0})
    save(root / 'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), 'active_study': str(HERE), 'state': 'GUI_running_not_completed', 'goal_active': True}
    save(HERE / 'publication-current.json', pointer)
    target = HERE.parent / 'active-defense-goal-current.json'
    if target.exists(): (root / 'previous-active-defense-goal-current.json').write_bytes(target.read_bytes())
    target.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
