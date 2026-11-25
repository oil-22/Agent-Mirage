"""Snapshot mutable handoffs, then publish current protocol state and limits."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    base = HERE.parent
    prepared = json.loads((HERE / 'preparation-current.json').read_bytes())
    routing = json.loads((HERE / 'CPU-routing-current.json').read_bytes())
    progress_pointer = json.loads((HERE / 'live-progress-current.json').read_bytes())
    progress = json.loads((Path(progress_pointer['root']) / 'result.json').read_bytes())['result']
    status = progress['status'] or {}
    rows = progress['rows']
    root = HERE / ('publication-' + str(time.time_ns()))
    root.mkdir()
    (root / 'before').mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    review = {'source_review': 'single researcher, source and control outcomes visible, not blind',
              'independent_acquisition_program': 'capture_source.py exclusively owns original native browser/environment',
              'no_arbitrary_bytes_signing_API': True, 'private_key_only_in_source_process_memory': True,
              'Controller_pins_public_key_session_environment_source_SHA': True,
              'nonce_issue_and_consumption_atomic_persistent_SQLite_FULL': True,
              'current_signature_verifier_boundary_controls': 20, 'source_live_controls': 16,
              'routing_stub_model_controls': 7, 'source_live_native_WAIT_actions': 1,
              'source_signed_blank_footer_lonebutton_receipts_are_valid': True,
              'same_uid_trusted_OS_and_program_assumption_explicit': True,
              'no_PRIVATE_reference_or_attack_label_used_by_guard': True,
              'original_Flash_contract_and_primary_native_generation_unchanged': True,
              'normal_image_notes_are_evaluation_only': True,
              'not_model_semantic_accuracy_or_population_effectiveness_evidence': True}
    save(root / 'source-review.json', review)
    main_count = sum(v['main_replies'] for v in rows)
    receipt_no = sum(v['receipt_NO'] for v in rows)
    head = f'''## 2026-11-16 最新：用户已批准可信采集回执，新协议两条旧帧GUI实际运行

权威目录 `{HERE}`，新preparation manifest {prepared['manifest_sha256']}。用户直接回复“增加可信采集回执，另设新协议验证”；先前待答复选择已解决。当前新协议只验证T058/T089两条新的stale_replace完整GUI，旧10终局保持，按钮遮罩不足不因此改成成功。progress指针 `{HERE / 'live-progress-current.json'}`；本快照{status.get('processed', 0)}/2终局、{main_count}完整主回复、来源NO={receipt_no}，phase={status.get('phase')}；完成整轨wire/张量/概率/原生动作/签名/持久化账本与原图审查前不计为成功。

独立采集进程拥有原生同live浏览器，收到新挑战才真实_get_obs，以Ed25519签完整PNG/环境/session/动作序号/captureID/sourceSHA；私钥只在采集进程内，接口不接受任意图片签名，Controller只有绑定公钥和SQLite原子持久化一次性账本。传输旧图在签名后注入，来源NO跳过Flash/主并真实复拍，来源通过才进原单图固定Flash；不加任务/主历史/旧帧/先前判定/KV。它防可信采集后的替换和旧回执重放，依赖可信OS/Controller/采集程序，不能识别源端本身签出的坏图，不能称Flash看出了旧帧。原27B完整历史/system/BF16/SDPA/seed42/2048输出/50步70actor、原生parser/action/scorer保持。

当前版本20协议边界、16真实采集/接口控制、7新Controller路由检查通过；包含并发/重启重放、相同像素新采集允许、来源自己签坏图不保证识别及纯nativeWAIT。工程证据不作防御效果。初始浏览器路径与DetachedPage传输失败、Windows SQLite未及时关闭诊断及所有原源/日志/回执均保留，新关联技术预检完成；已完成source控制精确复用，不重跑完整终局/旧20样本。主/Flash/GUI均已在新租约真正启动；launcher3007179/主3007821/Flash3007404仅首次引用，实际UID1033/fullcmd/start/每进程17继承锁及无外人compute已核实；GUI outer1264828 UID1015。新watcher前台exec session47249跟进，勿重复启动、勿重复stage/submit/gui。

原resource-attempt-20261106-01/broker已释放退休，本轮launch_group直接重新独占8张3090，7主+1Flash、全部8卡计成本，每次请求核对compute。结束后模型/launcher自行退出并关闭本轮锁，不留broker；未来不得重跑旧resource_control --worker。当前源码/运行包一旦使用不原地改版，技术续试须新关联attempt、保留失败。进展以最新不可变回执为准；旧帧组完成也不代表四种各两条或总体Mirage降低。以下旧快照保留。

'''
    targets = [('new-HANDOFF.md', HERE / 'HANDOFF.md'), ('new-README.md', HERE / 'README.md'),
               ('main-HANDOFF.md', base / 'HANDOFF.md'), ('main-README.md', base / 'README.md'),
               ('parent-HANDOFF.md', base / 'flash-four-injection-defense-20261115-04/HANDOFF.md')]
    transitions = []
    for label, path in targets:
        old = path.read_bytes()
        (root / 'before' / label).write_bytes(old)
        path.write_bytes(head.encode('utf-8') + old)
        transitions.append({'path': str(path), 'before_sha256': sha(root / 'before' / label), 'after_sha256': sha(path)})
    save(root / 'state.json', {'created': time.time(), 'authorization': str(HERE / 'user-authorization.json'),
                              'preparation': prepared, 'routing': routing, 'progress': progress_pointer,
                              'prior_choice_resolved': True, 'new_protocol_in_actual_GUI': True,
                              'full_trajectory_success_not_yet_claimed': True, 'old_four_mode_target_still_unmet': True,
                              'new_calls_by_publication': 0, 'transitions': transitions})
    save(root / 'seal.json', {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json')}
    for path in [HERE / 'publication-current.json', base / 'trusted-capture-protocol-current.json']:
        temp = path.with_name('.' + path.name + '.' + str(time.time_ns()))
        save(temp, pointer)
        temp.replace(path)
    print(json.dumps({'root': str(root), 'new_protocol_GUI_started': True, 'source_NO': receipt_no, 'complete_main_replies': main_count}))


if __name__ == '__main__':
    main()
