"""Publish preparation pointers only; preserve all closed terminal authorities."""
import hashlib
import json
from pathlib import Path
import shutil
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert not (HERE / 'publication-created.json').exists(), 'Already published'
    prepared = json.loads((HERE / 'preparation-created.json').read_bytes())
    source = Path(prepared['root'])
    assert sha_bytes((source / 'seal.json').read_bytes()) == prepared['seal_sha256']
    for name, digest in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha_bytes((source / name).read_bytes()) == digest, name
    proposal = json.loads((BASE / 'native-answer-origin-staging-20261110-34' /
                           'preparation-created.json').read_bytes())
    before = {name: (BASE / name).read_bytes()
              for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    status = json.loads(before['full-gui-current.json'])
    assert status['execution_state'] == 'original_batch_exited_after_technical_terminal'
    assert status['verified_complete_original32_track_count_lower_bound'] == 3
    assert status['linked_remaining31']['remaining_original_unstarted_track_count'] == 29
    closed_authority = status['authorities']['closed_terminal_publication']
    original_linked_state = json.loads(json.dumps(status['linked_remaining31']))
    publication = HERE / ('publication-' + str(time.time_ns()))
    publication.mkdir()
    shutil.copyfile(__file__, publication / 'publish_preparation_once.py')
    for name, data in before.items():
        (publication / ('before-' + name)).write_bytes(data)
    status['time'] = time.time()
    status['current_goal_turn_classification'] = (
        'progress: source-bound remaining29 and all-original32 main-agent outcome '
        'ledger prepared; no new model result or efficacy claim')
    status['authorities']['native_answer_source_preparation_NOT_deployed'] = proposal
    status['authorities']['remaining29_primary_outcome_preparation_NOT_launched'] = prepared
    status['remaining29_preparation'] = {
        'authority': prepared,
        'original_full32_and_all16_pairs_retained': True,
        'three_closed_terminals_excluded_and_preserved': True,
        'completed_request_IDs_excluded': 362,
        'new_model_GPU_GUI_scorer_paid_calls': 0,
        'source_rule_decision_already_requested_and_still_pending': True,
        'goal_clarification_is_not_source_rule_approval': True,
        'launch_ready': False, 'new_runtime_package_built': False,
        'new_recognition_campaign_started': False,
    }
    status['unresolved_work'] = [
        'Pending already-requested user choice on exact native STOP answer origin representation',
        'Build a new linked remaining29 runtime only after that choice; freshly verify resources before launch',
        'Complete remaining29 GUI tracks and source-first review within the original32 scope',
        'Matched trajectory-level main-agent Mirage plus normal operation, false rejection, completion, exposure and cost',
        'Keep original candidate38 unresolved, known semantic failures and all original terminals/version boundaries',
    ]
    status['latest_findings'] = [
        'Preparation only: unchanged full32 plan, 16 pairs and 8 selected tasks retained; three immutable endpoints excluded; exact remaining29 queue starts at zero.',
        '362 completed/prior request IDs excluded using sealed sources. No model, GPU, GUI, scorer or paid call; no old runtime restarted.',
        'Main-agent trajectory-level Mirage is primary. Auxiliary recognition is diagnostic; later blocks, recovery or official success do not erase occurrence.',
        'Native-answer origin repair is CPU-prepared and undeployed. The already-requested condition choice remains pending; no duplicate question.',
    ]
    assert status['authorities']['closed_terminal_publication'] == closed_authority
    assert status['linked_remaining31'] == original_linked_state
    assert status['matched_efficacy_analysis_ready'] is False
    save(publication / 'status.json', status)
    header = '''## 最新：2026-11-10 以主模型 Mirage 降幅为目标；剩余29轨仅完成续跑/分析准备

辅助识别只作诊断。主要判据是完整有/无辅助匹配GUI中主模型按轨迹一次即计的Mirage；错误在候选中已出现，后续拦截、纠正或官方成功均不抹去。同步审查正常操作误拦、接受/执行错误、完成和实际暴露，不能把早停、少执行或技术终局当收益。当前尚无可核实相对降低30%或减半的证据。

新准备 `remaining29-primary-outcome-staging-20261110-35/preparation-created.json` 保留原32轨/16对/8选任务及全预算，逐字节保留并排除3个已有终局，按原序绑定29条从未开始轨迹，排除362个既有请求ID。只有本地清单/分析账本与SHA核验，0新模型/GPU/GUI/scorer调用；没有构建或启动新runtime，没有开始新识别试验。

`native-answer-origin-staging-20261110-34/preparation-created.json` 为已完成CPU验证的精确原生STOP答案来源准备，未部署。先前已提出的正式来源规则选择仍待回复；本次目标澄清不代替该选择，不重复发问。目标ACTIVE，原批次已退出，29轨未启动。旧终局权威继续保留在 `remaining-full-history-gui-20261110-33/closed-terminal-publication-linked02-1794280835290980000/status.json`，不得重启旧stage/service/gui或重跑已完成轨迹。

'''
    replacements = {
        'README.md': header.encode('utf-8') + before['README.md'],
        'HANDOFF.md': header.encode('utf-8') + before['HANDOFF.md'],
        'full-gui-current.json': (publication / 'status.json').read_bytes(),
    }
    for name, data in replacements.items():
        path = BASE / name
        assert path.read_bytes() == before[name], 'Concurrent head change: ' + name
        path.write_bytes(data)
        assert path.read_bytes() == data, 'Readback mismatch: ' + name
    receipt = {
        'preparation': prepared, 'source_rule_preparation': proposal,
        'before_sha256': {k: sha_bytes(v) for k, v in before.items()},
        'after_sha256': {k: sha_bytes(v) for k, v in replacements.items()},
        'closed_terminal_authority_unchanged': True,
        'existing_outcomes_and_semantic_labels_unchanged': True,
        'all_three_heads_exact_readback_verified': True,
        'new_model_GPU_GUI_scorer_paid_calls': 0,
        'goal': 'active', 'efficacy_established': False,
    }
    save(publication / 'receipt.json', receipt)
    save(publication / 'seal.json', {p.name: sha_bytes(p.read_bytes())
                                   for p in sorted(publication.iterdir()) if p.is_file()})
    pointer = {'root': str(publication),
               'status_sha256': sha_bytes((publication / 'status.json').read_bytes()),
               'receipt_sha256': sha_bytes((publication / 'receipt.json').read_bytes()),
               'seal_sha256': sha_bytes((publication / 'seal.json').read_bytes())}
    save(HERE / 'publication-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    main()
