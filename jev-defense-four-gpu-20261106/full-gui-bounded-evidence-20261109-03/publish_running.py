import json
import time
from remote_control import HERE,BASE,save,sha

out=HERE/'publication-running-01';out.mkdir(exist_ok=False)
service=HERE/'operations/1794203053229243100-inspect-service/stdout.txt'
gui=HERE/'operations/1794203053233819200-inspect-full-GUI/stdout.txt'
s=json.loads(service.read_text(encoding='utf8'));g=json.loads(gui.read_text(encoding='utf8'))
assert s['worker/status.json']['value']['actual_model_attempts']==3
assert g['control/runner-process.json']['value']['actual']['uid']==1015
value={'stage':'new_matched_GUI_running_at_verified_snapshot','root':str(HERE),'time':time.time(),
 'service_evidence':str(service),'service_evidence_sha256':sha(service),'GUI_evidence':str(gui),'GUI_evidence_sha256':sha(gui),
 'actual_model_attempts_at_snapshot':3,'actor_calls_at_snapshot':1,'judge_calls_at_snapshot':2,'auxiliary_calls_at_snapshot':0,
 'completed_tracks_at_snapshot':0,'expected_tracks':4,'process_and_lock_and_committed_chain_verified':True,
 'inference_worker_UID':1033,'GUI_runner_UID':1015,'source_manifest_sha256':sha(HERE/'runtime-package/manifest.json'),
 'native_same_live_preflight_late_passed_no_retry':True,'goal':'active','efficacy_proven':False,
 'snapshots_are_not_current_process_authority':True}
save(out/'receipt.json',value)
current=BASE/'full-gui-current.json'
(out/'prior-full-gui-current.json').write_bytes(current.read_bytes());current.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
head='''## 最新：2026-11-09 新完整GUI四轨真实运行，主3调用；非效果结论

权威 `full-gui-bounded-evidence-20261109-03/publication-running-01/receipt.json` 与其服务/GUI操作回执。新manifest `584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67`；worker3959659 UID1033/start1182249260与GUI2380246 UID1015/start118691319完整命令、9锁、实际CUDA进程、3真实请求及两条committed链已核。首轨clean/noaux当前1actor+2judge、0aux、0终局；这只是当时快照，后续必须核实际请求/UID/fullcmd/锁/日志，禁止health探测或重复submit。

same-live环境原进程2357272曾在openai pyc磁盘读取D状态导致本地180秒超时，之后原尝试通过并真实退出；`environment-preflight-completion-01`保留原回执/两图/全文件SHA，0重试/0模型/0scorer。新GUI已通过唯一`GUI-submission.json`启动，四轨clean/stale×无/有单辅助，全部原预算。新mask强制text_refs=[]，不是改写回复或真值保证。`assessment-plan-01`固定Mirage一次即计/WAIT排除/误拦/任务完成/技术失败分列；单已知任务不能作总体降幅。旧B01–B06/repair01/旧GUI与所有旧queue均不得重启。目标ACTIVE。

'''
for name in ['HANDOFF.md','README.md']:
 p=BASE/name;(out/(name+'.before')).write_bytes(p.read_bytes());p.write_text(head+p.read_text(encoding='utf8'),encoding='utf8')
print(json.dumps({'new_GUI_running_snapshot_published':True,'actual_model_calls':3,'goal':'active'}))
