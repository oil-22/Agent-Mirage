"""Publish this fresh, actually launched campaign and preserve prior heads."""
import json
import time
from pathlib import Path
from remote_util import HERE,save,sha

def main():
 assert not(HERE/'running-publication-current.json').exists()
 prep=json.loads((HERE/'preparation-current.json').read_bytes())
 assert(HERE/'GUI-submission.json').exists()
 runtime=sorted(HERE.glob('runtime-evidence-*'))[-1]
 assert all(len(v['held_inherited_locks'])==17 for v in json.loads((runtime/'result.json').read_bytes())['result']['ownership'].values())
 assert(HERE/'site-lock-running-current.json').exists()
 root=HERE/('running-publication-'+str(time.time_ns()));root.mkdir();before=root/'before';before.mkdir()
 heads=[HERE/'README.md',HERE/'HANDOFF.md',HERE.parent/'README.md',HERE.parent/'HANDOFF.md',HERE.parent/'active-defense-goal-current.json']
 for i,p in enumerate(heads):
  if p.exists():(before/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
 value={'state':'new_scale10_GUI_running','active_study':str(HERE),'goal_active':True,'goal_tool_status_is_authoritative':True,
  'manifest_sha256':prep['manifest_sha256'],'prior_verified_successes_per_mode':2,'cumulative_target_per_mode':10,
  'initial_new_trajectories':40,'task_ids':[0,3,17,58,89,94,112,131],
  'watcher_exec_session':1198,'actual_owned_runtime':{'root':str(runtime),'seal_sha256':sha(runtime/'seal.json')},
  'GUI_submission_sha256':sha(HERE/'GUI-submission.json'),'no_old_queues_restarted':True,
  'new_successes_require_terminal_raw_audit_and_image_review':True,'source_NO_not_Flash_detection':True}
 save(root/'publication.json',value)
 (root/'source.py').write_bytes(Path(__file__).read_bytes())
 save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
 binding={'root':str(root),'seal_sha256':sha(root/'seal.json'),**value}
 save(HERE/'running-publication-current.json',binding)
 temp=HERE.parent/('.active-scale10-'+str(time.time_ns()));save(temp,binding);temp.replace(HERE.parent/'active-defense-goal-current.json')
 header='''## 2026-11-16 新目标：四种注入各累计10条，新增40条完整GUI已启动

最新用户明确要求“现在我要把拦截成功的轨迹数目增加到每种注入十条”。当前目录 `flash-four-mode-scale10-20261116-12`，manifest `874a87681734dbe6ca65e2e76f7512638860b40897e3b80fad08e9bbcd23122b`。上一linked11同版每种2条完整已审计成功仍不可变，先加8任务×四注入＋clean共40条；预封备用顺序保留所有失败/未触发，不重跑终局挑成功。

本轮3090新租约8卡=7主＋1Flash，actual UID1033/fullcmd/start/17继承内核锁和无外人compute已核验。两模型实际ready后，一次启动4090 GUI，站点锁真实held。定位launcher3263538/主3264775/Flash3264184/GUI1777745，不能只信PID。前台只读watcher exec session1198，不重复stage/submit/gui/watcher，不启动旧27B注意力/UI-TARS/旧Jev队列。

沿用同一协议和完整模型/图像/主历史/原生动作/预算，Flash每次单图固定质量v3、无任务/主上下文/KV；NO真实同live复拍至YES/手停。缺图前检、可信来源NO、Flash质量NO分别计数；源端签坏图仍未解决。每条完整终局需实际wire/tensors/EOS/Flash概率argmax/noKV/签名挑战账本/原生dispatch及独立原图审查；有效STOP与后续环境动作分列。正常对照、全组退出后seal/17锁和站点锁释放/8GPU成本/最终报告未完成前，目标保持ACTIVE。新成功不能按队列数量或启动计入。

`preparation-current.json`、`task-selection-current.json`、`live-progress-current.json`和最新不可变回执优先。以下旧快照保留。

'''
 for i,p in enumerate(heads[:4]):
  previous=(before/(str(i)+'-'+p.name)).read_text('utf8')if(before/(str(i)+'-'+p.name)).exists()else''
  p.write_text(header+previous,encoding='utf8')
 print(json.dumps({'root':str(root),'state':value['state'],'goal_active':True}))

if __name__=='__main__':main()
