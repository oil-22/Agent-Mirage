"""Freeze the new contract, explicit user choices, and four-call wiring check."""
import json,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from manage import HERE,sha,save
def main():
    old=HERE.parent/'binary-gate-comparison-20261112';protocol=json.loads((old/'protocol.json').read_bytes())
    contract={k:protocol[k]for k in ['state','question','options']}
    contract.update({'version':'flash-single-image-usability-gate-v1','repository':'perplexity-ai/pplx-decider-flash-v1.2','revision':'9ff7cf9838e59df461c276b7699d56b244d2af58'})
    save(HERE/'gate-contract.json',contract)
    with (HERE/'flash-identity.json').open('xb')as f:f.write((old/'flash-identity.json').read_bytes())
    config={**protocol['models']['flash'],'physical_gpu':7,'port':18341,'python':'/home/researcher/jev-defense-four-gpu-20261106/flash-preparation/env-flash-01/bin/python','stable_identity_sha256':sha(HERE/'flash-identity.json')}
    save(HERE/'service-config.json',config)
    save(HERE/'user-authorization.json',{'recorded_local_date':'2026-11-13','flash_selection':'那你就用flash吧，按我的框架去搭建','recapture_question':'Flash 返回 NO 后，复拍次数怎么设？','recapture_answer':'持续复拍，直到 YES 或手动停止','single_image_fixed_prompt_independent_calls':True,'continuous_recapture':True,'recapture_limit':None,'total_auxiliary_call_cap':None,'recapture_interval_seconds':0.5,'technical_failures_are_not_NO':True,'no_automatic_technical_retry':True,'old_GUI_goal_remains_paused':True,'actor_max_calls':70,'max_main_steps':50,'condition_change':'New binary image gate only; no old contextual semantic verifier. NO continuously recaptures instead of old 2-recapture/60-aux limits. Complete native main history/actor/parser/executor remain their original callbacks.','created':time.time()})
    inputs=HERE/'preflight-inputs';inputs.mkdir()
    blank=Image.new('RGB',(960,640),'white');blank.save(inputs/'new-blank.png')
    im=Image.new('RGB',(960,640),'#f4f6f8');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    d.rectangle((0,0,959,74),fill='#123c64');d.text((26,20),'Workspace settings',font=font,fill='white')
    d.rectangle((30,105,930,515),fill='white',outline='#b3c0cc',width=2)
    d.text((55,130),'Appearance',font=font,fill='#13283e');d.text((55,190),'Theme: Light',font=small,fill='#182635');d.text((55,245),'Text size: Default',font=small,fill='#182635')
    d.rectangle((55,325,220,380),fill='#1763a1');d.text((75,338),'Save settings',font=small,fill='white')
    d.text((36,570),'Help     Privacy     Version 1.0',font=small,fill='#334455');im.save(inputs/'new-readable.png')
    oldhashes={r['sha256']for r in protocol['cases']}
    cases=[{'file':p.name,'sha256':sha(p),'size':[960,640],'synthetic':True}for p in sorted(inputs.glob('*.png'))]
    assert all(r['sha256']not in oldhashes for r in cases)
    save(HERE/'preflight-plan.json',{'version':'new-wiring-only-4calls','created':time.time(),'max_new_Flash_calls':4,'expected_sequence':['NO','NO','YES','NO'],'first_three':'Two fresh capture IDs of new blank then new readable: only last image forwarded to a native-main-history/parser/executor fixture.','fourth':'A fresh blank call with manual stop while call in flight; do not forward regardless of eventual answer.','fixture_only':True,'same_live_GUI_experiment':False,'stop_if_finite_fixture_exhausted':'technical fixture stop, never a model NO or production recapture cap','no_rerun_or_budget_expansion':True,'contract_sha256':sha(HERE/'gate-contract.json'),'cases':cases,'main_model_calls':0,'GUI_actions':0,'paid_API_calls':0,'Mirage_reduction':None})
    print(json.dumps({'contract_sha256':sha(HERE/'gate-contract.json'),'plan_sha256':sha(HERE/'preflight-plan.json'),'cases':cases}))
if __name__=='__main__':main()
