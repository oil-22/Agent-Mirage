"""Refresh status paragraphs only; preserve all earlier experimental records."""
from pathlib import Path
here=Path(__file__).resolve().parent
status='当前状态：v3.6.2真实完整检查已到正确5美元图书详情，但在第33个候选的终止核验OOM技术中止；27次实际动作、5次真重截图、零格式失败，官方reward=1仍不能当正常完成。原错误第1页/第3页点击已在执行前拦住并实际恢复导航，首次错误保留。用户新授权空闲卡后，3090服务v8改为0–7八卡均衡放置；原生actor输入/生成token及配置完全一致，21图/31193token的原OOM请求以相同字节成功返回并通过引用校验，证明容量修复。v3.7正在做真实模型范围规则开发检查，区分限定历史报告与全局结论，并允许完整遍历或升序低价前缀两条比较证明路线。正式队列仍为technical_failure、仅1条复用baseline完成，尚未恢复新版正式运行；不宣称统计效力或整题恢复。旧结果、失败请求和哈希均保留，没有恢复小时巡检。详见[在线修复案例](在线修复案例-v3.6.2.md)、`v8-capacity-finalization.json`和`v3.7-scope-launch.json`。下方旧running描述均为历史。'
for name in ['README.md','实验协议.md','修复验证-20261025.md']:
    path=here/name
    text=path.read_text(encoding='utf-8')
    paragraphs=text.split('\n\n')
    found=False
    for index,paragraph in enumerate(paragraphs):
        if paragraph.startswith('当前状态：'):
            paragraphs[index]=status;found=True;break
    if not found:
        paragraphs.insert(1,status)
    path.write_text('\n\n'.join(paragraphs),encoding='utf-8')
print('Updated current status in README, protocol and verification; historical records retained.')
