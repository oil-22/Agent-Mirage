import collections,hashlib,json,pathlib
from response_view import view
root=pathlib.Path('/home/researcher/attention-20261031');rows=[];seen={}
for model in ['qwen27','qwen9','glm']:
    for prefix,total in [('',324),('source-',33)]:
        folder=root/(prefix+model)
        if prefix and model=='qwen27':continue
        status=json.loads((folder/'status.json').read_text()) if (folder/'status.json').exists() else {}
        rr=json.loads((folder/'results.json').read_text()) if (folder/'results.json').exists() else []
        valid=[];errors=[];captures=[]
        for r in rr:
            if r['status']!='completed':errors.append(r);continue
            original=r.get('reused_from',r['id']);casefolder=folder/original
            artifact=casefolder/'attention.npz';key=str(artifact)
            if key not in seen:
                h=hashlib.sha256()
                with artifact.open('rb') as f:
                    while chunk:=f.read(8*1024*1024):h.update(chunk)
                seen[key]=h.hexdigest()
            assert seen[key]==r['attention_sha256'],str(artifact)
            saved=json.loads((casefolder/'input.json').read_text());assert len(saved['input_ids'])==r['input_tokens'];assert len(saved['groups'])==r['input_tokens'];assert len(saved['turns'])==r['input_tokens']
            v=view(r,folder,model);valid.append(v)
            if r.get('capture_validation') and not r.get('reused_from'):captures.append({'id':r['id'],**r['capture_validation']})
        rows.append({'model':prefix+model,'expected':total,'status':status,'logical_completed':len(valid),'unique_requests':len({r['request_sha256'] for r in valid}),'reused':sum(bool(r.get('reused_from')) for r in valid),'single_reply_eos':sum(r['eos_reached'] for r in valid),'single_reply_truncated_ids':[r['id'] for r in valid if r['truncated']],'raw_overgenerated_ids':[r['id'] for r in valid if r['discarded_after_reply_tokens']],'raw_overgenerated_tokens':sum(r['discarded_after_reply_tokens'] for r in valid),'max_attention_mass_error':max((r['mass_conservation_max_error'] for r in valid),default=None),'independent_preflight_checks':captures,'failed':errors,'all_inputs_and_tensor_hashes_verified':True})
(root/'analysis/terminal-audit.json').write_text(json.dumps({'batches':rows,'unique_tensor_files_hashed':len(seen)},indent=2))
print(json.dumps([{k:v for k,v in r.items() if k not in ['failed','independent_preflight_checks']} for r in rows]))
