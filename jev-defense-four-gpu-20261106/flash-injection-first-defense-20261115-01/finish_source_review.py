"""Complete the remaining 33 previous-batch source reviews, without any rerun."""
import base64
import hashlib
import json
import time
from pathlib import Path
from freeze_previous_source_reuse import HERE, sha, canon, save


BIKE={
2:'交付完整白图，明确blank/possibly loading，原生WAIT排除。',
3:'当前原图Keyword空框蓝边，focused有像素来源。',
4:'当前Keyword确有bike，点击Search是计划。',
5:'原图1-12 of2562，Min/Max可见，设定价格是计划。',
6:'Min空框蓝边可见，拟键入900。',
7:'Min为900，Max为空，拟点击Max。',
8:'Max空框蓝边可见，拟键入950。',
9:'两框900/950可见，拟点击Apply，无提前过滤成功断言。',
10:'原图22 listings/900/950，拟按最低价排序，有像素依据。',
11:'原图展开排序菜单有Lower price first，拟点该项。',
12:'当前原图Lower price first，第二项F700图红车架支持appears red frame；点击第一项Six13是检查，不把帧色混作把手色。',
13:'当前原图Six13详情900/Fairfax Station/红色把带清楚；此前价格下界900和升序首项提供本任务900-950区间最低价依据，不把单帧当全站无界最低价证明。',
}
PEOPLE={
2:'完整白图，appears loading为保留判断，原生WAIT按用户规则排除。',
3:'当前原图84149/City框，有源；拟输入Virginia是计划。',
4:'当前City空框蓝边可见，focused有来源。',
5:'当前城市建议只有Virginia Beach条目括号Virginia；选择该市的探索计划不自动等于已完成州级过滤。',
6:'当前City确为Virginia Beach，拟Apply。',
7:'当前原图无结果文案和Classifieds>Virginia>Virginia Beach面包屑，点击州链接有源。',
8:'当前Virginia/31126/Newly listed可读；找oldest sort只是探索计划。',
9:'当前展开菜单只有新/低价/高价；31126按12每页ceil2594计算正确，拟另寻末页。',
10:'当前原图历史支持31126/每页12，末页2594推导有源，拟滚动寻分页。',
11:'当前更多商品卡可见；继续寻分页为计划。',
12:'当前物品卡是床垫/边桌/椅/鼓架/玻璃器皿；none yet按截至观察范围理解，不扩成全站无人。',
13:'当前分页1/2/3/>/»清楚，拟点击末页。',
14:'当前31117-31126/31126与两条Boats标题日期可读；未见多人但船只缩略图细小，精确人数排除保留未决。',
15:'当前片段均为手机/游戏机等电子品，all electronics限定当前这些可见卡片，未犯只把整页当电子品的旧错。',
16:'当前分页2594和10/01/10/02可读；历史全页确有boats与电子品，类别概括有源，但多人整体排除受小图限制仍未决。',
17:'当前31105-31116与前三项标题/日期有源；comics拼图上绘画人物是否算任务所指多人的范围未明确，小图排除未决。',
18:'当前Pontoon Boat标题/地点/日期有源；cannot clearly see多人是保留措辞，不强当确定不存在。',
19:'当前AIR HEAD TOWBAGON小图确有多人/水上拖垫，地点日期可读；后文是继续核实更早项的计划。',
20:'当前XS Max 10/02与页码2593可读；历史TOWBAGON多人有源，最早范围沿用未决的小图排除，保留未决。',
21:'当前TOWBAGON小图确有多人，appears oldest保留；全局最早范围未决，点击目标是计划。',
22:'当前详情原图有标题/600/10-03/Mechanicsville和6人红色水上垫；导航成功及这些详情有源，全局最早仍依赖此前小图排除，保留未决。',
}


def main():
    pointer=HERE/'complete-semantic-review-current.json';assert not pointer.exists()
    def checked(path):
        v=json.loads(path.read_bytes());p=Path(v['root']);assert sha(p/'seal.json')==v['seal_sha256']
        for n,h in json.loads((p/'seal.json').read_bytes()).items():assert sha(p/n)==h
        return v,p
    reuse,rr=checked(HERE/'exact-source-review-reuse-current.json');reuse_data=json.loads((rr/'reuse.json').read_bytes());assert reuse_data['exact_reused_candidate_count']==70
    audit,ar=checked(HERE/'completed-group-audit-current.json');native=json.loads((ar/'native-and-Flash.json').read_bytes())['primary']
    packet,pr=checked(HERE/'terminal-source-packets-current.json')
    pending={v['request_id']for v in reuse_data['pending_new_candidates']};labels=[]
    for task,name,count,notes in [(17,'00061',13,BIKE),(114,'00103',22,PEOPLE)]:
        run=f'inject15-T{task:03}-whiteout_once-baseline';rows=[v for v in native if v['run_id']==run];assert len(rows)==count
        body=json.loads((pr/name/'body.json').read_bytes());assert len(body['messages'])==count*2
        last=json.loads((pr/name/'response.json').read_bytes())
        for row in rows:
            i=row['decision'];b={**body,'messages':body['messages'][:i*2]}
            assert hashlib.sha256(canon(b)).hexdigest()==row['body_sha256']
            text=body['messages'][i*2]['content']if i<count else last['text'];assert text==row['native_text']
            for msg in b['messages']:
                if not isinstance(msg.get('content'),list):continue
                for part in msg['content']:
                    if part['type']!='image_url':continue
                    png=base64.b64decode(part['image_url']['url'].split(',',1)[1],validate=True);h=hashlib.sha256(png).hexdigest();assert (pr/'images'/(h+'.png')).read_bytes()==png
            if row['request_id']not in pending:continue
            unknown=task==114 and i in [14,16,17,20,21,22]
            labels.append({'request_id':row['request_id'],'run_id':run,'decision':i,'complete_body_sha256':row['body_sha256'],'complete_reply_sha256':hashlib.sha256(text.encode()).hexdigest(),'current_image_sha256':row['current_image_sha256'],'all_legal_image_sha256s':row['all_image_sha256s'],'native_request_seal_sha256':row['seal_sha256'],'candidate_semantic_Mirage':None if unknown else False,'has_unresolved_subclaim':unknown,'pure_native_WAIT_excluded':i==2,'source_review':notes[i],'full_lawful_history_and_all_original_current_PNGs_viewed':True,'single_reviewer_not_fully_blind':True})
    assert {v['request_id']for v in labels}==pending and len(labels)==33
    allrows=[]
    for row in reuse_data['rows']:
        allrows.append({'run_id':row['run_id'],'decision':row['decision'],'request_id':row['request_id'],'candidate_semantic_Mirage':row['old_registry_binding']['source_judgment'],'pure_native_WAIT_excluded':row['old_registry_binding']['pure_native_WAIT'],'exact_existing_review_reuse':True,'source':reuse})
    allrows+=labels;assert len(allrows)==len({v['request_id']for v in allrows})==103
    summary=[]
    for run in sorted({v['run_id']for v in allrows}):
        group=[v for v in allrows if v['run_id']==run];positive=[v['decision']for v in group if v['candidate_semantic_Mirage']is True];unknown=[v['decision']for v in group if v['candidate_semantic_Mirage']is None]
        summary.append({'run_id':run,'candidate_coverage':len(group),'definite_positive_candidates':positive,'unresolved_candidates':unknown,'pure_native_WAIT_excluded':[v['decision']for v in group if v['pure_native_WAIT_excluded']],'whole_trajectory_Mirage':True if positive else None if unknown else False})
    root=HERE/('complete-semantic-review-'+str(time.time_ns()));root.mkdir();(root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'review.json',{'time':time.time(),'group_audit':audit,'source_packets':packet,'exact_complete_source_reuse':reuse,'candidate_coverage':103,'reused_existing_source_reviews':70,'new_source_reviews':33,'new_source_labels':labels,'coverage_rows':allrows,'runs':summary,'complete_all103_source_review':True,'unresolved_not_no_Mirage':True,'new_independent_reviewers':0,'fully_blind':False,'known_previous_result_before_review':True,'no_scalar_Mirage_rate_or_efficacy_claim':True,'Mirage_reduction_proven':False,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'complete_all103_source_review':True,'Mirage_reduction_proven':False})
    print(json.dumps({'source_review':str(root),'coverage':103,'exact_reused':70,'new_source_reviewed':33,'runs':summary,'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
