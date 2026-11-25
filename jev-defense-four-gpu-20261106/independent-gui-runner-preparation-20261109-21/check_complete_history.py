"""Finite CPU boundary checks for actual accepted request/reply retention."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import time
from PIL import Image
from complete_actor_history import CompleteAcceptedActorHistory, HistoryBindingError, digest

HERE = Path(__file__).resolve().parent


def main():
    checks = []
    def image(colour):
        out=io.BytesIO()
        Image.new('RGB', (1280,720), colour).save(out, format='PNG')
        return {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()}}
    first, second = image('red'), image('blue')
    for auxiliary in [False, True]:
        history = CompleteAcceptedActorHistory('Original native actor SYSTEM')
        blocks = [{'type':'text','text':'Task: original public intent'},first]
        if auxiliary:
            blocks.append({'type':'text','text':'Fallible auxiliary data: literal first frame only'})
        body={'model':'native27B','max_tokens':2048,'messages':history.current_messages(blocks)}
        unchanged=copy.deepcopy(body)
        reply='<action>{"type":"click","x":500,"y":500}</action>'
        history.record_actual_reply(body,reply)
        proof=history.commit_accepted({'status':'accepted','candidate':reply,'observation_id':'first'})
        assert body==unchanged and history.messages==body['messages'][1:]+[{'role':'assistant','content':reply}]
        checks.append({'arm_auxiliary':auxiliary,'case':'complete_first_actual_request_and_reply_retained','passed':True})
        next_body={'model':'native27B','max_tokens':2048,
                   'messages':history.current_messages([{'type':'text','text':'Task: original public intent'},second])}
        assert next_body['messages'][1:1+len(history.messages)]==history.messages
        assert first in next_body['messages'][1]['content']
        assert second in next_body['messages'][-1]['content']
        if auxiliary:
            assert next_body['messages'][1]['content'][-1]['text'].endswith('first frame only')
        checks.append({'arm_auxiliary':auxiliary,'case':'earlier_complete_native_image_and_auxiliary_block_retained','passed':True})
        # A regenerated request keeps original history and Controller correction data.
        regenerated=copy.deepcopy(next_body)
        regenerated['messages'].append({'role':'user','content':'Original Controller correction, no replacement action'})
        regenerated_reply='<action>{"type":"scroll","direction":"up"}</action>'
        history.record_actual_reply(regenerated,regenerated_reply)
        prior=copy.deepcopy(history.messages)
        try:
            history.commit_accepted({'status':'accepted','candidate':'edited output','observation_id':'second'})
        except HistoryBindingError:
            pass
        else:
            raise AssertionError('Edited accepted output allowed')
        assert history.messages==prior
        history.commit_accepted({'status':'accepted','candidate':regenerated_reply,'observation_id':'second'})
        assert history.messages==regenerated['messages'][1:]+[{'role':'assistant','content':regenerated_reply}]
        checks.append({'arm_auxiliary':auxiliary,'case':'actual_regenerated_request_correction_and_unedited_reply_retained','passed':True})
        broken=copy.deepcopy(regenerated)
        broken['messages'][1]={'role':'user','content':'Previous observation request.'}
        try:
            history.record_actual_reply(broken,'reply')
        except HistoryBindingError:
            pass
        else:
            raise AssertionError('Earlier image replaced by placeholder allowed')
        checks.append({'arm_auxiliary':auxiliary,'case':'placeholder_or_removed_original_history_rejected','passed':True})
    out=HERE/('CPU-boundary-checks-'+str(time.time_ns()));out.mkdir()
    result={'time':time.time(),'passed':True,'checks':checks,'count':len(checks),
            'source_sha256':hashlib.sha256((HERE/'complete_actor_history.py').read_bytes()).hexdigest(),
            'new_model_GPU_GUI_scorer_calls':0,
            'runtime_integration_or_long_history_capacity_established':False,
            'original_within_decision_recovery_not_replaced_by_test':True}
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'seal.json').write_text(json.dumps({q.name:hashlib.sha256(q.read_bytes()).hexdigest()for q in out.iterdir()if q.is_file()},indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':str(out),'receipt_sha256':hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest(),'passed':True,'checks':len(checks)}))


if __name__=='__main__':
    main()
