"""Preserve former handoff heads, then bind the actual running new experiment."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    pointer=HERE.parent/'flash-late-corruption-current.json'
    assert not pointer.exists()
    progress=json.loads((HERE/'live-progress-current.json').read_bytes())
    episode=json.loads((HERE/'episode-audit-late15-T058-late_white3-gate-current.json').read_bytes())
    for p in [progress,episode]:
        root=Path(p['root']);assert sha(root/'seal.json')==p['seal_sha256']
        for n,h in json.loads((root/'seal.json').read_bytes()).items():assert sha(root/n)==h
    status=json.loads((Path(progress['root'])/'result.json').read_bytes())['result']['3090']['status']
    root=HERE/('running-checkpoint-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    header='''## 最新：新增12条持续视觉损坏配对GUI正在运行；已核实真实连续3NO复拍恢复

权威 flash-late-corruption-defense-20261115-02/live-progress-current.json、episode-audit-late15-T058-late_white3-gate-current.json 及本目录预封方案/manifest。用户要求继续多跑至明确效果，新的T003/T058/T089×late_white3/late_blur3×baseline/gate共12轨已once-only实际启动。第一项符合条件的第10步起固定3-capture损坏，包含复拍；第4起真实同live原图，底层网页本身正常。唯一Flash仍独立完整单图固定YES/NO/无主上下文或KV；原27B全史/system/2048/seed42/BF16/SDPA、50步70actor/native parser/scorer不改，NO持续复拍至YES/手停。0付费API，全部8张3090保留计成本。绝不重开旧终局或stage/submit/gui命令。

T058白屏gate第10步实际连续3NO、3个不同capture ID的真实复拍后YES，坏图不入主，原生type blue chair已执行。完整请求/首次forward/原始Flash头概率/无KV/图像源变换/链已窄审，0新增审计推理，整组退出全量仍待。先前只读seal读取把atime变化误当内容变化，失败代码/文件/回执已保全；修复仅排除atime，仍要求SHA及inode/dev/size/mtime/ctime一致。不是模型或GUI失败，不重跑模型。

截至本checkpoint为3/12终局、22完整主回复；T058白屏基线继续。T003两个白屏臂第1步原生格式失败，0环境动作、注入未触发，不算Mirage阴性或防御成功，不重试/替换。后续以最新实际进度回执为准。连续NO恢复只证机制，须审完基线及正常图/完整合法历史才能作配对Mirage结论；整体降低仍未证明。旧4轨已完整退出审计、不再重跑。以下为历史快照。

'''
    for name in ['HANDOFF.md','README.md']:
        file=HERE.parent/name;before=file.read_bytes();(root/(name+'.before')).write_bytes(before)
        file.write_bytes(header.encode('utf8')+before)
    save(root/'checkpoint.json',{'progress':progress,'episode':episode,'actual_status_at_checkpoint':status,'manifest_sha256':sha(HERE/'package/manifest.json'),'new_model_GUI_calls':0,'Mirage_reduction_proven':False})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'experiment':str(HERE),'checkpoint':str(root),'seal_sha256':sha(root/'seal.json'),'live_progress_pointer':str(HERE/'live-progress-current.json'),'state':'running','Mirage_reduction_proven':False})
    print(json.dumps({'checkpoint':str(root),'latest_heads_updated':True}))


if __name__=='__main__':main()
