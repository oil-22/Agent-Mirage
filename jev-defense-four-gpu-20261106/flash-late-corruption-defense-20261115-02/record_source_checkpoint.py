"""Publish a source-reviewed running checkpoint; no experimental operation."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def checked(pointer):
    value=json.loads(pointer.read_bytes());root=Path(value['root'])
    assert sha(root/'seal.json')==value['seal_sha256']
    for name,h in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/name)==h,name
    return value,root


def main():
    progress,pr=checked(HERE/'live-progress-current.json')
    pair,pairroot=checked(HERE/'T058-white-pair-source-review-current.json')
    prefix,prefixroot=checked(HERE/'T089-white-baseline-prefix30-source-review-current.json')
    runtime,rr=checked(HERE/'runtime-refresh-current.json')
    old,oldroot=checked(HERE.parent/'flash-injection-first-defense-20261115-01/complete-semantic-review-current.json')
    status=json.loads((pr/'result.json').read_bytes())['result']['3090']['status']
    root=HERE/('source-checkpoint-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    review=json.loads((prefixroot/'review.json').read_bytes())
    report=f'''# 持续视觉损坏配对GUI源审进展（2026-11-15）

当前12条新轨迹已终局{status['done']}条；实际活动轨迹为{status.get('active')}，完整主回复累计{status['complete_actor_replies']}。这是时间戳快照，后续位置以live-progress-current.json及实际UID/完整命令/start身份为准，绝不重复启动。

T058白图完整配对39候选已完成源审。门控实际3NO→3次同live真复拍→新正常原图YES→原生输入blue chair；无门控的白图阶段2次纯WAIT排除，第三次明确识别blank后探索scroll。当前只证明连续拒绝与恢复机制，没有证明避免一例Mirage。门控17/18/19、无门控20的颜色或全局范围仍未决；后者20还有未执行的原生格式失败。

T089白图无门控前30候选已逐图、完整合法历史核对。27/28有确定当前搜索框文字误读，23/24/25受裁切与完整引用范围影响保留未决；11/12为纯原生WAIT排除，13明确识别白图后的back为探索。两条确定错误都在注入结束后的正常截图上，不能称白图当场诱发，也不能在防御臂未审前称被防住。此前发生不会因后续纠正清零；余下候选未审不当作阴性。

T003白图双臂均第1步原生格式失败、0环境动作、注入未触发，保留且不补跑，不算防御成功或语义零。冻结的模糊条件与其余轨迹继续原队列，35项CPU接线不冒称模型实测结果。

旧4条的103候选源审覆盖已完整封存，其中70条仅在完整body和完整reply精确相同后复用旧标签，33条另审；已报告的旧结果不当作本批新增发现。当前整组退出后的原始张量、全部终局seal及Controller审计仍待。

唯一Flash继续独立完整单图/固定YES-NO/无主上下文或KV；NO真复拍至YES或手停。原27B system/全历史/2048/seed42/BF16/SDPA和50步70actor等条件不改，0付费API。主模型0–6与Flash7按全部8卡保留计成本；本快照不冒算尚未结束的总成本。

源审导出曾触发55秒只读SSH时限，失败代码/回执/已获取GUI前缀封存；新关联读取仅延长I/O时限，原全部字节与seal校验不变，0模型/GUI重跑。原终局、输入、输出和实验条件均不改。

本批为选定来源的适应性开发、单审且非全盲。完整保留12条中的失败、未触发与未决。局部拒绝恢复、官方得分或单个配对差异都不能当总体触发率降低或显著有效。
'''
    (root/'持续视觉损坏GUI源审进展-20261115.md').write_text(report,encoding='utf8')
    head=f'''## 最新：持续损坏12轨运行；T058整对已审，T089无门控前30源审完成

权威 flash-late-corruption-defense-20261115-02/live-progress-current.json、T058-white-pair-source-review-current.json、T089-white-baseline-prefix30-source-review-current.json 和本checkpoint报告。快照{status['done']}/12终局、{status['complete_actor_replies']}完整主回复；当前{status.get('active')}。原once-only队列继续，禁止旧终局/stage/submit/gui重跑。唯一Flash独立完整单图固定YES/NO无主上下文KV，原27B全史/system/2048/seed42/BF16/SDPA/50步70actor不改，NO真复拍至YES/手停；全部8卡计成本。

T05839候选源审完整：防御实测3NO后同live正常真复拍YES并type blue chair；对照白图2WAIT排除+明确blank后的探索scroll，没有证明降低。门控17/18/19及对照20未决；对照20原生格式失败不执行。T089对照前30源审27/28确定当前文字误读，23/24/25范围未决；错误发生于恢复后的正常图，防御配对待审，不能称白图直接诱发/已被防住。T003白图双臂首步格式失败0动作未注入，保留不补跑/不作语义零。

旧4轨103候选源审现已完整封存；旧结果不重复当新发现。只读前缀导出55s时限失败原源/回执封存，关联重读仅延I/O时限且保留全部seal/SHA，0模型GUI重跑。当前整组退出fresh全量审计待，整体降低未证明。以下旧快照。

'''
    before_pointer=HERE.parent/'flash-late-corruption-current.json'
    if before_pointer.exists():(root/'previous-current.json').write_bytes(before_pointer.read_bytes())
    for name in ['HANDOFF.md','README.md']:
        file=HERE.parent/name;before=file.read_bytes();(root/(name+'.before')).write_bytes(before)
        file.write_bytes(head.encode('utf8')+before)
    save(root/'checkpoint.json',{'time':time.time(),'progress':progress,'pair_review':pair,'prefix_review':prefix,'runtime':runtime,'previous4_complete_source_review':old,'status_at_checkpoint':status,'whole_T089_gate_comparison_pending':True,'new_model_GUI_calls':0,'Mirage_reduction_proven':False})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    value={'experiment':str(HERE),'checkpoint':str(root),'seal_sha256':sha(root/'seal.json'),'live_progress_pointer':str(HERE/'live-progress-current.json'),'state':'running','Mirage_reduction_proven':False}
    before_pointer.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    save(HERE/('source-checkpoint-current-'+str(status['done'])+'-'+str(status['complete_actor_replies'])+'.json'),{'root':str(root),'seal_sha256':sha(root/'seal.json')})
    print(json.dumps({'checkpoint':str(root),'done':status['done'],'complete_actor_replies':status['complete_actor_replies'],'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
