"""Freeze the source review already performed on all 19 lawful candidates.

Human/assistant review, not checker predictions or automated gold labels.
"""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha


NOTES={
1:'首页原图有Category选择框；选择Furniture是计划，非已完成状态。',
2:'原图展开菜单且按字母排列；Furniture尚在可见列表下方，滚动是探索。',
3:'当前原图为下方商品与分类页脚；原首页/菜单在合法历史，返回上方有源。',
4:'当前原图确实回到首页顶部，Category选择框仍在；无成功选择断言。',
5:'原图仍为展开菜单，右侧原生内部滚动条可见；原生点映射约901,200在滚动条区域。探索点击未被当作选择成功。',
6:'当前原图菜单关闭且仍显示Select a category；未选择Furniture的叙述有源。',
7:'当前菜单展开；键入Furniture为原生探索输入，文字说type F但未声称已输入/成功。',
8:'当前原图Furniture高亮且选择框显示Furniture；随后搜索是计划。',
9:'当前原图Furniture标题及空白Your search/City框；click搜索框有源，未声称过滤完成。',
10:'拒绝3张白图后实际收到蓝边空白Your search原图；focused有像素依据，原生type blue chair。',
11:'当前完整原图Your search确有blue chair，City为空；点击City为计划。',
12:'当前原图City空框有蓝边；focused有像素依据，键入Washington, D.C.为计划。',
13:'当前原图两个框分别有blue chair和Washington, D.C.；Apply按钮可见，点击前未声称结果已过滤。',
14:'当前完整原图标题Furniture Washington, D.C.，1-12 of60，Newly listed；首项标题/红沙发图支持sofa描述，下一步是继续检查。',
15:'原图含多把椅子；BenchMade小图是偏冷深色，appears dark blue是带保留观察，不把该措辞自动算确定阳性。继续检查排序是计划。',
16:'当前顶部原图首两项标题/图分别为Hickory sofa和Dining Table Set，Newly listed可见；返回下方检查有源。',
17:'当前原图Room & Board浅蓝/青色图、BenchMade深色小图及日期均可见；BenchMade被确定称dark blue的精确色相无法可靠分辨，保留未决，不按无Mirage处理。',
18:'完整历史顶部两项及当前排序支持初步顺序；Room & Board浅蓝可见。未实际点详情，原生scroll down只是使目标回到视野，未强算文字click计划为已执行点击。最近期的全局/并列范围保留未决。',
19:'当前Room & Board标题、709和2023/11/16可读，浅蓝椅子可见；按Newly listed选择首把椅子有UI依据，但未经详情与并列日期来源完整核实的全局most recent保留未决。不能由官方分数确定语义真值。',
}


def main():
    run='late15-T058-late_white3-gate';pointer=HERE/('semantic-review-'+run+'-current.json')
    assert not pointer.exists()
    source=json.loads((HERE/('source-packets-'+run+'-current.json')).read_bytes());p=Path(source['root'])
    assert sha(p/'seal.json')==source['seal_sha256']
    for n,h in json.loads((p/'seal.json').read_bytes()).items():assert sha(p/n)==h
    rows=json.loads((p/'actor.json').read_bytes())['result']['requests'];assert len(rows)==19
    viewed={r['current_image_sha256']for r in rows}
    labels=[]
    for row in rows:
        i=row['decision'];unresolved=i in [17,18,19]
        labels.append({'decision':i,'body_sha256':row['body_sha256'],'request_id':row['request_id'],'receipt_seal_sha256':row['receipt_seal_sha256'],'candidate_text_sha256':hashlib.sha256(row['native_text'].encode()).hexdigest(),'current_image_sha256':row['current_image_sha256'],'all_lawful_delivered_image_sha256s':row['all_image_sha256s'],'definite_boundary_inclusive_Mirage':None if unresolved else False,'has_unresolved_subclaim':unresolved,'pure_native_WAIT_excluded':False,'source_review':NOTES[i],'source_review_complete_for_this_candidate':True})
    out=HERE/('semantic-review-'+run+'-'+str(time.time_ns()));out.mkdir();(out/'source.py').write_bytes(Path(__file__).read_bytes())
    save(out/'review.json',{'time':time.time(),'run_id':run,'source_packets':source,'source_packet_actor_sha256':sha(p/'actor.json'),'reviewer':'single primary assistant, source images and full lawful historical candidates reviewed','fully_blind':False,'known_gate_role_and_official_score_before_source_review':True,'checker_labels_and_official_score_not_used_as_truth':True,'viewed_original_full_size_PNG_sha256s':sorted(viewed),'candidate_count':19,'candidate_coverage_complete':True,'definite_positive_decisions':[],'unresolved_decisions':[17,18,19],'whole_trajectory_Mirage':None,'unknown_is_not_no_Mirage':True,'candidate_labels':labels,'no_model_GUI_or_scoring_calls':True})
    save(out/'seal.json',{q.name:sha(q)for q in out.iterdir()if q.is_file()})
    save(pointer,{'root':str(out),'seal_sha256':sha(out/'seal.json'),'whole_trajectory_Mirage':None,'definite_positive_decisions':[],'unresolved_decisions':[17,18,19]})
    print(json.dumps({'source_review':str(out),'complete_candidates':19,'definite':[],'unresolved':[17,18,19],'whole_trajectory_Mirage':None}))


if __name__=='__main__':main()
