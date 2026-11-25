"""Record the newly established pairing limit without altering the live batch."""
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    pointer=HERE/'T089-pairing-checkpoint-current.json';assert not pointer.exists()
    pointers={}
    for name in ['live-progress-current.json','runtime-refresh-current.json','semantic-review-late15-T089-late_white3-baseline-current.json','T089-white-gate-prefix10-source-review-current.json']:
        pointers[name],_=checked(HERE/name)
    pr=Path(pointers['live-progress-current.json']['root'])
    status=json.loads((pr/'result.json').read_bytes())['result']['3090']['status']
    root=HERE/('pairing-checkpoint-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    head=f'''## 最新：新增12轨为{status['done']}终局；T089配对在注入前第6步已不同源

权威 flash-late-corruption-defense-20261115-02/live-progress-current.json、semantic-review-late15-T089-late_white3-baseline-current.json、T089-white-gate-prefix10-source-review-current.json 及本checkpoint。此快照{status['complete_actor_replies']}完整主回复，实际活动{status.get('active')}。原once-only12轨继续；旧终局/stage/submit/gui不重开，原模型/全史/图像/参数预算与唯一Flash单图YES-NO持续真复拍条件不改。

T089白图baseline已50步step_cap，50完整回复/50环境动作、0infra/cleanup；50候选29原PNG完整源审，确定当前文字误读27/28/33，未决23/24/25，纯WAIT11/12排除。阳性都在注入后的正常图，不能说白图当场诱发。gate前10已审，1–5完整body/reply/PNG与baseline相同；第6步baseline有城市下拉而gate没有，尚未注入已分化，原因未实验确定。实际注入baseline11/gate10，后续即使gate更顺也不得全归因门控或宣称精确匹配的降低。原图显示gate走Illinois>Virginia城市，不能冒称Virginia州；策略错误与Mirage另列。

gate第10步已见3NO→同live3真复拍→正常原图YES并继续click Apply，但全轨及fresh原始forward/Controller审计仍待，不能由前10无确定错误推出全轨阴性。T05839候选完整配对仍只证连续NO恢复、未证降低。两T003白图首步格式失败0动作/未注入保留，不算语义零/成功。全部12与模糊队列保持，整体目标未完成。最新3090实际UID/fullcmd/start/主17与Flash9继承锁/日志SHA核实、无外人compute，全部8卡保留计成本。以下旧快照。

'''
    latest=HERE.parent/'flash-late-corruption-current.json'
    (root/'previous-current.json').write_bytes(latest.read_bytes())
    for name in ['HANDOFF.md','README.md']:
        p=HERE.parent/name;raw=p.read_bytes();(root/(name+'.before')).write_bytes(raw)
        p.write_bytes(head.encode('utf8')+raw)
    save(root/'checkpoint.json',{'time':time.time(),'sources':pointers,'actual_status_at_checkpoint':status,'Mirage_reduction_proven':False,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    value={'root':str(root),'seal_sha256':sha(root/'seal.json')}
    save(pointer,value)
    latest.write_text(json.dumps({'experiment':str(HERE),'checkpoint':str(root),'seal_sha256':value['seal_sha256'],'live_progress_pointer':str(HERE/'live-progress-current.json'),'state':'running','Mirage_reduction_proven':False},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'checkpoint':str(root),'pre_injection_pair_limit_recorded':True,'new_model_GUI_calls':0}))


if __name__=='__main__':main()
