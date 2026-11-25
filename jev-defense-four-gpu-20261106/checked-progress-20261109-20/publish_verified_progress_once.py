"""New immutable publication for completed16/17/18/19 and prepared21 only."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha


def main():
    assert not(HERE/'publication-created.json').exists()
    evidence={
      'controls16_technical_audit':('balanced-visual-evidence-20261109-16/terminal-audit-1794217134123770200/receipt.json','a557abf26b49c370ad4b7600126aefabf17fa34f025bc4e5cda8b47331961391'),
      'controls16_semantic_review':('balanced-visual-evidence-20261109-16/semantic-review-01/review.json','739e3d591ba413b2324bbbc456149119023ccd9adb31d444700415107058817e'),
      'unicode17_native_CPU9':('unicode-length-guard-20261109-17/native-CPU-inspection-1794217355774954300/receipt.json','e7b6fa7d25060e31746616c49510d84651dd5518cb508753ab1702f39c49abdc'),
      'unicode18_terminal_collection':('unicode-guard-real-preflight-20261109-18/terminal-collection-1794218465768999100/receipt.json','3eac806dbd94b5ccbddf2a770beaf65b4f8ef78e61f356185ff74e109405721a'),
      'unicode18_technical_audit':('unicode-guard-real-preflight-20261109-18/terminal-audit-1794218675570817700/receipt.json','3c281031b4d777fdb3cfb2ec059d2cc32f99cb3adcf369ded82fa5f91d18cee8'),
      'unicode18_complete_review':('unicode-guard-real-preflight-20261109-18/semantic-review-1794218878811259600/review.json','25185ad340a7b8648950dfb5e9b7c2dde238cc267d1d543a47fd30ad1e8bbb32'),
      'native19_terminal_collection':('independent-native-bindings-20261109-19/terminal-collection-1794218463346272000/receipt.json','b10ede179c8ee1e84aad9d630ab55fe483ca7fa902d4a4d7ee1cb3b85e17367b'),
      'history21_CPU8':('independent-gui-runner-preparation-20261109-21/CPU-boundary-checks-1794218976767160300/receipt.json','1197dfcba23b7a940c98e39015748ef56a87083b1f621edeaa668431f60ffe1c'),
      'independent21_source_only':('independent-gui-runner-preparation-20261109-21/prepared-source-linked02/preparation-receipt.json','9260016208f396872fa603454b00c300d8d1d0e9b17792abb5e144a30d0b79c3'),
    }
    for _,(name,expected)in evidence.items():assert sha(BASE/name)==expected,name
    code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
b=Path('/home/researcher/jev-defense-four-gpu-20261106')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
assert os.getuid()==1033
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());record=lease['holder'];actual=identity(record['pid'])
assert all(str(actual[k])==str(record[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
locks=[]
for row in lease['lock_records']:
 p=Path('/proc',str(record['pid']));fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(record['pid'])in info
 locks.append({'path':row['path'],'fd':row['fd'],'inode':row['inode']})
assert len(locks)==9 and {row['index']for row in lease['gpu']}=={4,5,6,7}
closed=[]
for name,expected in [('balanced-visual-evidence-20261109-16','9e1abb821738d9f4308fc2bbb8f6ab7aa95cb218246d2d4984217f7d689eb479'),
                     ('unicode-guard-real-preflight-20261109-18','461bb53b23f038d40013c05241dba051b8104cd6d4f0b5ac476ab02529bd9cdf')]:
 r=b/name;assert sha(r/'terminal-manifest.json')==expected
 workers=[]
 for rel in ['launcher-process.json','worker/process.json']:
  rec=json.loads((r/rel).read_bytes());now=identity(rec['pid']);assert now.get('absent')is True
  workers.append({'record':rec,'actual':now})
 closed.append({'name':name,'processes':workers,'terminal_manifest_sha256':expected,'exit':json.loads((r/'exit.json').read_bytes())})
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
targets={row['uuid']for row in lease['gpu']}
assert not any(line.split(',')[0].strip()in targets for line in compute.splitlines()if line.strip())
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
print(json.dumps({'time':time.time(),'read_only':True,'new_model_GPU_GUI_scorer_paid_calls':0,'holder':actual,
                  'held_locks':locks,'authorized_GPUs':[4,5,6,7],'closed_experiments':closed,
                  'compute_snapshot':compute,'GPU_snapshot':gpu,'four_authorized_GPUs_compute_empty':True}))
'''
    output,operation=remote('3090',code,'publication20-fresh-holder-locks-closed16-18-no-model',timeout=55)
    fresh=json.loads(output)
    publication=HERE/('publication-'+str(time.time_ns()));publication.mkdir()
    previous=publication/'previous-heads';previous.mkdir()
    heads=['HANDOFF.md','README.md','full-gui-current.json']
    prior={}
    for name in heads:
        raw=(BASE/name).read_bytes();(previous/name).write_bytes(raw);prior[name]=hashlib.sha256(raw).hexdigest()
    save(publication/'fresh-proof.json',dict(fresh,operation=str(operation)))
    previous_state=json.loads((BASE/'full-gui-current.json').read_bytes())
    status=copy.deepcopy(previous_state)
    status.update(schema='audited-defense-progress-20261109-v2',time=time.time(),publication=str(publication),
                  goal='active',monitor_should_remain_active=True,efficacy_established=False)
    status['authoritative_evidence'].update({key:{'path':str(BASE/name),'sha256':expected}for key,(name,expected)in evidence.items()})
    status['controls16']={'phase':'completed','auxiliary':7,'actor':8,'judge':22,'natural_EOS':37,
          'auxiliary_contract_valid':2,'judge_format_citation_valid':22,'semantic_pass_count':None,
          'known_semantic_failures':'Both actor conditions false page3of4; both judges support exact4 despite72/12=6; plan/history classification and native direction conflict remain.',
          'complete_raw_reply_review':True,'must_not_retry':True,'GUI_scorer_calls':0}
    status['unicode17']={'phase':'completed','local_CPU_boundaries':58,'native_CPU_cases':9,'GPU_calls':0,
                          'old_failed_test_assertion_and_linked02_preserved':True}
    status['unicode18']={'phase':'completed','auxiliary_calls':6,'natural_EOS':6,'format_contract_valid':6,
          'actor_judge_GUI_scorer_paid_calls':0,'format_retries':0,'actual_forward_tensors_and_stateless_boundary_verified':True,
          'input_tokens':9300,'output_tokens':3274,'summed_instrumented_model_seconds':261.4203862324357,
          'four_GPU_reserved_seconds_in_launcher':1549.211483001709,
          'semantic_limitations':'Partial/misaligned boxes, omitted per-page denominator/CJK details/per-row states; no accuracy or efficacy label.',
          'must_not_retry_completed_controls':True}
    status['native19']={'phase':'completed','tasks':8,'native_initializations':8,'same_live_recaptures':8,
          'captured_images':16,'distinct_image_SHA':4,'all_task_pairs_same_SHA':True,
          'actual_process_absent':True,'model_agent_scorer_paid_calls':0,'scorer_router_loaded_not_invoked':True,
          'native_trajectories_or_task_success_established':False,'private_auth_configs_log_contents_not_exported':True}
    status['independent_GUI21']={'phase':'source_preparation_only','tasks':8,'planned_tracks':32,'matched_pairs':16,
          'noaux_first_pairs':8,'aux_first_pairs':8,'launch_ready':False,'actual_GUI_tracks_started':0,
          'accepted_history_CPU_boundaries_passed':8,
          'history_gap_found':'Old runner used text placeholders for previous actor image requests; old images retrieved separately by verifier. New source retains actual accepted main request/reply messages including complete image blocks and auxiliary data in both arms.',
          'within_decision_Controller_recovery_unchanged':True,
          'remaining_admission':['Source-bound normal-operation/negative/WAIT checks','Actual full accepted-history capacity','Repair freeze and once-only service/scorer transport']}
    status['resources'].update(inference_workers_actually_absent=True,compute_empty_at_fresh_publication_check=True,
         original_holder_locks_retained=True,holder_actual_identity=fresh['holder'],fresh_proof_sha256=sha(publication/'fresh-proof.json'))
    status['next_action']='Use new complete-history generic runner, finish source-bound normal/negative/WAIT and full-history capacity admission before32independent matched GUI tracks. No old queue resumes.'
    save(publication/'status.json',status)
    header='''## 最新：2026-11-09 单图长度约束6EOS与8独立任务初始化终局；完整主历史缺口已定位

权威：`PUBLICATION/status.json`及同目录fresh-proof；新18全部6实际自然EOS、6原严格格式契约valid、0retry、0actor/judge/GUI agent/scorer/付费。完整图/native CPU-prepared-first-forward IDs/pixels/grid/远端binary SHA/逐token mask/空首KV与cache释放/34链已核，worker4040458与launcher4040201实际均消失、exit0。永不重跑6完成控制。新增mask只收窄Unicode长度，未剪裁/改写输出或放宽validator；6不同新图不能与旧2/7作公平准确率比较。仍有不完整/偏移框与中文记录、页容量、逐行状态遗漏，不是6语义通过或防御效果。

新19的0/3/17/58/89/94/114/125八任务原生初始化＋同浏览器重截图均终局，16图4种SHA，每任务两图相同，实际进程3781974消失。官方scorer仅路由加载，0agent/model/评分，不是GUI轨迹成功。私有config/auth/日志内容未导出。新16旧37EOS及完整语义负结果、17原生CPU9已封存，禁止重刷完成控制。

关键新发现：旧GUI runner给下一决策主模型保存Task/Previous observation request文字占位；历史原图另供verifier检索。这不满足完整主图像历史要求，不能继续沿用旧runner。新21准备源码保留实际accepted actor请求/回复、完整图像块、原correction与辅助数据，两组一致，原Controller单决策恢复不变；8CPU边界通过。32轨顺序已冻结16配对中8noaux先/8aux先，但仅源码准备，launch_ready=false/0轨开始。正常操作/负例/WAIT及新的完整历史容量/服务scorer绑定仍需准入。旧终局不恢复。

实际辅助仍Qwen3.5-9B共享基座，decision_adapter_loaded=false。fresh-proof核holder完整UID/cmd/start及4–7九锁、两新worker/launcher退出和终局SHA；4–7无compute但holder仍预留，0–3不授权。目标ACTIVE；没有可复核轨迹Mirage降幅，不暂停monitor。

'''.replace('PUBLICATION',publication.relative_to(BASE).as_posix())
    report='''# 防御实验核验进展：单图结构修复与独立GUI准备

单图Unicode长度约束在6个新的完整离线控制输入中获得6次自然EOS，全部满足原严格输出契约。真实完整输入、输出IDs/EOS、原始tensor SHA、逐token mask和stateless cache边界已核；这说明本批格式问题未重现，不能证明语义准确或Mirage下降。部分框不完整或偏移，关键中文记录/页容量/逐行状态仍有遗漏。详见新18完整语义审查。

8个预先选择的独立任务均通过原生初始化与same-live重截图；仅加载官方评分路由，没有agent轨迹或官方评分。全部私有原配置/auth仍留远端，公共图和回执已收集审查。

新发现的主历史问题已在新21准备源码修复：旧runner给后续actor的历史是文字观察占位，图像只保存在核验器reference bank；新版本保存实际accepted actor请求/回复与完整图像，两组同规则，原单决策恢复机制不变。8CPU边界通过，32轨已冻结，尚未启动。完整主历史会增加显存使用，旧20382-token容量结果不能证明新历史fit。正常操作/负例/WAIT、完整历史容量及新服务/评分transport仍需完成。

旧终局、失败和完成控制不重跑。实际辅助是Qwen3.5-9B共享基座，无JEV专用decision adapter。当前仍无公平可复核的轨迹Mirage降幅，目标保持ACTIVE。
'''
    (publication/'防御实验核验进展-20261109.md').write_text(report,encoding='utf8')
    save(publication/'receipt.json',{'time':time.time(),'authoritative_status_sha256':sha(publication/'status.json'),
         'fresh_proof_sha256':sha(publication/'fresh-proof.json'),'prior_heads_SHA':prior,
         'all_local_authorities_rehashed':True,'new_model_GUI_calls':0,'goal':'active'})
    save(publication/'seal.json',{q.relative_to(publication).as_posix():sha(q)for q in publication.rglob('*')if q.is_file()})
    # Mutable pointers only, after complete old bytes and immutable evidence are saved.
    for name in ['HANDOFF.md','README.md']:
        assert sha(BASE/name)==prior[name]
        (BASE/name).write_bytes(header.encode('utf8')+(previous/name).read_bytes())
    assert sha(BASE/'full-gui-current.json')==prior['full-gui-current.json']
    (BASE/'full-gui-current.json').write_bytes((publication/'status.json').read_bytes())
    save(HERE/'publication-created.json',{'publication':str(publication),'receipt_sha256':sha(publication/'receipt.json'),
         'seal_sha256':sha(publication/'seal.json'),'heads_updated':heads,'time':time.time()})
    print(json.dumps({'publication':str(publication),'receipt_sha256':sha(publication/'receipt.json'),
                      'auxiliary18_EOS':6,'native19_initializations':8,'independent_GUI21_started':0,'goal':'active'},ensure_ascii=False))


if __name__=='__main__':
    main()
