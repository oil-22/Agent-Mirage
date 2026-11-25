"""Connect original live native callbacks; never start an archived GUI queue."""
import argparse,importlib.util,json,signal,threading
from pathlib import Path
from gate_core import Frame,GateController,ImageGate,Journal
from gate_client import FlashClient
from resource_guard import sha
from wire_contract import REVISION

def run(adapter,*,client,contract_sha256,evidence,stop_file,recapture_seconds=0.5,max_steps=50,max_actor_calls=70,stop_event=None):
    """adapter.capture_png() must capture its same live environment, unmodified.

    For injection experiments, adapter.capture_png includes injection BEFORE
    the gate. It must not check a clean image and later supply an injected one.
    adapter.actor(Frame), parse(text), execute(proposal) are the original
    native callbacks. execute returns environment_action true/false/unknown.
    adapter.observe_result(result) can commit the dispatched native exchange
    and actual execution feedback to the main model's complete history.
    """
    event=stop_event or threading.Event();journal=Journal(evidence)
    cancelled=lambda:event.is_set()or Path(stop_file).exists()
    capture=lambda:Frame.captured(adapter.capture_png())
    gate=ImageGate(client,revision=REVISION,contract_sha256=contract_sha256,journal=journal,recapture_seconds=recapture_seconds)
    controller=GateController(gate,max_steps=max_steps,max_actor_calls=max_actor_calls)
    terminal={'status':'not_started'}
    try:
        while not cancelled():
            if adapter.done():terminal={'status':'native_done'};break
            result=controller.step(capture(),capture,adapter.actor,adapter.parse,adapter.execute,cancelled=cancelled)
            adapter.observe_result(result)
            if result['status']!='dispatched':terminal={'status':result['status'],'reason':result.get('reason')};break
        else:terminal={'status':'cancelled','reason':'manual_stop'}
    except Exception as e:
        terminal={'status':'technical_failure','reason':type(e).__name__,'message':str(e),'no_automatic_retry':True}
    finally:
        terminal.update({'gate_calls':gate.calls,'recaptures':gate.recaptures,'actor_calls':controller.actor_calls,'decisions':controller.steps,'mirage_reduction':None})
        journal.emit('controller_terminal',terminal)
        with (journal.root/'terminal.json').open('x',encoding='utf8')as f:json.dump(terminal,f,indent=2)
    return terminal

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--stop-file',type=Path,required=True);p.add_argument('--url',default='http://127.0.0.1:18341');p.add_argument('--token-file',type=Path,required=True);p.add_argument('--contract',type=Path,default=Path(__file__).parent/'gate-contract.json');a=p.parse_args()
    spec=importlib.util.spec_from_file_location('original_live_adapter',a.adapter);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    adapter=module.create_adapter();event=threading.Event()
    signal.signal(signal.SIGINT,lambda *_:event.set());signal.signal(signal.SIGTERM,lambda *_:event.set())
    client=FlashClient(a.url,a.token_file,revision=REVISION,contract_sha256=sha(a.contract))
    print(json.dumps(run(adapter,client=client,contract_sha256=sha(a.contract),evidence=a.evidence,stop_file=a.stop_file,stop_event=event)))
if __name__=='__main__':main()
