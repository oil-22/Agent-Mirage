"""Publish a sealed running prefix; never mark launch or partial work complete."""
import json
import time
from pathlib import Path
from control import HERE,PACKAGE,manifest,save,sha
from join_reviewed_results import pointer,verify,MODES

def main():
 review_root,review_binding=pointer('review-checkpoint-current.json')
 progress_root,progress_binding=pointer('live-progress-current.json')
 review=json.loads((review_root/'result.json').read_bytes())
 progress=json.loads((progress_root/'result.json').read_bytes())['result']
 previous=json.loads((PACKAGE/'previous-completed-campaign.json').read_bytes())['report']
 old=verify(previous['root'],previous['seal_sha256']);prior=json.loads((old/'report.json').read_bytes())
 counts={k:review['successful_complete_trajectories_per_condition'][k]+prior['successful_complete_trajectories_per_condition'][k]for k in MODES}
 rows=review['rows'];assert len(rows)<40 and progress['status']['phase']=='running'
 root=HERE/('goal-continuation-checkpoint-'+str(time.time_ns()));root.mkdir();before=root/'before';before.mkdir()
 heads=[HERE/'README.md',HERE/'HANDOFF.md',HERE.parent/'README.md',HERE.parent/'HANDOFF.md',HERE.parent/'active-defense-goal-current.json']
 for i,p in enumerate(heads):
  if p.exists():(before/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
 value={'time':time.time(),'goal_active':True,'active_study':str(HERE),'state':'scale10_running_reviewed_prefix',
  'target_per_mode':10,'prior_successes_per_mode':prior['successful_complete_trajectories_per_condition'],
  'new_reviewed_successes_per_mode':review['successful_complete_trajectories_per_condition'],'cumulative_verified_successes_per_mode':counts,
  'new_complete_raw_audited_and_reviewed_trajectories':len(rows),'initial_new_total_trajectories':40,
  'all_new_reviewed_rows':rows,'reviewed_untriggered_or_failed':[r for r in rows if r['condition']!='clean_control'and not r.get('user_normal_frame_delivery_passed',False)],
  'review_binding':review_binding,'previous_completed_report':previous,'progress_binding':progress_binding,
  'current_runtime_snapshot':progress['status'],'watcher_exec_session':1198,
  'new_reviewed_normal_path_exposures':sum(r['normal_path_captures']for r in rows),
  'new_reviewed_unknown_quality_exposures':sum(r['normal_path_unknown_quality_captures']for r in rows),
  'new_reviewed_normal_Flash_false_blocks':sum(r['normal_usable_Flash_false_blocks']for r in rows),
  'new_complete_clean_controls':sum(r['condition']=='clean_control'for r in rows),
  'whole_group_raw_final_seal_release_cost_report_and_reserve_if_deficit_pending':True,
  'source_NO_is_Flash_detection':False,'PNG_reuse_adds_no_visual_diversity':True,'new_model_GUI_calls':0}
 save(root/'checkpoint.json',value)
 (root/'source.py').write_bytes(Path(__file__).read_bytes())
 save(root/'seal.json',{p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()})
 binding={'root':str(root),'seal_sha256':sha(root/'seal.json'),'state':value['state'],'active_study':str(HERE),'goal_active':True,'watcher_exec_session':1198}
 for p in [HERE/'goal-continuation-current.json',HERE.parent/'active-defense-goal-current.json']:
  temp=p.with_name('.scale10-checkpoint-'+str(time.time_ns()));save(temp,binding);temp.replace(p)
 header=('## 2026-11-16 每种10条扩展：累计已核验缺图/白图/旧帧/按钮='+
  '/'.join(str(counts[k])for k in MODES)+'，目标ACTIVE\n\n'+
  '权威 `'+str(root/'checkpoint.json')+'`，seal '+binding['seal_sha256']+'。新40轨已有'+str(len(rows))+'条全raw审计及原图审查；成功仅按完成且通过的闭环计入。未触发/失败原样保留，缺口待本批后按预封备用任务顺序补足。正常对照、全组退出后seal、资源释放/8GPU成本和最终汇总均仍待。\n\n'+
  '现有单个前台只读watcher exec session1198继续；不要stage/submit/gui或再开watcher，不重跑已终局轨迹。最新live-progress与actual request/reply优先，PID只定位。Flash独立单图固定质量提示及原主完整历史/预算保持；来源拒绝不称Flash检出。以下旧快照保留。\n\n')
 for i,p in enumerate(heads[:4]):p.write_text(header+(before/(str(i)+'-'+p.name)).read_text('utf8'),encoding='utf8')
 print(json.dumps({'root':str(root),'cumulative_successes':counts,'new_complete_reviewed':len(rows),'goal_active':True}))

if __name__=='__main__':main()
