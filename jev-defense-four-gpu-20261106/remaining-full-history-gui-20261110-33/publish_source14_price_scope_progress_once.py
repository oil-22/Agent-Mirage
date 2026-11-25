"""Publish new source-bound diagnoses/staging and actual original-tail progress."""
import json
from pathlib import Path
import time

from orchestrate import HERE, save
from join_source_reviews import verify_seal
from publish_current_progress_trajectory_scope_linked03 import main as publish


def main():
    pointers = [
        'source14-primary79-homepage80-semantic-review-created.json',
        'source14-price-routing-cpu-diagnosis-created.json',
        'source14-price81-83-input-review-created.json',
        'source14-price81-83-semantic-review-created.json',
        'source14-price84-85-input-review-created.json',
        'source14-price84-85-semantic-review-created.json',
        'source14-price86-87-input-review-created.json',
        'source14-price86-87-semantic-review-created.json',
        'source14-price88-input-review-created.json',
        'source14-price88-semantic-review-created.json',
        'source14-relation89-input-review-created.json',
        'source14-relation89-semantic-review-created.json',
        'source14-completion90-input-review-created.json',
        'source14-completion90-semantic-review-created.json',
        'source14-completion-source91-input-review-created.json',
        'source14-completion-source91-semantic-review-created.json',
        'source14-completion-relation92-input-review-created.json',
        'source14-completion-relation92-semantic-review-created.json',
        'literal-marking-scope-control-preparation-created.json',
        'price-reader-source-boundary-preparation-created.json',
        'completion90-observer-failure-preservation-created.json'
    ]
    authorities = {}
    for name in pointers:
        authority = json.loads((HERE / name).read_bytes())
        root = Path(authority['root'])
        assert root.parent == HERE and verify_seal(root) == authority['seal_sha256']
        authorities[name] = authority
    note = dict(
        title='历史价格九帧实读与关系核验已审；来源/范围修复草案未发送',
        goal_turn_classification='progress',
        progress_basis='Completed contiguous native provenance through0092,source-first semantics for actual0081-0092,exact13-record lineage/nine-new-four-reused audit,and sealed two UNSENT source-bound repair preparations;the same original31 queue remains live.',
        findings=[
            '真实原生回执连续0001–0092=14actor+64judge+14aux均自然EOS。实际原输入/IDs/tensors/生成参数、完整主历史/原图和跨机绑定按原回执核验；工程通过不认证语义。最新同一worker UID1033/fullcmd/start、九锁、4–7独占compute及GUI双链通过；当前0095/actor/generating，0093readiness与0094aux已封尚未纳入本次原生审计。14源候选和12已执行动作保持，未把正在生成的第15候选作语义标签。',
            '来源14的价格历史分支实际完成0080–0088九次新单帧读取，而非原CPU诊断的仅潜在九次。0089实际输入含13份冻结记录，逐项canonical匹配原始0070–0073四次缓存读取及0080–0088九次新读取；重复读价不算新GUI观察/独立任务。旧当前读取仍保留013-obs013，缓存复用不伪造当前014新推理或状态转移。',
            '各新读取的局部价格归属有来源支持，但0085–0088对小图材质/用途仍有未证实细节，reference的loading=not_observed与实际提示要求uncertain不一致；0088还把输入框kayak当已呈现查询，原面包屑仍是blue kayak/2764。原回复保留，不据此伪造strict validator拒绝或主候选新Mirage标签。',
            '0089价格关系返回supported，局部泛称蓝艇185美元有来源，但不能覆盖Grizzly10具体型号；理由还以未发现更便宜蓝艇推到cheapest，越过价格配对范围及未知颜色前提。完整原输入先封后读该回复。0090图像完成检查返回limited，却再从更便宜商品/皮划艇推出更便宜且蓝，另把65美元架子归为艇，并要求全79条而未落实允许的升序严格更便宜前缀。限定状态不自动使理由正确，未证明185全局最小或更便宜合格蓝艇。',
            '0091 supported只确认数字帧归属，不认证颜色/最低价/完成。0092 insufficient把原native answer的cannot guarantee与Based on what I observed限定抹成无条件结论，并沿用冻结评估中的错误范围理由。原候选另有明确型号错误，因此不能把整个STOP由此强行写成正常误拦；最终放行/执行/官方评分另查。各原始半句reason、引用、未知及标签全部保留。',
            '已封未发送的通用辅助v8草案与12条离线控制：在旧未发送短句<=100草案上增加照片物体实印文字与材质不确定，保留原strict180字符schema、单完整图/固定通用提示。三张已知来源原图SHA逐字节核验，PRIVATE期待隔离；合成反事实不是实际新actor/GUI结果或独立任务。另封主单帧读价来源边界草案，区分照片/标题、输入框/结果面包屑、菜单选项/已选排序及reference加载。代价是固定文字槽/预算可能挤掉其他细节，更多指令不保证准确；原生ID/GPU与新不同来源真实控制尚未完成，均未上线/未推理/未改当前32条件或路由。',
            '只读完成输入观察器曾假设payload图像有sha256键而KeyError；原输入/命令文本/错误摘录先封存，新链接只按完整raw_base64计算SHA并核对13原图库存。实际0090输入是任务+原图/来源，未含actor上下文。0观察器引发模型/GUI/scorer重试，原回复/图像/实验条件未改。',
            '源13/14两阳性仍属同一fullhistory23-T000-clean-aux轨，一次即计的Mirage已发生；不是两条独立轨或2/14触发率。14候选互斥构成仍7明确阴性、5仅未知、2阳性且另有未知，任意未知涉及7个。最新已封来源关联未accepted/executed；第15恢复生成及未完成全32/16对/8任务的端点、正常操作、曝光/成本、官方评分与相对降幅分别保留未知，目标ACTIVE。'
        ],
        additional_immutable_authorities=authorities,
        current_original32_conditions_unchanged=True,
        no_new_model_GUI_scorer_calls_from_observer_or_preparation=True,
        original32_effect_and_full_completion_unproven=True)
    note_path = HERE / ('source14-price-scope-progress-note-' + str(time.time_ns()) + '.json')
    save(note_path, note)
    publish(HERE / 'actual-evidence-1794266492944262000', 92, note_path)


if __name__ == '__main__':
    main()
