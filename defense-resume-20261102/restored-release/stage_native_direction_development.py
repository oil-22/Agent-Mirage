"""Freeze an isolated guard-integrated Controller and NEW public input prefixes."""
import ast
import copy
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from native_direction_consistency import check_direction


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def parse(text):
    matches=re.findall(r'<action>(.*?)</action>',text,re.DOTALL)
    assert len(matches)==1
    p=json.loads(matches[0]);return {'name':p['type'],'parsed':True,'executor_fallback_wait':False,'payload':p,'coordinate_space':'normalized_1000'}
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')


def build():
    root=BASE/'native-direction-development'/str(time.time_ns());release=root/'release'
    release.mkdir(parents=True);shutil.copytree(BASE/'defense',release/'defense',ignore=shutil.ignore_patterns('__pycache__'))
    for n in ['native_direction_consistency.py','native-vwa-request.json']:
        shutil.copy2(BASE/n,release/n)
    original=(release/'defense/core.py').read_text(encoding='utf-8')
    changed=original.replace('from .schema import KINDS','from .schema import KINDS\nfrom native_direction_consistency import check_direction')
    needle='            point_reason=None;point_needs_evidence=False;focus_reason=None'
    assert original.count(needle)==1
    changed=changed.replace(needle,needle+"\n            direction_check=check_direction(candidate,proposal)\n            self.log.append('native_direction_consistency',direction_check)\n            direction_reason=direction_check['reason']if direction_check['reject']else None")
    needle="            action_bad=verdict['action']['status']!='supported'or point_reason is not None or focus_reason is not None"
    assert original.count(needle)==1
    changed=changed.replace(needle,needle+' or direction_reason is not None')
    needle="completion_reason or point_reason or focus_reason or verdict['action']['reason']"
    assert original.count(needle)==1
    changed=changed.replace(needle,"completion_reason or direction_reason or point_reason or focus_reason or verdict['action']['reason']")
    (release/'defense/core.py').write_text(changed,encoding='utf-8')
    # Validators, pure-WAIT classification, recovery limits and actor/verifier caps untouched.
    def functions(text):
        return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    old,new=functions(original),functions(changed)
    for name in old:
        if name!='Controller':assert old[name]==new[name],name
    packet_dir=Path(json.loads((BASE/'semantic-review-packets-current.json').read_bytes())['directory'])
    used=set()
    for sub in ['source-evidence-preview-development','history-carryover-development','carryover-routing-real-development']:
        for p in (BASE/sub).rglob('inputs/*.json'):
            try:
                x=json.loads(p.read_bytes());pub=x.get('public')
                if pub:used.add(sha(canon(pub['messages'])))
            except (OSError,ValueError):pass
    candidates=[];offline=[]
    for p in sorted((packet_dir/'packets').glob('*/*.json')):
        x=json.loads(p.read_bytes());pub=x['public'];text=x['candidate']
        try:proposal=parse(text)
        except Exception:continue
        result=check_direction(text,proposal)
        offline.append({'packet':str(p),'packet_sha256':sha(p.read_bytes()),'candidate_sha256':sha(text.encode()),
                        'proposal':proposal,'check':result})
        sig=sha(canon(pub['messages']))
        if sig not in used and len(pub['messages'])>=4:
            candidates.append((p,x,sig,result))
    # Selected development strata; no inference worker sees archived candidate or private expectations.
    chosen=[];seen=set(used)
    for category in ['explicit_internal_direction_conflict','recognized_consistent','ambiguous_or_unrecognized_intent','not_scroll']:
        for p,x,sig,r in candidates:
            if r['status']==category and sig not in seen:
                chosen.append((p,x,sig,r));seen.add(sig);break
    assert len(chosen)==4,{c:sum(r['status']==c for _,_,_,r in candidates)for c in set(r['status']for *_,r in candidates)}
    (root/'inputs').mkdir();(root/'images').mkdir();(root/'PRIVATE-source-controls').mkdir()
    cases=[]
    for i,(p,x,sig,r)in enumerate(chosen,1):
        name='n%02d'%i;public=copy.deepcopy(x['public'])
        # Public packet carries full history/current image; original candidate withheld from worker.
        source_packet=sha(p.read_bytes());f=root/'inputs'/(name+'.json');save(f,{'public':public})
        for im in public['images']:
            src=packet_dir/'images'/(im['sha256']+'.png');assert sha(src.read_bytes())==im['sha256'];shutil.copy2(src,root/'images'/src.name)
        save(root/'PRIVATE-source-controls'/(name+'.json'),{'original_packet':str(p),'original_packet_sha256':source_packet,
             'archived_candidate':x['candidate'],'original_candidate_check':r,'new_model_candidate_expected':None})
        cases.append({'id':name,'packet':'inputs/'+f.name,'packet_sha256':sha(f.read_bytes()),
                      'native_messages_sha256':sig,'source_packet_sha256':source_packet,
                      'images':[im['sha256']for im in public['images']]})
    save(root/'offline-proposal-audit.json',{'scope':'Known nonblind archival engineering replay, not new semantic controls or efficacy',
         'model_calls':0,'gui_actions':0,'rows':offline,
         'counts':{k:sum(r['check']['status']==k for r in offline)for k in sorted({r['check']['status']for r in offline})}})
    plan={'cases':cases,'scope':'Four distinct complete native public prefixes, selected nonblind one-task development. Original archived candidates/private strata not supplied to worker.',
          'new_feedback_condition':'proposal-internal explicit direction guard after ORIGINAL strict verifier, within original recovery budget',
          'max_calls':24,'max_actor_calls':70,'max_verifier_calls':140,'max_regenerations':2,'max_recaptures':2,'max_format_retries':1,
          'actor_max_tokens':2048,'judge_max_tokens':4096,'new_gui_actions':0,'formal_trial':False,
          'fake_live_recapture_allowed':False,'previous_completed_controls_reexecuted':False,
          'new_real_wait_control_available':False,'wait_scope':'Only original archival/synthetic CPU exclusion tests; no new real WAIT pass claimed',
          'source_body_hashes_excluded':sorted(used),'validators_and_limits_ast_unchanged':True}
    save(root/'plan.json',plan)
    save(root/'original-core-sha256.json',{'original_sha256':sha(original.encode()),'development_sha256':sha(changed.encode()),'only_Controller_extension_changed':True})
    save(root/'source-sha256.json',{str(p.relative_to(root)):sha(p.read_bytes())for p in root.rglob('*')if p.is_file()})
    receipt={'directory':str(root),'release':str(release),'cases':cases,'max_calls':24,'formal_release':False,'new_model_calls':0,
             'offline_counts':json.loads((root/'offline-proposal-audit.json').read_bytes())['counts']}
    save(BASE/'native-direction-development/current.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':build()
