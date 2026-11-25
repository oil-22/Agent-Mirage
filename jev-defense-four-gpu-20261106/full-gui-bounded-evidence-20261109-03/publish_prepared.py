"""Publish only this new stage; keep all prior current pointers recoverable."""
from pathlib import Path
import hashlib
import json
import time
from remote_control import HERE,BASE,save,sha

def main():
    evidence=HERE/'publication-prepared-01';evidence.mkdir(exist_ok=False)
    manifest=HERE/'runtime-package/manifest.json'
    assert sha(manifest)=='584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67'
    old=BASE/'full-gui-current.json'
    if old.exists():(evidence/'previous-full-gui-current.json').write_bytes(old.read_bytes())
    view={'stage':'new_GUI_package_staged_native_preflight_pending','root':str(HERE),
        'manifest_sha256':sha(manifest),'new_GUI_model_calls_verified_at_publication':0,
        'terminal_auxiliary_stage':str(BASE/'bounded-evidence-20261109-02/review-completion-01/receipt.json'),
        'terminal_auxiliary_6_EOS_3valid3rejected_3valid_false_text_relations':True,
        'old_controls_terminal_not_rerun':True,'goal_status':'active','efficacy_proven':False,
        'condition':'Generated text_refs=[]; independent full-image text/elements, same fixed prompt, strict validator unchanged',
        'time_unix':time.time()}
    save(evidence/'receipt.json',view)
    old.write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    head='''## 最新：2026-11-09 新辅助6次结构预检终局；新GUI条件已stage、尚未启动

权威 `bounded-evidence-20261109-02/review-completion-01/receipt.json`：6辅助自然EOS、0retry，3契约valid/3不存在引用拒绝；3valid均有错误text_refs关联，不是3语义通过。177终局SHA/34链/实际IDs-pixels-grid-forward-mask-UTF8与进程退出已核；9072input/2906output/170.799含取证逐调用秒，0actor/judge/GUI/scorer/付费。B01–B06永不重跑，不花余cap。原stage01/旧GUI也保持终局。

新 `full-gui-bounded-evidence-20261109-03` 两端stage manifest `584e701680c4f593b67c0db09ea7673c11ba88803664e7acf07251b7e27a6b67`。不是把负预检改为准入通过。新条件直接令生成text_refs=[]，保留独立文字/元素，丢失关系表达且读图仍可错；原严格validator/主生成/完整历史原图/BF16/SDPA/50步/70actor140judge/原恢复预算保持。私有vendor只补maxItems=0初项边界，4字符级+3新增native-token定向CPU控制通过；旧9CPU不重跑，0模型。准备期复制配置重名失败及maxItems=0首个CPU失败源已封存，未有GUI/model调用。same-live环境preflight正在等待；只用新once-only service/gui命令，原4–7 holder九锁，绝不旧queue或抢0–3。

总体目标ACTIVE，尚无可复核Mirage降幅。新四轨仍是单已知任务clean/stale×无/有辅助开发配对，不能外推总体效果。后续先核actualUID/fullcmd/locks/realrequests/seals，正式效果需独立任务与语义审查，禁止把少执行/技术失败当成功。

'''
    for name in ['HANDOFF.md','README.md']:
        p=BASE/name
        (evidence/(name+'.before')).write_bytes(p.read_bytes())
        p.write_text(head+p.read_text(encoding='utf8'),encoding='utf8')
    print(json.dumps({'new_stage_published':str(evidence),'goal':'active','efficacy':False}))

if __name__=='__main__':main()
