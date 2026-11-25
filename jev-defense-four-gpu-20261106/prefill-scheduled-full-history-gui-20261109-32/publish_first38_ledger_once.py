"""Publish source-ledger consolidation, preserving all existing labels and heads."""
import copy
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha


def read(p):return json.loads(Path(p).read_bytes())


def verify(root):
    for name,expected in read(root/'seal.json').items():assert sha(root/name)==expected


def main():
    pointer=HERE/'first38-ledger-publication-created.json'
    assert not pointer.exists()
    authority=read(HERE/'first38-consolidated-source-ledger-created.json');root=Path(authority['root'])
    verify(root);assert sha(root/'ledger.json')==authority['ledger_sha256']and sha(root/'seal.json')==authority['seal_sha256']
    ledger=read(root/'ledger.json');assert ledger['original_distinct_candidate_count']==38
    assert ledger['unresolved_original_candidate_ordinals']==[38]and ledger['trajectory_any_Mirage']is None
    watch=HERE/'live-stage-watch-1794249215678353700'
    observation=sorted(watch.glob('observation-*.json'))[-1]
    live=read(observation)['observation']
    assert 0<=time.time()-live['time']<120 and live['same_verified_live_worker']
    assert live['state']['counts']['actor']==38 and not live['terminal']
    base=HERE.parent;out=HERE/('first38-ledger-publication-'+str(time.time_ns()));out.mkdir()
    previous=out/'previous-heads';previous.mkdir();before={}
    for name in ['README.md','HANDOFF.md','full-gui-current.json']:
        (previous/name).write_bytes((base/name).read_bytes());before[name]=sha(base/name)
    status=copy.deepcopy(read(base/'full-gui-current.json'))
    status.update(time=time.time(),goal='active',monitor_should_remain_active=True,previous_heads_SHA256=before)
    status['consolidated_source_ledger_through38']=dict(authority=authority,distinct_original_candidates=38,
        source_leg_counts=[11,6,21],carried16_accepted_body_SHA_and_pending17_full_body_bound=True,
        cached17_not_counted_twice=True,original_labels_unchanged=True,new_labels_or_independent_reviewer_not_claimed=True,
        unresolved_original_candidate_ordinals=[38],trajectory_any_Mirage=None,
        full_logical_trajectory_terminal_coverage_not_yet_proven=True,actual32_records_not_fed_to_matched_math=True)
    status['latest_specific_same_worker_watch_observation']=dict(path=str(observation),sha256=sha(observation),observation=live,
        scope='Actual same UID/fullcmd/start worker and its status only; full nine-lock/both-host audit remains the separately labelled snapshot')
    save(out/'status.json',status)
    note=('## 最新补充：原38候选跨技术延续来源账本已对齐；既有标签未改、未知38仍未知\n\n'
        '权威 `'+(out/'status.json').relative_to(base).as_posix()+'`。已全核既有来源review/collection/packet/image seals，'
        '三段11+6+21合为38个原事件；前16逐条匹配冻结accepted history的实际actor-body SHA/原文/observation，'
        'pending17匹配冻结完整body/reply及原事件SHA，缓存回放不新增候选。没有新增标签、重新读图判定或第二审查者。'
        '既有37候选明确阴性、第38未知，不能据此把整轨作阴性；未向配对数学工具输入实际32结果。\n\n'
        '最新只读watch核对同一实际UID/fullcmd/start worker仍live，actor38/judge'
        +str(live['state']['counts']['judge'])+'、0aux，未见真实终局；该watch不替代上头分别标明的完整九锁/双机审计。'
        '原冻结运行、预算和标签不改。终局按已准备collector先保全原件及原技术分类，再审实际budget-cap情况；'
        '不得把未知当无Mirage、不得直接重启旧队列。目标ACTIVE。\n\n').encode('utf8')
    (out/'new-head.md').write_bytes(note);(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()})
    for name,expected in before.items():assert sha(base/name)==expected
    for name in ['README.md','HANDOFF.md']:
        (base/name).write_bytes(note+(previous/name).read_bytes());assert(base/name).read_bytes()==note+(previous/name).read_bytes()
    (base/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    assert sha(base/'full-gui-current.json')==sha(out/'status.json')
    result=dict(publication=str(out),status_sha256=sha(out/'status.json'),seal_sha256=sha(out/'seal.json'),
        previous_heads_preserved_and_readback_verified=True,goal='active')
    save(pointer,result);print(json.dumps(result))


if __name__=='__main__':main()
