"""Publish mutable progress pointers only from actual immutable inspections."""
import hashlib,json,time
from pathlib import Path
from remote_control import HERE,BASE,ROOT3090,ROOT4090,save,sha

def latest(label):
    candidates=sorted((HERE/'operations').glob('*'+label))
    for p in reversed(candidates):
        receipt=p/'receipt.json';out=p/'stdout.txt'
        if receipt.exists() and out.exists() and json.loads(receipt.read_bytes())['returncode']==0:
            try:return p,json.loads(out.read_text(encoding='utf8'))
            except ValueError:continue
    return None,{}

def main():
    gpu_path,gpu=latest('inspect-service');gui_path,gui=latest('inspect-full-GUI')
    state=gui.get('batch/status.json',{}).get('value',{})
    service=gpu.get('worker/status.json',{}).get('value',{})
    current={'time_unix':time.time(),'scope':'NEW single9B full GUI four-trajectory development pilot',
        'authorization':'2026-11-08 user: 运行完整的gui实验','directory':str(HERE),
        'manifest_sha256':sha(HERE/'runtime-package/manifest.json'),'plan_sha256':sha(HERE/'runtime-package/plan.json'),
        'remote_service':ROOT3090,'remote_GUI':ROOT4090,'service_status':service,'GUI_status':state,
        'service_inspection':None if gpu_path is None else str(gpu_path),
        'GUI_inspection':None if gui_path is None else str(gui_path),
        'Mirage_reduction_established':False,'old_queues_paused':True,'semantic_controls_not_reexecuted':True,
        'known_old_absence_and_readiness_failures_unresolved':True,
        'auxiliary_is_one_Qwen35_9B_original_JEV_S2_base_without_decision_adapter':True}
    target=HERE/'progress-publications'/str(time.time_ns());target.mkdir(parents=True,exist_ok=False)
    save(target/'receipt.json',current)
    head='## 最新：2026-11-08 用户授权的新单9B完整GUI四轨pilot\n\n'
    head+='权威为 `full-gui-current.json`、`full-gui-single-evidence-20261108-01/operations/` 实际只读快照和远端原请求／Controller链。'
    head+='新manifest `'+current['manifest_sha256']+'`；3090仅原4–7卡、原holder九锁，27B 19/24/21层在4–6，唯一9B在7，BF16/SDPA/完整图像历史／原严格validator和全部原预算保持。'
    head+='用户明确要求“运行完整的gui实验”，本批是新条件开发pilot，未证明旧误拦已修复或长历史一定fit，不把之前准入false改称已通过。四轨clean/stale_replace×无/有辅助，单任务非盲开发，不能证明总体降幅。\n\n'
    head+='最新快照GUI phase='+str(state.get('phase'))+'，completed='+str(state.get('completed',0))+'/4；service phase='+str(service.get('phase'))+'，实际调用计数='+str(service.get('actual_model_attempts',0))+'。'
    head+='快照仅定位，须重核actual UID／fullcmd／start_ticks／持锁／requests／SHA链，不读running标志。辅助完整图＋固定通用提示，0任务历史候选，真实actor插入按新Controller运行；未生成或未插入时不能称已生效。\n\n'
    head+='仅只读监督：不得运行health／额外probe或重复service/gui提交，不重启旧终局／旧队列或补花旧cap。技术故障原始输入／图／回复／日志／tensor／seal先保全，原预算内未完技术部分须新linked attempt；语义完成失败不得刷分。0–3外人任务不动。所有总体未完工作保持，不因该pilot暂停总monitor。\n\n'
    handoff=BASE/'HANDOFF.md';old=handoff.read_bytes()
    save(target/'previous-pointers.json',{'HANDOFF_sha256':hashlib.sha256(old).hexdigest()})
    (target/'HANDOFF.before.md').write_bytes(old)
    marker='## 最新：2026-11-08 用户授权的新单9B完整GUI四轨pilot\n\n'
    # Keep all previous handoff versions; prepend the new actual snapshot.
    handoff.write_text(head+old.decode('utf8'),encoding='utf8')
    pointer=BASE/'full-gui-current.json'
    if pointer.exists():(target/'full-gui-current.before.json').write_bytes(pointer.read_bytes())
    pointer.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    save(target/'seal.json',{p.name:sha(p) for p in target.iterdir() if p.is_file()})
    print(json.dumps({'progress_receipt':str(target/'receipt.json'),'GUI_phase':state.get('phase'),'service_phase':service.get('phase'),'model_attempts':service.get('actual_model_attempts',0)}))

if __name__=='__main__':main()
