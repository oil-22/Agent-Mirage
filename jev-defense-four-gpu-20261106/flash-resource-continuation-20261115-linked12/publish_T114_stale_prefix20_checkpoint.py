"""Publish the source-only prefix and current admission state; no inference."""
import json
import time
from pathlib import Path
from control import HERE, remote, save, sha
from offline_followup_control import PREP, REMOTE, OUTPUT, OLD_REMOTE, OLD_OUTPUT, COMMAND_NAME


def load(path):
    return json.loads(path.read_bytes())


def main():
    review = HERE / 'T114-stale-baseline-prefix20-source-review-1794679139105022900'
    binding = HERE / 'source-native-prefix-binding-1794679228425689900'
    native = HERE / 'live-evidence-incremental-1794679188162873900'
    for root in [review, binding, native]:
        assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    r = load(review / 'review.json')
    b = load(binding / 'binding.json')
    assert r['candidate_coverage'] == b['candidate_coverage'] == 20
    assert b['run_id'] == 'flash14-T114-stale_replace-baseline'
    assert r['definite_positive_candidates'] == [] and r['unresolved_candidates'] == [15, 16, 18, 19]
    assert r['partial_prefix_only'] and r['trajectory_semantic_Mirage'] is None
    assert not (PREP / 'submission.json').exists()
    code = ('PACKAGE=' + repr(REMOTE) + '\nOLD_PACKAGE=' + repr(OLD_REMOTE)
            + '\nOUTPUTS=' + repr([OUTPUT, OLD_OUTPUT]) + '\nCOMMAND_NAME=' + repr(COMMAND_NAME) + '\n' + r'''
import json,os,sys,time
from pathlib import Path
assert os.getuid()==1033
p=Path(PACKAGE);sys.path.insert(0,str(p));import offline_guard as g
assert 'torch'not in sys.modules
assert not(p/'previous-GUI-admission.json').exists()and not(Path(OLD_PACKAGE)/'previous-GUI-admission.json').exists()
assert all(not Path(v).exists()for v in OUTPUTS)
assert not list((g.LEASE.parent/'commands').glob(Path(COMMAND_NAME).stem+'*'))
status=g.load(Path(g.load(p/'aggregate-bindings.json')['continuation_output'])/'primary/status.json')
assert status['phase']!='completed'and status['done']<13
print(json.dumps({'time':time.time(),'status':status,'approved_offline10_submitted':False,
 'old_and_new_output_and_shared_command_absent':True,'new_model_GPU_GUI_calls':0}))
''')
    raw, operation = remote('3090', code, 'approved10-unsubmitted-source-prefix20-checkpoint')
    actual = json.loads(raw)
    completed = 16 + actual['status']['done']
    dest = HERE / ('T114-stale-prefix20-checkpoint-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'status.json', {'time': time.time(), 'goal': 'active', 'completed_logical_GUI_configurations': completed,
        'expected_logical_GUI_configurations': 29, 'source_review': str(review), 'source_review_seal_sha256': sha(review / 'seal.json'),
        'source_native_binding': str(binding), 'binding_seal_sha256': sha(binding / 'seal.json'),
        'native_audit': str(native), 'native_seal_sha256': sha(native / 'seal.json'),
        'source_candidate_coverage': 20, 'definite_positive_candidates': [], 'unresolved_candidates': [15, 16, 18, 19],
        'partial_prefix_only': True, 'whole_trajectory_Mirage_label': None,
        'pair_or_overall_effectiveness_proven': False, 'offline_actual_state': actual, 'offline_operation': str(operation),
        'all29_and_actual_process_exits_required_before_offline10': True, 'formal_changed_GUI_authorized': False,
        'new_model_GUI_calls_by_checkpoint': 0})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    archive = dest / 'previous-heads'
    archive.mkdir()
    header = (f'## 最新续检：{completed}/29终局；T114旧帧基线前20源审，批准10离线仍未提交\n\n'
        f'权威 {HERE.name}/{dest.name}/status.json。20完整body/全史/16原PNG/候选已源审并绑定原生输入、EOS、原解析动作；15/16/18/19人物排除子句未决，0确定阳性仅限此前缀，整轨未知，不作成功。native累计114主/68Flash，实际UID/fullcmd/start/UUID/compute与主17/Flash9继承锁通过；旧raw保留原核验时点，当前组退出fresh全量仍待。CPU68未重复。\n\n'
        f'原GUI继续原版，父16+新{actual["status"]["done"]}={completed}终局；最新运行位置以回执status实际时点为准。批准10离线新旧输出/共用命令均未出现，0调用；只有ALL29逻辑终局/30attempt seals和链及全部实际模型/GUI/launcher退出后collect_aggregate_completion.py，再offline_followup_control.py submit一次。不重问、不绕过准入、不发布正式新提示GUI。后续native从live-evidence-incremental-1794679188162873900继续，source从T114-stale-baseline-prefix20-source-review-1794679139105022900继续。旧终局/已完成父fresh/容量不重跑，目标ACTIVE、降低未证。以下为历史。\n\n')
    for i, path in enumerate([HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']):
        prior = path.read_bytes()
        (archive / ('%02d-%s' % (i, path.name))).write_bytes(prior)
        path.write_bytes(header.encode('utf8') + prior)
    pointer = HERE / 'active-source-prefix-current.json'
    if pointer.exists():
        (archive / pointer.name).write_bytes(pointer.read_bytes())
    pointer.write_text(json.dumps({'publication': str(dest), 'seal_sha256': sha(dest / 'seal.json'),
        'source_review': str(review), 'binding': str(binding), 'native': str(native),
        'goal': 'active', 'completed_trajectory_review': False}, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'checkpoint': str(dest), 'source_prefix_coverage': 20, 'unresolved': [15, 16, 18, 19],
        'actual_status': actual['status'], 'approved_offline_calls': 0, 'goal': 'active'}))


if __name__ == '__main__':
    main()
