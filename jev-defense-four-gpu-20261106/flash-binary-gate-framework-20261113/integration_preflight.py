"""Four new real Flash requests; native-main/execution callbacks are fixtures."""
import base64,copy,json,threading,time,urllib.error,urllib.request
from pathlib import Path
from gate_core import Frame,GateController,ImageGate,Journal,NativeHistoryActor,digest
from gate_client import FlashClient
from resource_guard import sha
from flash_runtime import save
from wire_contract import REVISION

def main(package):
    root=package/'integration-preflight';root.mkdir(exist_ok=False)
    plan=json.loads((package/'preflight-plan.json').read_bytes());contract_sha=sha(package/'gate-contract.json')
    blank=(package/'preflight-inputs/new-blank.png').read_bytes();good=(package/'preflight-inputs/new-readable.png').read_bytes()
    for row in plan['cases']:assert sha(package/'preflight-inputs'/row['file'])==row['sha256']
    client=FlashClient('http://127.0.0.1:18341',package/'service/token',revision=REVISION,contract_sha256=contract_sha)
    decisions=[];bodies=[];proposals=[]
    class LimitedCheck:
        def decide(self,png):
            if len(decisions)>=4:raise RuntimeError('Finite integration fixture exhausted; no fifth model call')
            result=client.decide(png);decisions.append(result.__dict__);return result
    checker=LimitedCheck();gate=ImageGate(checker,revision=REVISION,contract_sha256=contract_sha,journal=Journal(root/'forward-fixture'),recapture_seconds=0)
    template={'model':'NATIVE_MAIN_FIXTURE_NO_MODEL','messages':[{'role':'system','content':'Original native system sentinel'},{'role':'user','content':'All main history retained; never sent to Flash'},{'role':'assistant','content':'Previous native reply sentinel'}],'max_tokens':2048,'temperature':0,'seed':42,'chat_template_kwargs':{'enable_thinking':False}}
    actor=NativeHistoryActor(template,lambda body:bodies.append(copy.deepcopy(body))or '{"type":"click","x":100,"y":200}',text_blocks=[{'type':'text','text':'Original current task sentinel'}])
    captures=iter([Frame.captured(blank),Frame.captured(good)])
    result=GateController(gate).step(Frame.captured(blank),lambda:next(captures),actor,json.loads,lambda proposal:proposals.append(copy.deepcopy(proposal))or {'fixture':True,'environment_action':False},cancelled=lambda:False)
    if result['status']=='dispatched':actor.commit(result)
    save(root/'main-fixture-request.json',bodies);save(root/'native-fixture-dispatches.json',proposals)
    # This thread sets cancellation while the fourth actual HTTP call is in
    # flight; the core must check it again after the reply before forwarding.
    event=threading.Event();during=[]
    class CancelDuringCall:
        def decide(self,png):
            def stop():time.sleep(0.02);event.set();during.append(time.time())
            t=threading.Thread(target=stop);t.start()
            try:return checker.decide(png)
            finally:t.join()
    gate2=ImageGate(CancelDuringCall(),revision=REVISION,contract_sha256=contract_sha,journal=Journal(root/'cancellation-fixture'),recapture_seconds=0)
    forwarded=[];executed=[]
    second=GateController(gate2).step(Frame.captured(blank),lambda:Frame.captured(good),lambda f:forwarded.append(f)or '{}',json.loads,lambda p:executed.append(p),cancelled=event.is_set)
    observed=[r['value']for r in decisions]
    bindings=(len(bodies)==1 and base64.b64decode(bodies[0]['messages'][-1]['content'][-1]['image_url']['url'].split(',')[1])==good and bodies[0]['messages'][:3]==template['messages'] and {k:v for k,v in bodies[0].items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'})
    checks={'expected_new_binary_sequence':observed==plan['expected_sequence'],'only_exact_yes_frame_forwarded':bindings,'original_native_proposal_unmodified':proposals==[{'type':'click','x':100,'y':200}],'no_image_or_prompt_sent_after_cancel':second['status']=='cancelled'and not forwarded and not executed,'four_new_actual_calls':len(decisions)==4,'no_response_reuse':len({r['request_id']for r in decisions})==4}
    save(root/'decisions.json',decisions)
    terminal={'status':'passed'if all(checks.values())else'failed','checks':checks,'observed':observed,'new_Flash_calls':len(decisions),'forward_fixture_status':result['status'],'cancellation_fixture_status':second['status'],'stop_during_call_times':during,'fixture_dispatches':len(proposals),'actual_environment_actions':0,'main_model_calls':0,'GUI_trajectories':0,'Mirage_reduction':None,'time':time.time()}
    save(root/'terminal.json',terminal);save(root/'seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
    print(json.dumps(terminal))
if __name__=='__main__':
    import sys,traceback
    package=Path(sys.argv[1])
    try:main(package)
    except BaseException:
        root=package/'integration-preflight'
        if not (root/'failure.json').exists():save(root/'failure.json',{'error':traceback.format_exc(),'no_automatic_retry':True})
        if not(root/'failure-seal.json').exists():save(root/'failure-seal.json',{str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()})
        raise
