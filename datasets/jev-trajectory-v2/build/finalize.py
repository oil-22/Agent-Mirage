"""Build the optional training view, check the actual records & native encoder, then package."""
from common import *
from collections import Counter,defaultdict
from archive_files import WORK as OLDWORK,BLOB,content_id
from join_archive import bystep,okscreen
from temporal_request import native_request,STATE
import base64,zipfile,shutil
sys.path.insert(0,str(HERE))
from verify import check

def views():
    m=list(lines(HERE/'manifest.jsonl'));tt=[r for r in m if r['split']=='train'];tr=list(lines(HERE/'train.jsonl'))
    lookup={r['sample_id']:v for r,v in zip(tt,tr)}
    yes=[r for r in tt if r['label']=='YES'];no=[r for r in tt if r['label']=='NO']
    no.sort(key=lambda r:(r['origin']=='constructed' and r['evidence_kind']=='before_replay',sha(('balanced-v2/'+r['sample_id']).encode())))
    assert len(no)>=len(yes)
    selected={r['sample_id'] for r in yes+no[:len(yes)]};writel(HERE/'train-balanced.jsonl',(lookup[r['sample_id']] for r in tt if r['sample_id'] in selected))
    idx=load(WORK/'spotcheck-index.json');aud={r['sample_id']:r for r in lines(HERE/'audit.jsonl')}
    wrong=next(r['sample_id'] for r in idx if r['method']=='different_typed_value');parent=aud[wrong]['evidence']['parent_sample_id']
    writel(HERE/'example-typed-contrast.jsonl',[lookup[parent],lookup[wrong]])
    writej(HERE/'spot-check.json',dict(method='Model-assisted visual reading of real screenshots, 3 fixed hash-ranked new examples per represented evidence rule. No human adjudication or model scoring claimed.',count=len(idx),sample_ids=idx,observations={'before_replay':'The clicked listing or pagination control remains in the source state; the matched normal frame shows the destination.','delivered_blank':'All three delivered candidates are white and contain neither target nor feedback.','delivered_partial':'The surviving buttons do not show the clicked listing, typed field value, or new focus ring.','delivered_stale':'The pre-scroll listings are repeated; the corresponding normal capture shows a different viewport.','different_typed_value':'The actual requested and alternative field values are legible in the original images.','directional_scroll':'Shared content and lower landmarks show the requested displacement.','earlier_same_page':'The earlier page still shows the search or list, with a different local field value.','earlier_unchanged_field':'The targeted input remains empty or unfocused.','rendered_navigation':'The clicked pagination, search or sort control is reflected in the new results.','visible_browser_scroll':'The requested scroll advances through results or returns to the page header.','visible_focus_ring':'A distinct focus outline appears around the dispatched click.','visible_scroll_boundary':'The complete contact/copyright footer remains visible at the bottom.','visible_typed_text':'The three dispatched text values appear in the corresponding fields.'}))
    print('balanced',len(selected),'example',parent,wrong)
def origin_checks():
    m=list(lines(HERE/'manifest.jsonl'));auds={r['sample_id']:r for r in lines(HERE/'audit.jsonl')};nm=load(NAT/'extract.json')
    nats={(r['source_run'],r['step']):r for r in nm['events']};probes={(r['source_run'],r['step'],r['condition'],r['bin']):r for r in nm['probes']}
    observations={oid(r):r for file in ('observations.jsonl','additional-archive-observations.jsonl') for r in lines(V1/file)}
    aliases=load(OLDWORK/'archive-logs-aliases.json')
    @lru_cache(480)
    def archive(run,fn):
        p=BLOB/content_id(aliases[run+'/'+fn]);return bystep(p),sha(p.read_bytes())
    def actual(s,b,a,h,injection=False):
        if s['suite']=='natural_classifieds':
            z=nats[s['source_run'],s['step']]
            assert z['trace_member_sha256']==s['trace_member_sha256'] and z['trace']==s['trace']
            assert z['action']==a and z['before']==s['before'] and z['after']==s['after'] and z['before']['png_sha256']==b
            if injection:
                d=s['probe'];assert probes[s['source_run'],s['step'],d['condition'],d['bin']]==d and d['delivered_sha256']==h and d['normal_sha256']==z['after']['png_sha256']
            else:assert z['after']['png_sha256']==h
        else:
            if not injection:
                z=observations[s['source_observation_id']];assert [z['before_sha256'],z['action'],z['candidate_sha256']]==[b,a,h]
            if s['suite']=='archive_vwa':
                step=s['step'];run=s['source_run'];v={}
                for f in ('action_execution.jsonl','agent_visible_trace.jsonl','model_delivery.jsonl'):
                    x,checksum=archive(run,f);assert s['log_hashes'][f]==checksum;v[f]=x
                ex=v['action_execution.jsonl'][step];x=v['model_delivery.jsonl'][step];y=v['model_delivery.jsonl'][step+1]
                assert ex['success'] is True and not ex['error'] and v['agent_visible_trace.jsonl'][step]['action']==a and okscreen(x)
                assert [x['delivered_sha256'],y['delivered_sha256']]==[b,h] and [x['request_sha256'],y['request_sha256']]==[s['before_request'],s['after_request']]
                if injection:assert y['injection_fired'] is True and y['current_image_blocks']==1 and y['capture_sha256']==s['archived_capture_sha256']
                else:assert okscreen(y)
    def from_donor(s):
        run=s['source_run'];step=s['step'];h=s['hash']
        if s['trajectory_id'].startswith('natural:'):
            z=nats[run,step];assert z['before']['png_sha256']==h and z['before']['input_ids_sha256']==s['receipt'] and z['trace']['before_route']==s['route']
        else:
            x=archive(run,'model_delivery.jsonl')[0][step];assert okscreen(x) and x['delivered_sha256']==h and x['request_sha256']==s['receipt']
    normal=Counter();built=Counter();native=native_messages();protocol=load(HERE/'protocol.json');qs={}
    lookup={r['sample_id']:r for r in m};views={s:iter(lines(HERE/(s+'.jsonl'))) for s in ('train','val','test')}
    for r in m:
        v=next(views[r['split']]);b=r['before_sha256'];e=r['candidate_sha256'];a=r['action'];au=auds[r['sample_id']];ev=au['evidence']
        if a['type'] not in qs:
            i,j=[(HERE/n).read_bytes() for n in v['images']];req=native_request(i,a,j);assert [base64.b64decode(x.split(',')[1]) for x in req['images']]==[i,j]
            qs[a['type']]=req['questions']
        sms=native.messages(dict(images=[0,1],questions=qs[a['type']],state=STATE+'\nDispatched native action (JSON): '+action_json(a)))
        assert sms[0]['content']==protocol['system_prompt'] and sms[1]['content']==[{'type':'image'},{'type':'image'},{'type':'text','text':v['prompt']}]
        if r['pair_observed']:
            src=au.get('source') or ev['source'];actual(src,b,a,e,r['origin']=='observed_injection');normal[r['origin']]+=1
        if r['origin'] in ('constructed','observed_matched'):
            realparent=lookup[ev['parent_sample_id']];src=au['source'] if not r['pair_observed'] else au['donor_sources'][0]
            actual(src,b,a,realparent['candidate_sha256']);don=ev['donor']
            if 'sample_id' in don:
                op=lookup[don['sample_id']];assert op['pair_observed'] and op['split']=='train' and op[('before' if don['role']=='before' else 'candidate')+'_sha256']==don['hash']==e
            else:from_donor(don)
            built[r['evidence_kind']]+=1
    return dict(reference_encoder_rows=len(m),native_request_verified_action_types=sorted(qs),observed_sources_reconciled=dict(normal),constructed_or_matched_sources_reconciled=dict(built),natural_source_extract_sha256=sha((NAT/'extract.json').read_bytes()),natural_completed_source_folders=nm['completed_sources'],natural_joined_action_occurrences=len(nm['events']),natural_linked_probe_occurrences=len(nm['probes']),frozen_archive_log_aliases_sha256=sha((OLDWORK/'archive-logs-aliases.json').read_bytes()))
def report():
    m,stats=check(HERE,report=False);proof=origin_checks()
    writej(HERE/'stats.json',stats)
    hashes={n:sha((HERE/n).read_bytes()) for n in ('train.jsonl','train-balanced.jsonl','val.jsonl','test.jsonl','protocol.json','manifest.jsonl','audit.jsonl','v1-provenance.jsonl','split-guards.json','spot-check.json')}
    writej(HERE/'validation.json',dict(**proof,actual_unique_inputs=len(m),unique_training_inputs=sum(stats['splits']['train'].values()),fully_decoded_input_pngs=stats['model_input_pngs'],additional_evidence_pngs=stats['audit_only_pngs'],protected_originals_and_decoded_identities=stats['regression_images_checked'],cross_split_shared_images=0,cross_split_shared_source_groups=0,conflicting_exported_labels=0,visually_equivalent_input_aliases_in_export=0,frozen_v1_validation_and_test_byte_identical=True,source_selection_diagnostics=load(WORK/'selection-diagnostics.json'),spot_checked_new_rows=load(HERE/'spot-check.json')['count'],file_sha256=hashes))
    print('confirmed',len(m),stats['splits'],proof,flush=True)
def pack():
    p=HERE.parent/'jev-trajectory-v2.zip';members=sorted(n for n in HERE.rglob('*') if n.is_file() and '__pycache__' not in n.parts and n.name not in ('checksums.sha256','bundle.sha256') and n.suffix in ('.py','.md','.json','.jsonl','.png'))
    assert all((HERE/n) in members for n in ('README.md','manifest.jsonl','validation.json','train.jsonl','example-typed-contrast.jsonl'))
    def h(f):
        with f.open('rb') as v:return hashlib.file_digest(v,'sha256').hexdigest()
    checks=HERE/'checksums.sha256';checks.write_bytes(''.join(h(n)+'  '+n.relative_to(HERE).as_posix()+'\n' for n in members).encode())
    members.append(checks)
    with zipfile.ZipFile(p,'w',allowZip64=True) as z:
        for f in members:z.write(f,f.relative_to(HERE).as_posix(),compress_type=zipfile.ZIP_STORED if f.suffix=='.png' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(p) as z:
        assert len(z.namelist())==len(set(z.namelist()))==len(members) and z.testzip() is None
        for line in z.read('checksums.sha256').decode().splitlines():
            hx,n=line.split('  ',1);assert sha(z.read(n))==hx
    dig=h(p);(HERE/'bundle.sha256').write_bytes((dig+'  '+p.name+'\n').encode());print('archive verified',p,len(members),p.stat().st_size,dig,flush=True)
if __name__=='__main__':
    {'views':views,'report':report,'zip':pack}[sys.argv[1]]()
