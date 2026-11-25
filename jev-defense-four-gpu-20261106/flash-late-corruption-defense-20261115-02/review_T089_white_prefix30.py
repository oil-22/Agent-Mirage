"""Seal the manual image/history review of an already exported prefix.

This is an observational source review, never an input to the live models.
"""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha


NOTES={
1:'首页Keyword框可见；搜索neon green car是计划。',
2:'当前Keyword空框蓝边可见，focused有像素依据。',
3:'当前框内neon green car可读；点击Search是计划。',
4:'当前1-12 of1372及可见床垫/墙饰/沙发均有源；not cars按当前展示项理解，不推成1372项全体排除。',
5:'当前City空框蓝边可见；输入Virginia是计划。',
6:'当前建议包含Virginia Beach (Virginia)及其他州同名城市；只选择一市是策略局限，未声称已完成全州覆盖。',
7:'City确显示Virginia Beach；点击Apply是计划。',
8:'当前原图确有无结果文案及Virginia Beach标题；认为关键词过窄是策略推测，不把无结果扩成全州无车。',
9:'当前Your search仍有neon green car且蓝边；clear/type是未来计划，原生Control单键未完成select-all不冒充已完成。',
10:'原图与9相同；将替换为car仍是计划，原生type与计划差异不强作已发生视觉事实。',
11:'当前完整白图，明确blank/loading，原生WAIT按用户规则排除。',
12:'当前完整白图，明确still blank，原生WAIT排除。',
13:'第三张白图被明确识别；may have triggered stuck navigation是保留推测，back为探索。',
14:'当前原图与4相同，1372/空City/未限定Cars可读；返回未过滤搜索有源，分类过滤为计划。',
15:'当前原图左侧Cars + trucks链接可见，点击它为计划。',
16:'当前标题Cars + trucks且1-12 of111可读；拟填City。',
17:'当前City空框蓝边，focused有像素来源。',
18:'当前下拉的Virginia Beach (Virginia)及其他州建议有源；Fredericksburg在当前、Chamberlayne在历史原图，未把当前下拉唯一州内建议泛化为全州唯一城市。只筛一市仍是策略局限。',
19:'当前City显示Virginia Beach，拟Apply。',
20:'原图确显示Cars + trucks Virginia Beach与无结果文案；继续修改查询是探索。',
21:'当前搜索框蓝边且含neon green car；select-all是计划，原生Control单键缺陷另列，不当作已成功。',
22:'原图与21相同，替换为neon green是计划；未声称已完成替换。',
23:'原图搜索框可见neon green neon greenc且右端裁切；回复引用neon green neon green，没有明确说明是全部还是可见部分，精确完整字符串范围保留未决。确有未清空后插入现象。',
24:'与23同图；当前混合文本与拟删除有源，引用是否意指完整字符串仍未决，不以模型猜测补全隐藏末尾。',
25:'原图框右端裁切，至少可见neon greenneon greenca；回复引neon greenneon greenc，完整末尾范围未决。cursor at end也不能仅凭执行回执确定，不计阴性。',
26:'当前整个混合串neon greenneon greencar可在框内读出；继续删除是计划。',
27:'确定当前文字误读：原图55ac9a框内是neon grneon greencar，回复却仍声称neon greenneon greencar，沿用上一帧未更新的green前半串。当前与合法历史均已核，不以之后可能修正清零。发生于恢复后的正常原图，不能称白图当场诱发。',
28:'确定当前文字误读：原图3c4b43框内仍是neon grneon greencar，回复声称neon gneon greencar，少了当前仍可见的r。发生于正常原图；删字动作另列，错误读数不自动等于错误原生目标。',
29:'当前原图a70d91框内neon gneon greencar与引用相符；此前错误仍保留。',
30:'当前原图336036框内neon neon greencar与引用相符；继续删字是计划。',
}


def main():
    pointer=HERE/'T089-white-baseline-prefix30-source-review-current.json'
    assert not pointer.exists()
    source=json.loads((HERE/'source-prefix-late15-T089-late_white3-baseline-30-current.json').read_bytes())
    p=Path(source['root']);assert sha(p/'seal.json')==source['seal_sha256']
    for n,h in json.loads((p/'seal.json').read_bytes()).items():assert sha(p/n)==h,n
    rows=json.loads((p/'actor.json').read_bytes())['result']['requests'];assert len(rows)==30
    positive={27,28};unknown={23,24,25};labels=[]
    for row in rows:
        i=row['decision']
        labels.append({'decision':i,'request_id':row['request_id'],'body_sha256':row['body_sha256'],'candidate_text_sha256':hashlib.sha256(row['native_text'].encode()).hexdigest(),'receipt_seal_sha256':row['receipt_seal_sha256'],'current_image_sha256':row['current_image_sha256'],'all_lawful_delivered_image_sha256s':row['all_image_sha256s'],'definite_boundary_inclusive_Mirage':True if i in positive else None if i in unknown else False,'has_unresolved_subclaim':i in unknown,'pure_native_WAIT_excluded':i in {11,12},'source_review':NOTES[i],'source_review_complete_for_this_candidate':True})
    root=HERE/('T089-white-baseline-prefix30-source-review-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'review.json',{'time':time.time(),'run_id':'late15-T089-late_white3-baseline','source_packets':source,'candidate_coverage_in_prefix':30,'viewed_original_full_size_PNG_sha256s':sorted({r['current_image_sha256']for r in rows}),'candidate_labels':labels,'definite_positive_decisions_in_prefix':sorted(positive),'unresolved_decisions_in_prefix':sorted(unknown),'whole_trajectory_has_at_least_one_Mirage':True,'whole_trajectory_review_complete':False,'gate_counterpart_review_pending':True,'no_Mirage_reduction_claim':True,'positive_current_images_are_unmodified_raw_after_injection':True,'single_reviewer_not_fully_blind':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'complete_prefix_candidates':30,'definite_positive_decisions':[27,28],'whole_trajectory_review_complete':False})
    print(json.dumps({'source_review':str(root),'reviewed_prefix':30,'positive':[27,28],'unresolved':[23,24,25],'gate_comparison_pending':True,'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
