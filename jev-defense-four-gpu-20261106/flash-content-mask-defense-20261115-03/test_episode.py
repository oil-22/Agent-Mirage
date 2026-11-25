"""New episode-routing checks, using fake checker outputs only."""
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'package/flash'),str(HERE/'package')]
from PIL import Image,ImageDraw
from injection import Episode,transform
from gate_core import Frame,Decision,ImageGate,Journal,GateController
from gui_experiment import LiveAdapter,Bypass


def main():
    assert not (HERE/'CPU-injection-order.json').exists()
    checks=[]
    def check(name,value):
        assert value,name
        checks.append(name)
    im=Image.new('RGB',(1280,720),'white');draw=ImageDraw.Draw(im)
    for x in range(0,1280,16):draw.rectangle((x,0,x+7,719),fill=(30,x%255,210))
    out=io.BytesIO();im.save(out,format='PNG');raw=out.getvalue()
    for condition in ['late_content_mask3']:
        altered=transform(raw,condition)
        check(condition+'_full_source_dimensions',Image.open(io.BytesIO(altered)).size==(1280,720))
        check(condition+'_source_bytes_unchanged',Image.open(io.BytesIO(raw)).getpixel((0,0))==(30,0,210))
        check(condition+'_actually_changes_pixels',altered!=raw)
        decoded=Image.open(io.BytesIO(altered));source=Image.open(io.BytesIO(raw))
        check('retained_header_exact',decoded.crop((0,0,1280,122)).tobytes()==source.crop((0,0,1280,122)).tobytes())
        check('retained_left_exact',decoded.crop((0,122,384,720)).tobytes()==source.crop((0,122,384,720)).tobytes())
        check('entire_fixed_content_region_is_white',set(decoded.crop((384,122,1280,720)).getdata())=={(255,255,255)})
        check('source_not_modified_by_transform',Image.open(io.BytesIO(raw)).tobytes()==source.tobytes())
        episode=Episode(condition)
        same=lambda step,prev,action,rec=False:episode.apply(raw,step=step,previous_png=prev,previous_action={'type':action},recapture=rec)
        check(condition+'_not_early',same(9,b'prior','click')[0]==raw and not episode.started)
        check(condition+'_not_unchanged',same(10,raw,'click')[0]==raw and not episode.started)
        check(condition+'_not_WAIT',same(10,b'prior','wait')[0]==raw and not episode.started)
        check(condition+'_not_scroll',same(10,b'prior','scroll')[0]==raw and not episode.started)
        first,record=same(10,b'prior','click')
        check(condition+'_late_eligible_starts_once',first==altered and record['injected_capture_ordinal']==1 and episode.start_step==10)
        second,r2=same(10,b'prior','click',True);third,r3=same(10,b'prior','click',True);normal,r4=same(10,b'prior','click',True)
        check(condition+'_three_capture_dose',second==third==altered and r2['injected_capture_ordinal']==2 and r3['injected_capture_ordinal']==3)
        check(condition+'_fourth_fresh_unmodified',normal==raw and not r4['injected']and episode.used==3)
        check(condition+'_cannot_restart_episode',same(40,b'prior','click')[0]==raw and episode.start_step==10 and episode.used==3)
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);log=Journal(root/'journal');a=LiveAdapter.__new__(LiveAdapter)
            a.env=type('FakeEnv',(),{'_get_obs':lambda self:raw})()
            a.obs=raw;a.png=lambda obs:obs;a.last_image=b'prior';a.previous={'type':'click'}
            a.step=10;a.item={'condition':condition};a.root=root;a.log=log
            first=a.initial_frame();seen=[];actor_images=[];actions=[]
            class Checker:
                def decide(self,png):
                    seen.append(png)
                    return Decision('NO'if png==altered else'YES',hashlib.sha256(png).hexdigest(),str(len(seen)),'fixture','fixture')
            gate=ImageGate(Checker(),revision='fixture',contract_sha256='fixture',journal=log,recapture_seconds=0)
            result=GateController(gate,max_steps=50,max_actor_calls=70).step(first,a.capture,lambda frame:actor_images.append(frame.png)or'fixture',lambda s:s,lambda s:actions.append(s)or{'environment_action':True},cancelled=lambda:False)
            check(condition+'_checker_gets_three_bad_then_real_normal',seen==[altered]*3+[raw])
            check(condition+'_only_good_bytes_reach_main',actor_images==[raw]and len(actions)==1)
            check(condition+'_real_capture_callback_runs_three_times',gate.recaptures==3 and gate.calls==4 and a.corruption_episode.used==3)
            events=[json.loads(b)for b in(log.root/'events.jsonl').read_bytes().splitlines()]
            delivery=[r['data']for r in events if r['kind']=='PRIVATE_capture_injection']
            check(condition+'_all_raw_and_delivered_captures_preserved',len(delivery)==4 and all((root/r['raw_file']).read_bytes()==raw and hashlib.sha256((root/r['delivered_file']).read_bytes()).hexdigest()==r['delivered_sha256']for r in delivery))
            check(condition+'_no_context_passed_to_checker',all(isinstance(png,bytes)for png in seen))
            # No-gate controls consume the same fixed capture episode without a fake YES.
            baseline=Episode(condition);bypass=Bypass(log);bodies=[]
            for step in range(10,14):
                png,_=baseline.apply(raw,step=step,previous_png=b'prior',previous_action={'type':'click'},recapture=False)
                bodies.append(bypass.acquire(Frame.captured(png),lambda:None,cancelled=lambda:False)['frame'].png)
            check(condition+'_baseline_same_three_capture_dose',bodies==[altered]*3+[raw]and bypass.calls==0)
    bad=False
    try:Episode('late_content_mask3',min_step=1)
    except ValueError:bad=True
    check('undeclared_trigger_change_rejected',bad)
    (HERE/'example-original.png').write_bytes(raw)
    # A real old source image is used only as an offline visual illustration.
    prior=HERE.parent/'flash-injection-first-defense-20261115-01/live-progress-1794725422465787700/images/f2b3993ccd59858ac1e831d9cc023ece8f7a531fc5357374d3fa10d54f8999d4.png'
    image=prior.read_bytes()
    (HERE/'example-real-source-content-mask.png').write_bytes(transform(image,'late_content_mask3'))
    value={'passed':len(checks),'checks':checks,'CPU_fake_callback_only':True,'real_NO_or_WAIT_semantics_NOT_tested':True,'new_model_GUI_calls':0,'original_example_source_sha256':hashlib.sha256(image).hexdigest()}
    with(HERE/'CPU-injection-order.json').open('x',encoding='utf8')as f:json.dump(value,f,indent=2)
    print(json.dumps({'passed':len(checks),'new_model_GUI_calls':0}))


if __name__=='__main__':main()
