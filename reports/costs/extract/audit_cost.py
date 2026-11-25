"""Build a reviewer-safe cost extract strictly from the manuscript's frozen experiments."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
from statistics import median
from math import comb
import csv, io, json
from struct import pack

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
CMP = ROOT / 'jev-defense-four-gpu-20261106/binary-gate-comparison-20261112'
EV = ROOT / 'reports/jev-gui-paired-20261122/evaluation'
LED = EV / 'ledgers/1795515204676783100'
MET = EV / 'reports/1795515294228399000'
GATE = EV / 'gate-cycle-audits/1795518173533348800'
PANEL = ROOT / 'reports/jev-defense-scale-20261122'

def digest(raw): return sha256(raw).hexdigest()
def read(path): return json.loads(path.read_bytes())
def bound(root, seal, name, csv_file=False):
    raw=(root/name).read_bytes()
    assert digest(raw)==seal[name],name
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))) if csv_file else json.loads(raw)

def main():
    src = {}; selection = []; admissions=[]; panel_calls=[]; clean=[]
    cseal = read(CMP/'delivery-seal.json')
    sel = bound(CMP,cseal,'comparison-summary.json')
    assert sel['candidate_by_predeclared_rule']=='neohorse'
    assert digest((CMP/'protocol.json').read_bytes())==sel['protocol_sha256']
    assert digest((CMP/'PRIVATE-labels-pre-output.json').read_bytes())==sel['pre_output_labels_sha256']
    raw=bound(CMP,cseal,'case-results.csv',True)
    for key,m in sel['models'].items():
        rr=[r for r in raw if r['model']==key]
        assert len(rr)==18 and {r['case_id'] for r in rr}=={r['case_id'] for r in raw}
        no=[r for r in rr if r['expected']=='NO']; yes=[r for r in rr if r['expected']=='YES']
        assert len(no)==m['unusable_n']==6 and len(yes)==m['usable_n']==10
        assert sum(r['answer']=='YES' for r in no)==m['false_allow_unusable']
        assert sum(r['answer']=='NO' for r in yes)==m['false_reject_usable']
        assert median(float(r['seconds_with_input_audit']) for r in rr)==m['median_audited_call_seconds']
        assert max(int(r['peak_allocated_bytes']) for r in rr)==m['max_peak_allocated_bytes']
        selection.extend({k:r[k] for k in ('model','case_id','expected','answer','seconds_with_input_audit','peak_allocated_bytes')} for r in rr)
    src['selection_seal']=digest((CMP/'delivery-seal.json').read_bytes())
    g=bound(GATE,read(GATE/'seal.json'),'gate-cycles.json')
    assert digest((LED/'seal.json').read_bytes())==g['ledger_seal_sha256']
    assert digest((MET/'seal.json').read_bytes())==g['metrics_seal_sha256']
    led=bound(LED,read(LED/'seal.json'),'private-linked.json')
    pairs=bound(MET,read(MET/'seal.json'),'paired-metrics.json')
    mc=bound(MET,read(MET/'seal.json'),'condition-by-version.json')
    receipts={}
    for stage,rec in led['collections'].items():
        root=Path(rec['path']); assert digest((root/'seal.json').read_bytes())==rec['seal_sha256']
        allflash=bound(root,read(root/'seal.json'),stage+'.json')['hosts']['3090']['flash']
        for request,x in allflash.items():
            assert request not in receipts
            receipts[request]=x
    by_run={r['slot']['run_id']:r for r in led['rows']}; used=set()
    for run,r in by_run.items():
        ev=r.get('evidence')
        if not ev:continue
        for step in ev['steps']:
            for h in step['gates']:
                if h['event']=='main_image_forwarded': assert h['extra_auxiliary_text_in_main_prompt'] is False
                if h['event']!='gate_decision':continue
                req=h['request_id'];f=receipts[req];assert req not in used
                assert r['slot']['gate_enabled'] and (f['run'],f['image_sha256'],f['seal_sha256'],f['decision'])==(run,h['image_sha256'],h['Flash_seal_sha256'],h['decision'])
                used.add(req)
                admissions.append({'version':r['version'],'condition':r['slot']['condition'],'input_tokens':f['input_tokens']})
    assert used==set(receipts) and len(used)==sum(x['n'] for x in g['actual_Flash_verdicts'])==394
    assert {x['input_tokens'] for x in admissions}=={1174}
    src['full_task_ledger_seal']=g['ledger_seal_sha256'];src['full_task_metrics_seal']=g['metrics_seal_sha256']
    for q in pairs:
        if not(q['both_officially_scored'] and q['condition']=='clean_control'):continue
        item={'task':q['task_id'],'version':q['version']}
        for arm in ('off','on'):
            v=by_run[q[arm]]['evidence']; t=v['terminal'];steps=v['steps']
            checks=[a for z in steps for a in z['gates'] if a['event']=='gate_decision']
            item[arm]={'elapsed_ns':t['elapsed_monotonic_ns'],'score':t['official_reward'],
                       'actor_input':sum(z['main']['input_tokens'] for z in steps),'actor_output':sum(z['main']['output_tokens'] for z in steps),
                       'actor_calls':t['actor_calls'],'flash_input':sum(receipts[a['request_id']]['input_tokens'] for a in checks)}
            assert all(z['main']['actual_forward'] for z in steps)
        assert (item['on']['elapsed_ns']-item['off']['elapsed_ns'])/1e9==q['elapsed_difference_seconds']
        clean.append(item)
    clock=next(z for z in mc['separate_version_condition_results'] if z['version']=='NF4' and z['condition']=='clean_control')
    nf4=[r for r in clean if r['version']=='NF4']
    assert len(nf4)==clock['paired']['official_comparable_pairs']==4
    clocks={k:clock[k]['first_normal_frame_to_actor_submit_seconds'] for k in ('off','on')}
    pct=[(v['on']['elapsed_ns']-v['off']['elapsed_ns'])/v['off']['elapsed_ns']*100 for v in nf4]
    deltas=[(v['on']['elapsed_ns']-v['off']['elapsed_ns'])/1e9 for v in nf4]
    assert median(deltas)==clock['paired']['elapsed_seconds_on_minus_off_task_pairs']['p50']
    assert all(v['on']['actor_input']==v['off']['actor_input'] and v['on']['score']==v['off']['score'] for v in nf4)
    result=read(PANEL/'completion-receipt.json')
    run=PANEL/'attempts'/result['attempt'];seal=bound(PANEL,result['files_sha256'],'attempts/'+result['attempt']+'/local-seal.json')
    audited=bound(PANEL,result['files_sha256'],'逐条独立审计.json')
    src['temporal_completion_receipt']=digest((PANEL/'completion-receipt.json').read_bytes())
    config=read(ROOT/'jev-defense-validation-20261103/model-research-finalists/1793970930004290200/perplexity-ai--pplx-decider-flash-v1.2--config.json')
    image_id=config['image_token_id'];lengths=Counter();ids=set()
    for episode in audited['episodes']:
        rr=bound(run,seal,'run/episodes/'+episode['id']+'/terminal.json')
        for call in rr['flash']:
            req=call['request_id'];assert req not in ids;ids.add(req)
            prefix='run/flash/'+req+'/'
            s=bound(run,seal,prefix+'result.json');f=bound(run,seal,prefix+'actual-forward.json')
            assert req==s['request_id'] and call['forward_sha256']==s['forward_sha256']==seal[prefix+'actual-forward.json']
            assert s['kind']==call['kind'] and s['native_seconds_with_trace']==call['native_seconds']
            assert s['ordered_images']==call['images'] and f['past_key_values'] is None and f['use_cache'] is False
            tensors,=f['tensors_per_forward'];t=tensors['input_ids'];tokens,=t['values']
            assert t['shape']==[1,len(tokens)] and digest(pack('<'+'q'*len(tokens),*tokens))==t['sha256']
            usage=s['native_result']['usage']
            assert usage=={'input_tokens':len(tokens),'output_tokens':0,'sequences':1}
            assert tensors['image_grid_thw']['values']==[[1,44,80]]*len(call['images'])
            assert tokens.count(image_id)==len(call['images'])*880
            elapsed=(call['finished_ns']-call['started_ns'])/1e9;assert elapsed==call['roundtrip_seconds']
            stage=s['kind'];lengths[stage]+=1
            panel_calls.append({'mode':stage,'input_tokens':len(tokens),'image_positions':tokens.count(image_id),
                                'generated_tokens':0,'instrumented_s':s['native_seconds_with_trace'],'roundtrip_s':elapsed})
    assert all(lengths[k]==result['model_calls'][k] for k in ['quality','temporal'])
    p=PANEL/'attempts'/result['attempt']
    assert set(ids)=={f.parent.name for f in (p/'run/flash').glob('*/result.json')}
    recovered=[q for q in audited['pairs'] if q['both_first_early_confirmed'] and q['defense_loop_recovered']]
    assert round(median(q['gate_seconds_defense']-q['gate_seconds_original'] for q in recovered),2)==6.73
    canon={'selection':selection,'full_task_gate_usage':admissions,'completed_clean_pairs':clean,
           'clean_nf4_submission_seconds':clocks,'browser_gate_calls':panel_calls}
    (BASE/'review-cost-data.json').write_text(json.dumps(canon,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
    nonzero=[v for v in deltas if v!=0];k=min(sum(v>0 for v in nonzero),sum(v<0 for v in nonzero))
    summary={'source_bindings':src,'clean_nf4':{'wall_s_median':median(deltas),'wall_s_range':[min(deltas),max(deltas)],
             'paired_slowdown_pct_median':median(pct),'paired_slowdown_pct_range':[min(pct),max(pct)],'decision_clock':clocks,
             'two_sided_exact_sign_p':min(1,2*sum(comb(len(nonzero),i) for i in range(k+1))/2**len(nonzero)),
             'pairs':nf4},'full_task_flash_total':sum(r['input_tokens'] for r in admissions),'browser':{}}
    for kind in lengths:
        rr=[r for r in panel_calls if r['mode']==kind];lens=[r['input_tokens'] for r in rr]
        summary['browser'][kind]={'n':len(rr),'tokens':[min(lens),median(lens),max(lens)],'total':sum(lens),
            'native_s_p50':median(r['instrumented_s'] for r in rr),'roundtrip_s_p50':median(r['roundtrip_s'] for r in rr)}
    (BASE/'verified.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'browser':summary['browser'],'full_task_inputs':summary['full_task_flash_total'],'wall_s':median(deltas),'relative_pct':median(pct)}))
if __name__=='__main__':main()
