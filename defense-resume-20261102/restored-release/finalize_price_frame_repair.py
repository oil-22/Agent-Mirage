"""Seal the independently reviewed single-frame diagnostic, including any failures."""
import argparse,hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-frame-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

def main(notes_path):
    assert not(P/'completed-current.json').exists()
    notes=read(notes_path);assert notes['actual_frozen_readings_reviewed'] is True and notes['independent_original_images_reviewed']is True
    i=read(P/'inspection-current.json');assert i['terminal']and i['status']['phase']=='completed'
    ap=read(P/'service-audit-current.json');root=Path(i['collected_root']);audit=read(Path(ap['directory'])/'audit.json')
    assert sha((Path(ap['directory'])/'audit.json').read_bytes())==ap['audit_sha256']
    s=read(root/'summary.json');cases={r['id']:r for r in s['results']};assert len(cases)==5
    frozen={};bindings={};reuse=[]
    for case in s['results']:
        f=root/'journal'/case['id']/'events.jsonl'
        if not f.exists():assert case['mode']=='routing'and not case['calls'];continue
        for e in[json.loads(x)for x in f.read_text(encoding='utf-8').splitlines()]:
            if e['kind']=='price_history_single_frame_frozen':
                d=e['data'];value={k:v for k,v in d.items()if k!='frozen_sha256'};assert sha(canon(value))==d['frozen_sha256']
                im=d['original_source_frame'];assert sha((root/'images'/(im['sha256']+'.png')).read_bytes())==im['sha256']
                assert d['frozen_sha256']not in frozen;frozen[d['frozen_sha256']]={'case':case['id'],'event':e['seq'],**d}
            if e['kind']=='price_history_single_frame_reuse':
                assert e['data']['frozen_sha256']in frozen
                assert frozen[e['data']['frozen_sha256']]['original_source_frame']['sha256']==e['data']['image_sha256'];reuse.append({'case':case['id'],**e['data']})
            if e['kind']=='price_history_binding':bindings[case['id']]=e['data']
    result=lambda k:cases[k].get('result',{})
    relation=lambda k:bindings.get(k,{}).get('relation',{}).get('action',{}).get('status')
    eligibility={
      'wrong_pair_Controller_blocked':result('g01').get('status')=='blocked',
      'wrong_pair_relation_contradicted':relation('g01')=='contradicted',
      'correct_pair_Controller_accepted':result('g02').get('status')=='accepted',
      'correct_pair_relation_supported':relation('g02')=='supported',
      'grouped_correct_price_uncertain_clothing_supported':result('g03').get('agrees')is True and relation('g03')=='supported',
      'missing_source_retains_insufficient':result('g04').get('agrees')is False and relation('g04')in {'insufficient','uncertain'},
      'authored_WAIT_route_excluded':result('g05').get('pure_native_WAIT')is True and result('g05').get('price_history_eligible')is False and len(cases['g05']['calls'])==0,
      'manual_frozen_price_facts_match_source':notes['frozen_price_facts_match_source']is True,
    }
    eligible=all(eligibility.values())
    review={'manual_notes':notes,'eligibility_checks':eligibility,'fullgui_candidate_eligible':eligible,'rows':[{k:v for k,v in r.items()if k!='calls'}for r in s['results']],
       'frozen_original_frame_readings':list(frozen.values()),'cached_past_data_reuse':reuse,'independent_price_relations':bindings,
       'scope':'Five authored/selected known-task controls, four model-using cases plus zero-call WAIT routing. No natural actor or GUI trajectory. Two selected past native frames, actual current frame and original full legal text; not full-GUI completion validation, global minimum evidence or general efficacy.',
       'formal_release':False,'native_actor_calls':0,'GUI_actions':0,'official_scores':0,'paid_API_calls':0}
    out=P/('independent-review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    row={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'worker_exited':True,'source_review_complete':True,'calls':ap['calls'],'terminal_directory':str(root),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'fullgui_candidate_eligible':eligible,'formal_release':False,'monitor':'ACTIVE'}
    (P/'completed-current.json').write_text(json.dumps(row,indent=2))
    report=f'''# 逐帧价格历史绑定真实预检与发布边界

5个选择性人工源绑定控制全部处理，{ap['calls']}次judge自然EOS、0actor模型/GUI/官方评分/付费API。四个模型控制与一个0调用人工WAIT路由，不能称5个自然语义通过或独立效力样本。新完整GUI候选资格：{eligible}；正式发布仍false。

逐项资格和人工原图审查见review.json。错绑必须在Controller被拒且冻结关系明确contradicted；正确价格必须在Controller被接受；正确合并价格不因未决服饰误拦；缺源保留insufficient/uncertain；纯WAIT只路由排除。未通过项不能隐藏为成功。

独立原图事实按帧读取、冻结；已读同一原始SHA作为过去数据复用，非新推理/当前GUI确认。关系检查只核对候选原样历史价格句，不证明服饰、全局最低价或动作结果。语义审查为单审查者、已知同任务、完整法律反馈文本，非完全盲法。错误读者仍可能绕过或误拦，额外调用耗原140judge预算。

实际service wire/inputIDs/generation/outputIDs/EOS/reply/原图及全部存在事件链已核实：{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒；非墙钟/货币/能耗。terminal {i['terminal_manifest_sha256']}；audit {ap['audit_sha256']}。绝不重复本终局控制或用剩余20cap重试。monitor ACTIVE。
'''
    (BASE/'逐帧价格历史绑定预检与发布边界-20261029.md').write_text(report,encoding='utf-8');print(json.dumps(row))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review-notes',type=Path,required=True);main(p.parse_args().review_notes)
