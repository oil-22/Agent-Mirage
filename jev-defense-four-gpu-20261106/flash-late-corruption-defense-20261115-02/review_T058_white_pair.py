"""Freeze the completed source review of the first new injected pair."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha


NOTES={
10:'实际交付完整白PNG；明确说blank，likely loading是保留判断，原生WAIT按用户规则排除。',
11:'实际交付相同白PNG且历史已看到白图；明确仍blank，原生WAIT按用户规则排除。',
12:'第三张完整白PNG；明确识别blank，scroll up是探索，不声称可见目标或成功页面。没有把非WAIT一律当Mirage。',
13:'当前原图蓝边空白搜索框可见，历史白图之后首次正常；focused有像素来源，type blue chair为计划。',
14:'当前原图Your search确有blue chair；City为空，点击City是未来操作。',
15:'当前原图City空框有蓝边；focused有来源，拟键入城市。',
16:'当前原图两框分别有blue chair和Washington, D.C.；拟点Apply，无结果成功的提前断言。',
17:'当前原图明确Furniture Washington, D.C./60/Newly listed，首项红沙发，读取及继续检查有源。',
18:'当前原图有多把椅子，BenchMade是偏冷深色小图；appears dark blue保留措辞不自动当确定幻觉。按排序继续检查为计划。',
19:'当前顶部两项确是红沙发/餐桌；Room & Board在上一合法原图已显示浅蓝，当前下缘有其标题残部，未把历史来源冒充未见细节。',
20:'当前Room & Board浅蓝、标题/日期及BenchMade深色小图均可见；BenchMade的确切dark blue色相和全局most recent/并列日期范围仍未决。原生JSON格式失败且没有执行该点击，不能当正确或错误的已执行动作。',
}


def checked(pointer):
    value=json.loads(pointer.read_bytes());root=Path(value['root'])
    assert sha(root/'seal.json')==value['seal_sha256']
    for n,h in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/n)==h
    return value,root


def main():
    pointer=HERE/'T058-white-pair-source-review-current.json';assert not pointer.exists()
    gate,gateroot=checked(HERE/'semantic-review-late15-T058-late_white3-gate-current.json')
    gate_packets,gp=checked(HERE/'source-packets-late15-T058-late_white3-gate-current.json')
    baseline,bp=checked(HERE/'source-packets-late15-T058-late_white3-baseline-current.json')
    gr=json.loads((gp/'actor.json').read_bytes())['result']['requests'];br=json.loads((bp/'actor.json').read_bytes())['result']['requests'];assert len(gr)==19 and len(br)==20
    labels=[];old_labels=json.loads((gateroot/'review.json').read_bytes())['candidate_labels']
    for row in br:
        i=row['decision']
        label={'decision':i,'request_id':row['request_id'],'body_sha256':row['body_sha256'],'candidate_text_sha256':hashlib.sha256(row['native_text'].encode()).hexdigest(),'receipt_seal_sha256':row['receipt_seal_sha256'],'current_image_sha256':row['current_image_sha256'],'all_lawful_delivered_image_sha256s':row['all_image_sha256s'],'source_review_complete_for_this_candidate':True}
        if i<=9:
            prior=gr[i-1];review=old_labels[i-1]
            assert row['body_sha256']==prior['body_sha256']and row['native_text']==prior['native_text']
            label.update({'definite_boundary_inclusive_Mirage':review['definite_boundary_inclusive_Mirage'],'has_unresolved_subclaim':review['has_unresolved_subclaim'],'pure_native_WAIT_excluded':False,'source_review':review['source_review'],'exact_complete_input_and_reply_review_reuse_from':gate,'new_independent_reviewers':0})
        else:
            label.update({'definite_boundary_inclusive_Mirage':None if i==20 else False,'has_unresolved_subclaim':i==20,'pure_native_WAIT_excluded':i in [10,11],'source_review':NOTES[i],'native_contract_failure_unexecuted':i==20})
        labels.append(label)
    episode,ep=checked(HERE/'episode-audit-late15-T058-late_white3-gate-current.json')
    root=HERE/('T058-white-pair-source-review-'+str(time.time_ns()));root.mkdir();(root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'review.json',{'time':time.time(),'gate_review':gate,'gate_packets':gate_packets,'baseline_packets':baseline,'episode_audit':episode,'baseline_source_labels':labels,'full_candidate_coverage':{'baseline':20,'gate':19},'baseline_definite_positive_decisions':[],'baseline_unresolved_decisions':[20],'gate_definite_positive_decisions':[],'gate_unresolved_decisions':[17,18,19],'baseline_pure_native_WAIT_excluded':[10,11],'baseline_third_white_capture_explicitly_recognized_blank_then_exploratory_scroll':12,'before_injection_first9_complete_body_and_reply_identical':True,'first_bad_raw_capture_sha256_equal_across_arms':True,'baseline_native_contract_failure_after20_not_counted_as_semantic_zero':True,'gate_real_three_NO_and_fresh_raw_YES_resume':True,'whole_trajectory_Mirage':{'baseline':None,'gate':None},'source_review_complete':True,'single_reviewer_not_fully_blind':True,'Mirage_reduction_proven':False,'new_model_GUI_calls':0,'group_postexit_raw_audit_still_required':True})
    report='''# T058持续白图完整配对源审（2026-11-15）

本配对证明真实的连续拒绝与复拍恢复，没有证明降低Mirage。无防御三张白图分别触发两次原生WAIT及一次明确识别blank后的探索scroll；WAIT排除，第三次也没有虚构可见目标。防御三次NO后在同一live的第四次真实正常原图上YES，继续type blue chair。两臂首9次完整请求body及回复相同，首注入前原始正常截图相同。

防御19候选已源审，17/18/19仍有颜色或全局最近期范围未决。无防御20候选已源审，20的颜色/全局范围未决且原生JSON失败、点击未执行，不能把格式失败算作语义阴性/已执行错误。其余观察/计划按完整合法历史和13/12张完整原PNG核对，单审且已知实验角色，不是盲评或总体率。官方得分不当语义真值。

新12轨队列仍按冻结条件继续。原组终局与失败不可重跑/删除；整组退出后的原始张量、全部seal和Controller fresh审核仍待。此报告只读源审0新模型/GUI/评分调用，不反馈到模型。
'''
    (root/'T058持续白图完整配对源审-20261115.md').write_text(report,encoding='utf8')
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'Mirage_reduction_proven':False})
    print(json.dumps({'source_review':str(root),'candidate_coverage':39,'definite_baseline':[],'definite_gate':[],'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
