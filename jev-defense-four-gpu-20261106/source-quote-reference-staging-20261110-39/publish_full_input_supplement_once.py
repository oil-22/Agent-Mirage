"""Publish complete input identity evidence without altering the sealed proposal."""
import copy
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'remaining29-full-history-gui-20261110-37'))
from orchestrate import save,sha
from join_source_reviews import verify_seal


def main():
    assert not(HERE/'full-input-supplement-published.json').exists()
    pointer=json.loads((HERE/'full-input-CPU-completed.json').read_bytes())
    cpu=Path(pointer['root']);assert verify_seal(cpu)==pointer['seal_sha256']
    assert sha(cpu/'receipt.json')==pointer['receipt_sha256']
    receipt=json.loads((cpu/'receipt.json').read_bytes())
    assert receipt['passed']and receipt['original_complete_forward_input_reproduced']
    assert receipt['complete_image_count']==13 and receipt['public_history_message_count']==29
    assert(receipt['original_complete_input_tokens'],receipt['proposed_complete_input_tokens'],receipt['input_token_delta'])==(29871,30707,836)
    assert receipt['identical_actual_pixel_values_and_image_grids']and receipt['identical_ordered_image_token_IDs']
    published=json.loads((HERE/'proposal-published.json').read_bytes());proposal=Path(published['root'])
    assert verify_seal(proposal)==published['seal_sha256']
    out=HERE/('full-input-supplement-'+str(time.time_ns()));out.mkdir()
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out/'CPU-receipt.json').write_bytes((cpu/'receipt.json').read_bytes())
    report=f'''# 完整输入绑定补充：未启动新GUI

封存的提案保持不变：[{proposal.name}/proposal.md]({proposal.as_posix()}/proposal.md)。补充CPU回执`CPU-receipt.json`已核SHA，并关联原生forward请求0074的原始prepared元数据。

原生AutoProcessor重新构造了完整29条公开主历史与13张实际原图；旧输入29871个IDs与实际请求逐个相等，全部prepared字段的shape/dtype/bytes/SHA与原实际forward准备记录一致。新方案的用户数据、候选、全部原图块保持逐字节一致，只在system追加完整来源表。

新完整输入30707tokens，增加836。pixel_values、image_grid_thw及按原顺序的图像token IDs逐项相等；没有删消息、裁图、降精度或改2048/4096输出上限。这仅证明该封存样例的CPU输入身份，不证明GPU能容纳全部未来历史、不是真实模型语义/WAIT通过，也没有新模型或GUI调用。

新quote_id wire条件已通过异步问题请求人类选择，尚无答复。此前STOP来源映射批准仍有效，不能自动批准新的wire条件。剩余28条模板继续拒绝执行；四个已有终局和437个旧请求排除保持。目标ACTIVE，防御降幅仍未证实。
'''
    (out/'supplement.md').write_text(report,encoding='utf8')
    save(out/'receipt.json',dict(time=time.time(),original_proposal=published,complete_input_CPU_authority=pointer,
        exact_full_history_messages=29,complete_original_images=13,original_input_tokens=29871,proposed_input_tokens=30707,
        added_tokens=836,original_prepared_and_actual_forward_identity_reproduced=True,
        human_source_reference_condition_question_submitted=True,human_answer_received=False,
        no_actual_condition_deployment=True,no_new_model_GPU_GUI_scorer_paid_calls=0,goal='active',efficacy_established=False))
    paths=[HERE.parent/n for n in['README.md','HANDOFF.md','full-gui-current.json']]
    before={p:p.read_bytes()for p in paths}
    status=json.loads(before[paths[2]])
    status=copy.deepcopy(status)
    status.update(time=time.time(),source_reference_complete_input_CPU=dict(authority=pointer,full_main_messages=29,
        original_images=13,old_input_tokens=29871,new_input_tokens=30707,delta=836,
        all_pixels_grids_and_ordered_image_IDs_identical=True,GPU_fit_or_future_context_not_proven=True),
        human_source_reference_question_submitted=True,human_source_reference_answer_received=False,
        actual_GUI_models_currently_stopped=True,source_reference_condition_decision_received=False,
        immutable_publication=str(out),goal='active',new_model_GPU_GUI_scorer_paid_calls=0)
    save(out/'status.json',status)
    head=f'''## 最新：2026-11-10 完整29消息/13原图的来源表输入已实核；新GUI仍待条件决定

补充权威`{out.relative_to(HERE.parent).as_posix()}/receipt.json`与`/supplement.md`。原生CPU处理器重建原0074完整输入，29871IDs逐个相同，全部prepared字段shape/dtype/bytes/SHA与实际forward准备记录相同。新system仅追加来源表后30707tokens，增加836；原29消息、13完整原图、候选/user数据、pixel_values/image_grid_thw和原顺序图像tokenIDs保持。没有权重加载/CUDA/模型/GUI/评分，不是GPU容量或未来全历史、语义/防御成功证明。

新quote_id来源表示的具体条件决定已询问，尚无答复；此前已批准STOP原句映射不复问也不当新wire许可。原封存提案、18本地/23原生CPU控制和全部失败保留；四个终局/437旧请求排除、原32轨/16对/8任务及剩余28条范围保持。服务/GUI已退出，模板拒绝执行，目标ACTIVE且相对降幅仍null。以下为保留历史。

'''
    for p,raw in before.items():
        (out/('before-'+p.name)).write_bytes(raw)
        (out/('after-'+p.name)).write_bytes((out/'status.json').read_bytes()if p==paths[2]else head.encode('utf8')+raw)
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    for p,raw in before.items():assert p.read_bytes()==raw
    for p in paths:p.write_bytes((out/('after-'+p.name)).read_bytes())
    result=dict(root=str(out),receipt_sha256=sha(out/'receipt.json'),seal_sha256=sha(out/'seal.json'))
    save(HERE/'full-input-supplement-published.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
