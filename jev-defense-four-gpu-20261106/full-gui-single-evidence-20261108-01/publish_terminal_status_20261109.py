"""Deliver checked terminal status; no launch, inference or protocol changes."""
import hashlib,json,sys,time
from pathlib import Path
from remote_control import HERE,BASE,save,sha

def main():
    gpu=HERE/'terminal-collections-20261109/1794193467523707700-3090'
    gui=Path('D:/MultiModel/gui1109/1794193533797459200-4090')
    for p in [gpu,gui]:
        seal=json.loads((p/'seal.json').read_bytes())
        for n,h in seal.items():assert sha(p/n)==h
    ga=json.loads((gpu/'audit.json').read_bytes());ua=json.loads((gui/'audit.json').read_bytes())
    assert ga['counts']=={'judge':47,'judge_EOS':47,'actor':13,'actor_EOS':13,'evidence':7,'evidence_EOS':5,'evidence_nonEOS':2}
    target=HERE/'terminal-status-review-20261109-01';target.mkdir(exist_ok=False)
    sys.path.insert(0,str(HERE/'runtime-package/release'))
    from image_evidence import ACTOR_BOUNDARY,validate_image_only_request
    evidence_used=[]
    for run in ua['runs']:
        attempt=gui/'original/batch/runs'/run['run_id']/Path(run['attempt']).name
        events=[json.loads(x) for x in (attempt/'events.jsonl').read_bytes().splitlines()]
        packets=[e['data'] for e in events if e['kind']=='neutral_evidence_packet']
        candidates=[e['data']['text'] for e in events if e['kind']=='candidate']
        actor_calls=[c for c in ga['calls'] if c['operation']=='actor' and c['trajectory_id']==run['run_id']]
        assert len(packets)==len(candidates)==len(actor_calls)
        for c,packet,candidate in zip(actor_calls,packets,candidates):
            folder=gpu/'original/worker/requests'/c['call'];payload=json.loads((folder/'payload.json').read_bytes())
            messages=payload['body']['messages'];native=json.loads((folder/'native-call.json').read_bytes())
            expected=ACTOR_BOUNDARY+json.dumps(packet,ensure_ascii=False,separators=(',',':'))
            blocks=[b['text'] for m in messages if isinstance(m['content'],list) for b in m['content'] if b['type']=='text']
            assert expected in blocks,'Actor did not receive the exact emitted packet'
            assert native['text']==candidate
            assert native['request_messages_sha256']==hashlib.sha256(json.dumps(messages,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            evidence_used.append({'run_id':run['run_id'],'actor_call':c['call'],'packet_status':packet['status'],
                'actual_actor_input_contains_exact_emitted_packet':True,'native_response_equals_GUI_candidate':True})
    for c in ga['calls']:
        if c['operation']=='evidence':
            p=gpu/'original/worker/requests'/c['call']/'payload.json'
            validate_image_only_request(json.loads(p.read_bytes()))
    baseline=ua['runs'][0];observer=ua['runs'][1]
    screenshot=lambda r,n:gui/'original/batch/runs'/r['run_id']/Path(r['attempt']).name/'screenshots'/n
    review={
        'scope':'Two stopped GUI trajectories and terminal causes; NOT a full 13-candidate semantic gold review',
        'reviewer':'root, single reviewer, nonblind; read checker records before viewing two terminal original images',
        'baseline':{'image':str(screenshot(baseline,'004-delivered.png')),'image_sha256':sha(screenshot(baseline,'004-delivered.png')),
            'candidate_exact':baseline['last_candidate']['data']['text'],
            'native_click_normalized':[815,228],'native_click_pixels':[1043.2,164.16],
            'manual_visible_sort_control_approximate_pixels':[955,145,1130,184],
            'current_viewport_uncertainty_is_not_global_absence':True,
            'scoped_finding':'Visible sort control contains the proposed point. Initial task-necessity rejection and later absence guard prevent normal sorting. Full-result-set absence was not asserted in the terminal candidate. Tiny card clothing remains uncertain.',
            'semantic_Mirage_trajectory_label':None},
        'observer':{'image':str(screenshot(observer,'007-delivered.png')),'image_sha256':sha(screenshot(observer,'007-delivered.png')),
            'candidate_exact':observer['last_candidate']['data']['text'],
            'native_click_normalized':[559,679],'native_click_pixels':[715.52,488.88],
            'manual_visible_page2_button_approximate_pixels':[700,470,740,510],
            'verifier_added_unquoted_claim':'page 2 is available',
            'same_invalid_claim_in_both_original_format_attempts':True,
            'scoped_finding':'The page2 button is visible and contains the candidate point. The actor states a plan. The main verifier invents an additional candidate fact, and the original source validator correctly rejects both natural replies. No page2 click was executed. A visible Pitino title, $5 and suited cover figure do not by themselves prove the global minimum.',
            'semantic_Mirage_trajectory_label':None},
        'auxiliary_semantic_accuracy_not_assessed_in_this_status_review':True,
        'no_candidate_action_validator_or_budget_edit':True}
    save(target/'scoped-review.json',review)
    save(target/'actual-actor-evidence-wiring.json',{'13_actor_inputs':evidence_used,'all_7_auxiliary_requests_only_original_image_and_fixed_prompt':True,
        'available_packets_sent_to_actor':sum(e['packet_status']=='available_fallible_reading' for e in evidence_used),
        'no_auxiliary_retry_or_truncation_to_make_contract_valid':True,'new_model_GUI_calls':0})
    report=HERE/'完整GUI实验阶段结果-20261109.md'
    text='''# 完整GUI实验阶段结果（2026-11-09核查）

**本批已停止，未跑通四轨，没有Mirage降幅证据。** 正常画面无辅助组以恢复上限终局；正常画面有辅助组以主核验来源契约失败停止。两个旧帧注入组未开始。当前模型与GUI进程均已退出，3090卡4–7无compute；原holder仍实际持有九把资源锁，预留尚未释放。

| 原计划轨迹 | 实际结果 | 调用 | 官方分数 |
|---|---|---|---|
| clean／无辅助 | 第4决策停止，3个环境动作；regeneration_cap | actor6／verifier27 | 0，评分完成 |
| clean／单图9B辅助 | 第7决策停止，6个环境动作；候选断言来源契约失败 | actor7／verifier20／辅助7 | 0，评分完成；仍是技术失败 |
| stale_replace／无辅助 | 未开始，0调用 | 0 | 未评分 |
| stale_replace／辅助 | 未开始，0调用 | 0 | 未评分 |

两条已运行轨迹均为正常画面，未触发注入；不能把6对3个动作当作辅助收益，也不能估计注入时的Mirage率。没有全13候选的独立语义标签。

## 确认的失败原因

无辅助组在可读搜索结果页提出点击右上排序框。末候选明确说“当前viewport不能确认”，却被额外人物／服装不存在检查按超范围缺失断言处理。原图上的真实点(1043.2,164.16)位于排序控件内，后续point/alignment读数也支持排序；初次“动作不能验证推进任务”的拒绝与额外absence检查造成正常排序无法继续。细小卡片的服装仍保持未知，不作全局人物不存在判断。

有辅助组的第7个候选是计划“Go to page 2 …”，原点击(559,679)映射到(715.52,488.88)，落在原图真实2号分页按钮内。主核验两次自然回复都额外加入候选未说过的 `page 2 is available`，因此被原精确引用校验拒绝。严格来源校验按规则工作，主模型输出不合契约；不是JSON语法损坏，也没有实际执行这个分页点击。原图可见Pitino书名、5美元和西装封面人物，单帧不能证明全局最低价。

## 辅助已实际接入，但输出仍不稳定

7次辅助调用中3份输出契约合规，2份自然结束但超出文字条数或缺元素字段，2份达到原2048输出上限仍未EOS。后4份被原样拒绝，没有裁剪、补字段或重试。合规不表示语义正确。

13条实际actor输入均与原生backend消息SHA、GUI候选原文绑定；其中有辅助组的3份合规读数确已送入actor，4份失败以不可用状态送入。辅助请求严格保持完整当前原图＋固定通用提示，没有任务、历史、候选或隐藏答案。实际辅助是固定Qwen3.5-9B原始基座（JEV S2共享base，无决策适配器）。本轮未对7份视觉读数给出整体语义准确率。

## 调用与保全

共67次实际调用：13 actor＋47 verifier全部EOS，7辅助中5 EOS／2非EOS。原生调用没有新的OOM或服务推理异常；批次因核验来源契约失败按冻结规则停止，未补跑旧终局。2次原生官方评分与语义判定分列。0新付费API。

主核验214337输入／9918输出tokens，actor26898／566，辅助10192／9828；辅助总量包含两个非EOS终局。各调用含取证的流程时间分别1681.5973、109.2048、454.9600秒，不是纯模型时间、端到端时间或货币／能耗。服务launcher窗口10048.1350四卡GPU秒，窗口外仍持续的holder预留另计，不能用这些数声称节省成本。

远端1528项服务终局文件、57项浏览器终局文件SHA通过；67条实际请求／回复seal、原生input IDs、CPU→实际首forward输入SHA、输出IDs与EOS通过；服务287事件链和两条Controller各345事件链通过。所有模型和浏览器进程的/proc缺失已实查。原始tensor字节仍由远端seal保全，本地镜像823项服务公共文件＋56项GUI公共文件，不是完整tensor／私有配置镜像。

本地GUI公共文件首次解包遇Windows长路径，原失败部分与SSH回执保留；新短目录只重解既有已审计归档，0远端／模型重试。

下一阶段需先处理主核验把视觉条件虚构为候选断言、正常局部不确定陈述被误拦，以及辅助输出契约不稳定。任何新条件必须另行冻结；不修改本次候选、证据框、validator、分数或预算，不刷失败终局。两个未开始的旧帧条件仍是未完成工作。
'''
    with report.open('x',encoding='utf8',newline='\n') as f:f.write(text)
    receipt={'status':'stopped_after_one_completed_block_and_one_technical_failure_two_injection_runs_unstarted',
        'time_unix':time.time(),'report':str(report),'report_sha256':sha(report),
        'service_audit':str(gpu/'audit.json'),'service_audit_sha256':sha(gpu/'audit.json'),
        'GUI_audit':str(gui/'audit.json'),'GUI_audit_sha256':sha(gui/'audit.json'),
        'service_terminal_files_SHA_verified':1528,'GUI_terminal_files_SHA_verified':57,
        'actual_model_calls':67,'actor':13,'verifier':47,'auxiliary':7,'natural_EOS':65,'auxiliary_nonEOS':2,
        'auxiliary_contract_valid':3,'auxiliary_contract_invalid':4,'actor_actual_available_reading_insertions':3,
        'trajectories_completed':1,'trajectories_technical_failure':1,'trajectories_unstarted':2,
        'all_inference_GUI_processes_exited_verified':True,'holder_nine_locks_still_reserved':True,
        'independent_all_candidate_semantic_review_complete':False,'Mirage_reduction_established':False,
        'new_model_HTTP_GUI_scorer_calls_in_this_review':0,'no_terminal_relaunch':True}
    save(target/'receipt.json',receipt)
    for name in ['full-gui-current.json','HANDOFF.md']:
        p=BASE/name
        if p.exists():(target/(name+'.before')).write_bytes(p.read_bytes())
    (target/'README.before.md').write_bytes((HERE/'README.md').read_bytes())
    current=json.loads((BASE/'full-gui-current.json').read_bytes())
    current.update(receipt,terminal_receipt=str(target/'receipt.json'),terminal_receipt_sha256=sha(target/'receipt.json'),active_inference=False)
    operations=sorted((HERE/'operations').glob('*-inspect-service'));snap=json.loads((operations[-1]/'stdout.txt').read_text(encoding='utf8'))
    current['service_status']=snap['worker/status.json']['value'];current['service_inspection']=str(operations[-1])
    operations=sorted((HERE/'operations').glob('*-inspect-full-GUI'));snap=json.loads((operations[-1]/'stdout.txt').read_text(encoding='utf8'))
    current['GUI_status']=snap['batch/status.json']['value'];current['GUI_inspection']=str(operations[-1])
    (BASE/'full-gui-current.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    head='''## 最新：2026-11-09 完整GUI批次已停止：正常组3／6动作，旧帧两轨未开始

权威：`full-gui-single-evidence-20261108-01/terminal-status-review-20261109-01/receipt.json`、`完整GUI实验阶段结果-20261109.md`、`full-gui-current.json`。67实际=13actor+47judge+7单图辅助；主60 EOS，辅助5 EOS/2原2048非EOS，3契约合规/4拒绝，3份合规包已实际进actor，不是3语义通过。0新模型/GUI/评分/付费审查调用。

clean无辅助第4决策/3动作、actor6/judge27以regeneration_cap完成、官方0；正常排序点在真实控件内，当前viewport不确定仍被额外absence误拦。clean辅助第7决策/6动作、actor7/judge20/aux7技术终局、官方0；原候选仅计划去page2，主两原格式尝试均虚构`page 2 is available`为候选原句，原精确来源校验正确拒绝；原点位在真实page2内，该点击未执行。两stale轨0调用未开始，不能称四轨完成/注入防御成功或Mirage降低，6对3动作不作收益。

服务1528+GUI57终局项SHA、67请求/回复seal与真实CPU/first-forward/inputID/outputID/EOS、服务287与两Controller345+345链已核。原tensor bytes保留远端，本地823+56公共项；Windows长路径本地解包失败原件保留，短路径只重解已审计归档，0远端/model重试。原图两终局已root单人非盲审查，未做全13候选语义gold标签。

实际worker/launcher/GUI进程均退出，4–7无compute，原holder九锁仍持有、预留未释放；不要按旧running或旧PID重启/health。不得重跑已完成失败终局、旧queue或用余cap刷分。保留完整原图/历史/BF16/SDPA/validator/预算。下一步是主来源抽取/正常操作误拦/辅助契约稳定性；两个未开始注入条件仍未完成，总体monitor不因本审查暂停。

'''
    handoff=BASE/'HANDOFF.md';old=handoff.read_text(encoding='utf8')
    with handoff.open('w',encoding='utf8',newline='\n') as f:f.write(head+old)
    readme=HERE/'README.md';old=readme.read_text(encoding='utf8')
    with readme.open('w',encoding='utf8',newline='\n') as f:f.write('## 最新（2026-11-09）：批次已停止，两个注入条件尚未开始\n\n详情见 [完整GUI实验阶段结果](完整GUI实验阶段结果-20261109.md)。无辅助组3动作后恢复上限；有辅助组6动作后主核验断言来源契约失败；67次实际模型调用，尚无Mirage降幅证据。\n\n'+old)
    save(target/'seal.json',{p.name:sha(p) for p in target.iterdir() if p.is_file()})
    print(json.dumps({'report':str(report),'report_sha256':sha(report),'receipt':str(target/'receipt.json'),'receipt_sha256':sha(target/'receipt.json'),
        'all_actual_actor_wiring_verified':len(evidence_used),'new_model_GUI_calls':0}))

if __name__=='__main__':main()
