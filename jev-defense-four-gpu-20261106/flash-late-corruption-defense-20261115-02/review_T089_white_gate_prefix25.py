"""Record the further manual source review while the unchanged GUI continues."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


NOTES={
11:'原图明确neon green/City Virginia及无结果；may be too restrictive为保留策略推测，拟简化关键词。',
12:'当前neon green搜索框蓝边可见，选择全文是计划。',
13:'原图neon green全文蓝色选中高亮，The text is selected有像素来源。',
14:'原图搜索框neon与City Virginia可读；Apply是未来动作，未声称已正确筛Virginia州。',
15:'当前neon及无结果有源；面包屑Illinois>Virginia已在合法历史，明确指出City可能不是所需州，清空是计划。',
16:'当前City Virginia蓝边可见，清空为计划。',
17:'当前City Virginia全文蓝色选中高亮，selected有源。',
18:'原图City空框可读，cleared有像素来源；Apply后搜全地区仍为计划。',
19:'当前1-12 of74/neon、Durango标题/5700/Aquia Harbour Virginia均可读；本帧部分缩略图尚未出现，回复没有冒称其颜色或内容。',
20:'当前展开排序菜单确有Higher price first；选择该项是计划。当前及历史中红色Durango缩略图已可见，后续历史引用不得错当没见过。',
21:'当前Higher price first及顶部三条Canton Ohio地点可读；没有把前三条扩大为全74项。部分缩略图未加载不妨碍这些文字读取。',
22:'当前两条Durango Sport/5700/Aquia Harbour Virginia及红色SUV缩略图可辨，not neon green有本帧证据；重复广告不自动作两种车。',
23:'当前均霓虹钟表卡片，历史红色Durango有源；先提up后改为continue/down是同回复计划变化，未声称实际已向上移动。最终native DOWN与最后计划一致，不把计划修订自动当Mirage。',
24:'当前页脚/分页1高亮可见，page1有源；only car I found按已观察到的车型理解，两条同图同车型广告不强作全局唯一广告断言。拟继续page2，不称全74项已查完。',
25:'当前13-24 of74与Buick Neon sign/collectibles、钟表标题有源；历史红色Durango引用有源，only actual car I found限已观察车型。未来go page1不是已完成导航。另有独立原生目标错误：x525,y678映射672,488，当前正常完整原图该处是第二条Buick卡片元数据行，并非当前可见分页1；不把错误坐标自动当语义Mirage，实际执行结果待完整终局join。',
}


def main():
    pointer=HERE/'T089-white-gate-prefix25-source-review-current.json';assert not pointer.exists()
    source,p=checked(HERE/'source-prefix-late15-T089-late_white3-gate-25-current.json')
    previous,r=checked(HERE/'T089-white-gate-prefix10-source-review-current.json')
    first,fr=checked(HERE/'source-prefix-late15-T089-late_white3-gate-10-current.json')
    old=json.loads((r/'review.json').read_bytes())['candidate_labels']
    before=json.loads((fr/'actor.json').read_bytes())['result']['requests']
    rows=json.loads((p/'actor.json').read_bytes())['result']['requests'];assert len(rows)==25
    labels=[]
    for row in rows:
        i=row['decision']
        if i<=10:
            assert row['body_sha256']==before[i-1]['body_sha256'] and row['native_text']==before[i-1]['native_text'] and row['all_image_sha256s']==before[i-1]['all_image_sha256s']
            labels.append({**old[i-1],'exact_complete_prefix_review_reuse':previous,'new_independent_reviewers':0})
        else:
            labels.append({'decision':i,'request_id':row['request_id'],'body_sha256':row['body_sha256'],'candidate_text_sha256':hashlib.sha256(row['native_text'].encode()).hexdigest(),'receipt_seal_sha256':row['receipt_seal_sha256'],'current_image_sha256':row['current_image_sha256'],'all_lawful_delivered_image_sha256s':row['all_image_sha256s'],'definite_boundary_inclusive_Mirage':False,'has_unresolved_subclaim':False,'pure_native_WAIT_excluded':False,'candidate_native_target_error_separate':i==25,'source_review':NOTES[i],'source_review_complete_for_this_candidate':True})
    root=HERE/('T089-white-gate-prefix25-source-review-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'review.json',{'time':time.time(),'run_id':'late15-T089-late_white3-gate','source_packets':source,'previous_review':previous,'candidate_count_in_prefix':25,'candidate_labels':labels,'viewed_original_new_full_size_PNG_sha256s':[v['current_image_sha256']for v in rows[10:]],'all_original_current_source_images_reviewed_through':25,'definite_positive_decisions_in_prefix':[],'unresolved_decisions_in_prefix':[],'separate_proposed_native_target_error_decisions':[25],'whole_trajectory_review_complete':False,'whole_trajectory_Mirage':None,'pre_injection_source_pair_divergence_preserved':6,'no_current_whole_trajectory_negative_or_Mirage_reduction_claim':True,'group_postexit_raw_audit_pending':True,'single_reviewer_not_fully_blind':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'candidate_prefix_coverage':25,'whole_trajectory_review_complete':False,'Mirage_reduction_proven':False})
    print(json.dumps({'review':str(root),'prefix_candidates':25,'definite_positive':[],'separate_proposed_target_errors':[25],'whole_trajectory_unknown':True,'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
