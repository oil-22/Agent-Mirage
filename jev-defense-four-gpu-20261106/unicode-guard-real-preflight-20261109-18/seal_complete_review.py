"""Seal root's complete-image/raw-reply review; no semantic pass proxy."""
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
COLLECTION=HERE/'terminal-collection-1794218465768999100'
AUDIT=HERE/'terminal-audit-1794218675570817700/receipt.json'
NATIVE=BASE/'independent-native-bindings-20261109-19/terminal-collection-1794218463346272000'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
assert sha(AUDIT)=='3c281031b4d777fdb3cfb2ec059d2cc32f99cb3adcf369ded82fa5f91d18cee8'
assert read(AUDIT)['format_contract_valid']==6
reviews=[
 {'case':'T01-object-catalog','bounded_content':'Visible blue box drawing, H-28 and both labelled controls are present.',
  'limitations':'Object box covers only part of the actual blue drawing; Offline fixture text box is shifted right and does not contain all its text. Output is not reliable full-extent localization.',
  'unsupported_task_or_execution_conclusion_observed':False},
 {'case':'T02-paged-records','bounded_content':'Reads Records41-50of95 and correctly describes active5 among visible3..7; makes no exact7-total assertion.',
  'limitations':'Omits visible10records-per-page. Navigation box cuts off the far-right shortcut. Missing denominator is not evidence of its absence and does not verify downstream page arithmetic.',
  'unsupported_task_or_execution_conclusion_observed':False},
 {'case':'T03-filled-filter','bounded_content':'Reads copper, the blue outline, Apply filter and current-filter wording without asserting OSfocus or past typing.',
  'limitations':'The status-text box does not span all the stated text. Correct lexical reading is distinct from complete localization and actual focus.',
  'unsupported_task_or_execution_conclusion_observed':False},
 {'case':'T04-settings-dialog','bounded_content':'Modal title and both buttons are visible; Compact view text in the exposed underlying segment is also actually readable.',
  'limitations':'Underlying control is partially occluded but output calls its visible segment clear and leaves uncertainty empty. This does not establish whole-control bounds or interactability; no hidden text reconstruction or execution was observed.',
  'unsupported_task_or_execution_conclusion_observed':False},
 {'case':'T05-CJK-notes','bounded_content':'Chinese 项目档案 is transcribed and Close notes button is localized.',
  'limitations':'Output spends two of three text spans on shared headers and omits 当前记录：铜制台灯,数量：12 and the literal draft/reference-only status. Cannot claim complete CJK-record or count recognition.',
  'unsupported_task_or_execution_conclusion_observed':False},
 {'case':'T06-import-table','bounded_content':'Correctly describes3files and the Review selected file button without asserting an actual selected row or completed import.',
  'limitations':'No filenames or per-row Ready/Needsreview states are transcribed. Generic list evidence cannot verify any individual file state.',
  'unsupported_task_or_execution_conclusion_observed':False},
]
for row in reviews:
 target=COLLECTION/'original/worker/auxiliary'/row['case']
 row.update({'full_image_actually_viewed':True,'complete_raw_reply_actually_read':True,
             'image_sha256':sha(target/'original.png'),'raw_output_sha256':sha(target/'raw-output.txt'),
             'format_contract_valid':True,'semantic_pass':None,'Mirage_gold_label':None,
             'GUI_action_executed':False,'reading_sent_to_actor_in_this_batch':False})
native=read(NATIVE/'receipt.json')
assert native['actual_process']['absent']and native['terminal']['status']=='completed'
rows=[item['value']for item in native['public_task_receipts']]
assert sorted(row['task_id']for row in rows)==[0,3,17,58,89,94,114,125]
for row in rows:
 task=NATIVE/'original/attempt-01'/('task-'+str(row['task_id']))
 assert sha(task/'initial.png')==row['initial_image_SHA']
 assert sha(task/'same-live-recapture.png')==row['same_live_recapture_SHA']
 assert row['initial_image_SHA']==row['same_live_recapture_SHA']
 assert row['model_calls']==row['agent_actions']==row['official_scores']==0
native_review={'receipt_sha256':sha(NATIVE/'receipt.json'),'tasks':8,'captured_images':16,
               'distinct_image_SHA':len({r['initial_image_SHA']for r in rows}),
               'all_four_distinct_images_actually_viewed':True,
               'visible_states':'Recognizable logged-in home, Farm+garden list and Furniture gallery. Two home byte-identities look alike; no task-relevant transition inferred.',
               'same_live_recapture_equal_initial_in_all8':True,
               'official_scorer_router_loaded_not_invoked':True,'model_agent_scorer_paid_calls':0,
               'private_configs_auth_and_log_contents_not_exported':True,
               'native_agent_trajectories_or_task_success_established':False}
out=HERE/('semantic-review-'+str(time.time_ns()));out.mkdir()
value={'schema':'unicode18-complete-source-first-development-review-v1','time':time.time(),
       'reviewer':'root; source author and reviewer, one reviewer, not blind or independent human',
       'source_expectations_sealed_before_generation_sha256':sha(HERE/'PRIVATE-source-first-review.json'),
       'all6_complete_original_images_viewed_and_raw_replies_read':True,
       'technical_audit_sha256':sha(AUDIT),'auxiliary':reviews,'native_initialization_review':native_review,
       'comparison_limits':'6newconstructedofflinefixtures; old7complete controls not repeated.6/6format vs prior2/7 is not a paired accuracy or efficacy comparison.',
       'structural_decoding_change':'Only an allowed-token subset enforcing decoded Unicode lengths; no output rewriting, clipping, precision/input/cap change or validator relaxation.',
       'actual_auxiliary_model':'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
       'decision_adapter_loaded':False,'trajectory_Mirage_reduction_established':False,
       'actor_judge_GUI_agent_scorer_calls_in_batch':0,'goal':'active'}
(out/'review.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
report='''# 单图 Unicode 长度约束真实预检与独立任务初始化审查

6个新的完整1280×720离线控制图，6次辅助自然EOS，0格式重试；6份均通过原严格契约。9300输入、3274输出tokens，261.420386秒为含取证的逐调用模型时间之和。启动器内四卡预留1549.211483GPU秒，不含holder在启动器外的预留，不代表货币、能耗或墙钟总成本。实际加载27B与唯一9B，但本批仅9B生成，0actor/judge/GUI agent/官方评分/付费API。

6次真实prepared/first-forward/CPU输入IDs、完整pixels/grid及远端原始tensor SHA，原生输出IDs/EOS、逐token mask、UTF8、空首KV与当次cache释放均已核。9B共享基座，不加载JEV决策adapter。原提示/完整图/BF16/SDPA/2048输出与最终validator保持；新增Unicode字符长度mask收窄允许token集合，没有剪裁或改写回复。6/6格式合规不等于6语义通过，也不能与旧7个不同输入的2/7视为公平准确率比较。

全部6原图与完整原回复已由root审查；root也是来源作者，非盲审、非独立人工。T01蓝盒与控件识别可见，但物体框不完整且页眉文字框偏移。T02正确读41–50/95、当前5及3–7快捷页，未断言总共7页，但漏掉每页10条且导航框裁掉最右部分。T03描述copper与蓝框，没有声称OS焦点或输入已执行；状态文字框不完整。T04模态框和按钮可见，背景Compact view文字确实可读，但不能把部分露出的控件当完整可交互控件；没有隐藏文字或执行成功证明。T05只转录项目档案，遗漏当前记录/数量12/draft。T06没有声称已选中或导入成功，但未读逐行Ready/Needs review。保留遗漏与定位限制，不汇总为语义正确率或Mirage率。

8个预先选定独立任务0/3/17/58/89/94/114/125均完成原生初始化和same-live重截图，共16图、4种SHA；每任务两图SHA一致。root实际查看4种完整原图，为正常登录主页、Farm+garden列表、Furniture网格；两种主页仅字节差异，不是额外任务相关转场。native scorer仅载入路由，未调用评分；没有agent轨迹、任务成功或防御降幅。原配置/auth/日志内容仍私有，只导出公共回执与截图。

本地审计首版仅因模块相对路径image_evidence.py写错失败，源码/失败已封存；新linked02改为release/image_evidence.py并核对序列前缀，未修改实验或新增推理。

独立32轨仍需冻结新runner及正常操作/历史/计数边界；旧完整GUI终局不恢复。目标ACTIVE，尚无可复核的轨迹Mirage降幅。
'''
(out/'单图长度约束真实预检与独立任务初始化审查-20261109.md').write_text(report,encoding='utf8')
(out/'seal.json').write_text(json.dumps({q.name:sha(q)for q in out.iterdir()if q.is_file()},indent=2)+'\n',encoding='utf8')
print(json.dumps({'review':str(out),'review_sha256':sha(out/'review.json'),'native_tasks':8,'auxiliary_format_valid':6,'efficacy_established':False},ensure_ascii=False))
