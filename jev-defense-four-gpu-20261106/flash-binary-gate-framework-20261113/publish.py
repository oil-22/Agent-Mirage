"""Publish the verified new framework without resuming the old GUI goal."""
import json,subprocess,sys,time
from pathlib import Path
from manage import HERE,save,sha

def main():
    snapshots=sorted(HERE.glob('evidence-*'));evidence=snapshots[-1]
    audits=sorted(evidence.glob('audits/*/audit.json'));audit=json.loads(audits[-1].read_bytes())
    terminal=json.loads((evidence/'integration-preflight/terminal.json').read_bytes())
    assert audit['status']==terminal['status']=='passed'and audit['new_Flash_calls_verified']==4
    for row in audit['requests']:
        request=evidence/'service/requests'/row['request_id']
        assert sha(request/'seal.json')==row['seal_sha256']
        assert all(sha(request/name)==h for name,h in json.loads((request/'seal.json').read_bytes()).items())
    assert all(sha(evidence/'integration-preflight'/name)==h for name,h in json.loads((evidence/'integration-preflight/seal.json').read_bytes()).items())
    assert all(sha(audits[-1].parent/name)==h for name,h in json.loads((audits[-1].parent/'seal.json').read_bytes()).items())
    for name,h in json.loads((evidence/'package-manifest.json').read_bytes()).items():assert sha(HERE/name)==h==sha(evidence/name)
    publication=HERE/('publication-'+str(time.time_ns()));publication.mkdir()
    # The final combined suite binds all tested controller/client sources to
    # the delivered bytes; it never loads weights or calls the running service.
    p=subprocess.run([sys.executable,'-B','-m','unittest','test_gate','test_controller','-v'],cwd=HERE,text=True,encoding='utf8',capture_output=True)
    (publication/'cpu-tests.stdout.txt').write_text(p.stdout,encoding='utf8');(publication/'cpu-tests.stderr.txt').write_text(p.stderr,encoding='utf8')
    assert p.returncode==0 and 'Ran 20 tests'in p.stderr
    save(publication/'cpu-tests.json',{'returncode':p.returncode,'tests_passed':20,'model_calls':0,'tested_sources':{name:sha(HERE/name)for name in ['gate_core.py','gate_client.py','wire_contract.py','run_controller.py','test_gate.py','test_controller.py']}})
    rows=audit['requests'];peak=max(r['peak_allocated_bytes']for r in rows);input_tokens=sum(r['input_tokens']for r in rows);modelseconds=sum(r['elapsed_seconds_with_capture']for r in rows)
    journal=json.loads((evidence/'integration-preflight/forward-fixture/events.jsonl').read_text().splitlines()[0])
    first_events=[json.loads(line)for line in(evidence/'integration-preflight/forward-fixture/events.jsonl').read_text().splitlines()]
    terminal_events=[json.loads(line)for line in(evidence/'integration-preflight/cancellation-fixture/events.jsonl').read_text().splitlines()]
    total_duration=terminal_events[-1]['time']-first_events[0]['time']
    result={'status':'deployed_ready','created':time.time(),'local_date':'2026-11-13','model':'perplexity-ai/pplx-decider-flash-v1.2','revision':audit['revision'],'contract_sha256':audit['contract_sha256'],'service':{'host':'3090','physical_gpu':7,'url':'http://127.0.0.1:18341','actual_identity_at_audit':audit['service_actual_identity'],'held_inherited_locks':9,'actual_health_at_audit':audit['health']},'policy':{'input':'one original current PNG and one fixed generic question','main_context_supplied_to_Flash':False,'auxiliary_context_accumulates':False,'NO':'continuous same-live recapture until YES or manual stop','recapture_limit':None,'auxiliary_call_cap':None,'manual_stop_checked_after_inflight_call':True,'technical_failure':'preserve and stop, not semantic NO or automatic retry'},'verification':{'CPU_tests':20,'new_Flash_calls':4,'observed':terminal['observed'],'old_completed_model_controls_repeated':0,'actual_forward_tensors_and_raw_scores_audited':4,'HTTP_negative_controls':2,'service_journal':audit['journal'],'fixtures_dispatched':1,'actual_environment_actions':0,'main_model_calls':0,'GUI_trajectories':0,'paid_API_calls':0,'input_tokens':input_tokens,'autoregressive_output_tokens':0,'peak_allocated_bytes':peak,'summed_native_seconds_including_input_capture':modelseconds,'four_call_fixture_elapsed_seconds_including_ownership_HTTP_and_cancellation':total_duration},'GUI_adapter_status':'callback entrypoint and full-main-history binding tested with fixtures; no live GUI/native main-model trajectory started','mirage_reduction':None,'formal_defense_effective':False,'old_GUI_goal':'user_paused_not_resumed','evidence_snapshot':str(evidence),'CPU_receipt':str(publication/'cpu-tests.json'),'audit_receipt':str(audits[-1])}
    save(publication/'deployment.json',result)
    text=f'''# Flash 单图门控框架部署与接线验证（2026-11-13）

已按用户选择部署 Flash 单模型，并完成新的 YES/NO 门控 Controller。3090 物理 GPU 7 上实际服务 UID {audit['service_actual_identity']['uid']}、PID {audit['service_actual_identity']['pid']}；完整命令、start ticks、GPU UUID 与继承的九把实际持锁记录已核。模型原生 decision adapter 实际加载，BF16/SDPA 与发布者原生非因果 reference 路径保留，无量化/CPU 替代或其他辅助模型。检查进程时须重新核对，PID 与 ready 文件均不能替代现场证据。

每次请求只有一张当前完整 PNG 和固定通用问题。任务、主模型完整历史、候选动作、上一次图像/判定不进入 Flash；每次只做一次无 past KV、use_cache=false 的原生前向。权重保持常驻，不宣称物理显存逐次清零。服务严格拒绝额外 prompt/history 字段、重复 request_id；重复相同图像也做独立调用，不复用概率。概率只留审计，不进入主提示。

用户明确采用“持续复拍，直到 YES 或手动停止”。因此新模式没有旧 2 次复拍和 60 次辅助调用上限，每次 NO 等待 0.5 秒后从同一环境重新截图；不做返回、点击、滚动或环境重置。主模型保留自己的完整历史、原生成参数与原生解析/执行，主决策 50 步/70 actor 与持续辅助循环分开。手动停止在辅助和主调用返回后再次检查，阻止后续转交/派发；已派发的环境动作不能撤回。缺失图片先重拍，网络/模型/资源问题则封存技术失败并停止，不当作 NO 或隐式重试。

YES 的标准是“当前可见界面连贯并足够可观察”，而非任务成功或动作正确。正常页脚、无结果、稀疏页面、可读对话框与深色界面可以通过；空白、替代主界面的明确加载图、严重损坏/模糊/遮挡而不可理解的画面返回 NO。该标准不凭任务目标是否在屏幕中来拦截。固定原问题与选项见 gate-contract.json，SHA `{audit['contract_sha256']}`。

20 项 CPU 流程/边界测试通过，涵盖超过两次复拍、同图新调用、完整主历史/参数保留、精确图像字节绑定、无效响应/解析不执行、手动停止和技术失败。另用两张与旧 18 图均不同 SHA 的新合成图做 4 次真实 Flash 调用，预输出计划已封存：实际序列 **NO → NO → YES → NO**。前两次原图同字节、不同 capture/request ID，无缓存；只有第三张通过图交给主模型接口 fixture，原生动作 fixture 原样派发一次、无真实环境动作。第四次在请求途中设置停止，返回后未转交主模型或执行。没有再次运行旧54比较控制。

四份实际完整 wire body/PNG、input IDs/pixels/grid、全原生 head 分数与发布者 temperature→概率绑定、模型/source identity、前后资源准入及 request/reply seals 已逐一核对；实际 service journal {audit['journal']['events']} 事件，头 `{audit['journal']['head']}`，两个 Controller journal 也已核。CPU 审计再发 2 个非法/重复 HTTP 请求，分别400/409，实际模型调用数保持4。原始张量在新证据快照中保留，token 不导出。

4 次合计 {input_tokens} input tokens，0 自回归 output tokens（原生二元读出，不是生成 EOS）。峰值 allocated {peak} bytes，约 {peak/1024**3:.2f} GiB；原生调用与输入捕获累计 {modelseconds:.4f} 秒。四调用 fixture 全流程约 {total_duration:.2f} 秒，包含资源检查、HTTP、取证与停止检查；不能把前面的模型计时当作端到端延迟或花费。加载时原生 PyTorch reference kernels 的缺少优化依赖提示保留，没有临时改变安装或内核条件。

本次完整 GUI 轨迹、主27B、真实 actor、官方评分与付费 API 均为0。当前已经完成的是常驻 Flash 服务、可运行 Controller 入口及原生回调接线测试；现有 GUI 适配器需要通过 run_controller.py 明确提供其原生 capture/actor/parser/executor。没有恢复旧 GUI、注意力或 UI-TARS 队列，也没有把旧目标改为完成或恢复。完整图限制为PNG且不超过4,194,304像素，超限停止而非裁剪；native processor 自身的原尺寸处理保持。

**结论：框架已经按指定流程部署并完成真实接线预检；尚未证明降低 Mirage 触发率。** 单图无法可靠区分清晰旧帧与新帧，也不能验证下一步动作、主模型历史断言或任务完成。下一阶段的有效性证据应来自独立匹配的完整 GUI 轨迹，分别审查首次错误发生、放行/执行、正常操作误拦、完成情况、复拍次数/长期停滞与成本，不能由这4次流程控制推断降幅。

证据快照：`{evidence}`。独立审计：`{audits[-1]}`。启动/停止、精确标准与原生适配器接口见 README.md。
'''
    report=HERE/'Flash单图门控框架部署与接线验证-20261113.md';report.write_text(text,encoding='utf8')
    save(HERE/'deployment-current.json',{'publication':str(publication),'deployment':str(publication/'deployment.json'),'deployment_sha256':sha(publication/'deployment.json'),'report':str(report),'report_sha256':sha(report),'status':'deployed_ready','mirage_reduction':None})
    head=f'''## 最新：2026-11-13 Flash 单图 YES/NO 门控部署；持续复拍获用户明确采用，旧 GUI 目标仍暂停

权威 `flash-binary-gate-framework-20261113/deployment-current.json` 及 `Flash单图门控框架部署与接线验证-20261113.md`。用户选择 Flash，并明确“持续复拍，直到 YES 或手动停止”；此为新的单图门控条件，移除旧2复拍/60辅助上限，不复问。固定 Flash revision `{audit['revision']}`，3090 GPU7 loopback18341 已真实加载，UID1033/PID{audit['service_actual_identity']['pid']}仅定位，操作前重核完整命令/start/UUID/九继承锁和实际请求。每次完整当前图+固定通用问题；没有任务、主历史、候选、前图或累积KV，原生 use_cache=false。YES转交同一PNG，NO仅持续同环境复拍；技术故障封存并停，不伪装NO/自动重试。手动停止返回后再检查，不再转交或派发。原主完整历史/参数/原生parser/executor入口保留，本模式无旧上下文语义judge。

20 CPU测试与4新真实 Flash调用完成：NO/NO/YES/NO，只有YES图进入原生主接口fixture，取消路径0转交/执行。4实际wire/input IDs/pixels/grid/原始head概率/ownership/request-reply seals与9 service事件链、两个Controller链通过；2非法/重复HTTP均无新增推理。0主27B/实际GUI/环境动作/scorer/付费API；0旧54控制重跑。合成接口控制不等于降低Mirage，mirage_reduction仍null。单图不证明清晰旧帧新鲜性/动作正确。服务常驻待接入，没有持续GUI worker；不要重复stage/submit/preflight，不恢复任何旧终局/队列。旧完整GUI目标仍用户暂停，未伪造完成或恢复；本目录新结果覆盖“尚未下载/部署Flash”的历史。以下旧头保留。

'''
    for name in ['HANDOFF.md','README.md']:
        target=HERE.parent/name;old=target.read_bytes();(publication/('old-'+name)).write_bytes(old)
        target.write_bytes(head.encode('utf8')+old)
    save(publication/'publication-seal.json',{'deployment.json':sha(publication/'deployment.json'),'cpu-tests.json':sha(publication/'cpu-tests.json'),'cpu-tests.stdout.txt':sha(publication/'cpu-tests.stdout.txt'),'cpu-tests.stderr.txt':sha(publication/'cpu-tests.stderr.txt'),'old-HANDOFF.md':sha(publication/'old-HANDOFF.md'),'old-README.md':sha(publication/'old-README.md'),'report':sha(report),'README':sha(HERE/'README.md'),'handoff_after':sha(HERE.parent/'HANDOFF.md'),'parent_readme_after':sha(HERE.parent/'README.md')})
    print(json.dumps({'publication':str(publication),'report':str(report),'status':result['status'],'actual_Flash_calls':4,'CPU_tests':20,'GUI':0,'Mirage_reduction':None}))
if __name__=='__main__':main()
