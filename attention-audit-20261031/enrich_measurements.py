"""CPU-only extraction of token-query and layer summaries from frozen captures."""
import hashlib,json,pathlib
import numpy as np
from transformers import AutoTokenizer
from action_audit import action_spans,audit_action
from response_view import view

root=pathlib.Path('/home/researcher/attention-20261031');out=root/'analysis';out.mkdir(exist_ok=True)
models={'qwen27':'/opt/whz/llms/Qwen3.8-27B','qwen9':'/home/researcher/models/Qwen3.5-9B','glm':'/home/researcher/models/GLM-4.6V-Flash-411bb4d77144'}
cachepath=out/'query-cache.json';cache=json.loads(cachepath.read_text()) if cachepath.exists() else {}
rows=[];source_rows=[]
for model,path in models.items():
    tokenizer=None
    for prefix in ['', 'source-']:
        folder=root/(prefix+model)
        if not (folder/'results.json').exists():continue
        for r in json.loads((folder/'results.json').read_text()):
            if r['status']!='completed':continue
            r=view(r,folder,model)
            key='v3:'+model+':'+r['attention_sha256']+':'+str(r['output_tokens'])
            if key not in cache:
                if tokenizer is None:tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
                raw=tokenizer.decode(r['output_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                encoded=tokenizer(raw,add_special_tokens=False,return_offsets_mapping=True)
                exact=encoded['input_ids']==r['output_ids']
                offsets=encoded['offset_mapping'] if exact else None
                if offsets is None:
                    prefixes=[tokenizer.decode(r['output_ids'][:i],skip_special_tokens=False,clean_up_tokenization_spaces=False) for i in range(len(r['output_ids'])+1)]
                    if all(raw.startswith(p) for p in prefixes) and all(len(a)<=len(b) for a,b in zip(prefixes,prefixes[1:])):
                        offsets=[(len(a),len(b)) for a,b in zip(prefixes,prefixes[1:])]
                spans=action_spans(raw);indices=[]
                if len(spans)==1 and offsets is not None:
                    start,end,_=spans[0]
                    indices=[i for i,(a,b) in enumerate(offsets) if a<end and b>start and r['output_ids'][i] not in tokenizer.all_special_ids]
                # Ambiguous actions have no action-query average, not zero mass.
                others=[i for i in range(len(r['output_ids'])) if i not in indices and r['output_ids'][i] not in tokenizer.all_special_ids]
                artifact=np.load(folder/r.get('reused_from',r['id'])/'attention.npz')
                mass=artifact['mass'][:r['output_tokens']];layers=artifact['layers'].tolist()
                data={'query_groups_exactly_reencoded':exact,'query_character_offsets_exact':offsets is not None,'action_query_count':len(indices),'non_action_query_count':len(others),'layers':layers,
                      'first_query_mass':mass[0].mean(axis=(0,1)).tolist(),'first_query_layer_mass':mass[0].mean(axis=1).tolist(),
                      'all_query_layer_mass':mass.mean(axis=(0,2)).tolist(),
                      'first_query_head_mass':mass[0].tolist(),
                      'action_query_mass':mass[indices].mean(axis=(0,1,2)).tolist() if indices else None,
                      'action_query_layer_mass':mass[indices].mean(axis=(0,2)).tolist() if indices else None,
                      'non_action_query_mass':mass[others].mean(axis=(0,1,2)).tolist() if others else None}
                if 'source_mass' in artifact:
                    sm=artifact['source_mass'][:r['output_tokens']]
                    data.update(source_mass=sm.mean(axis=(0,1,2)).tolist(),first_query_source_mass=sm[0].mean(axis=(0,1)).tolist(),
                                action_query_source_mass=sm[indices].mean(axis=(0,1,2)).tolist() if indices else None,
                                source_layer_mass=sm.mean(axis=(0,2)).tolist(),
                                action_query_source_layer_mass=sm[indices].mean(axis=(0,2)).tolist() if indices else None)
                cache[key]=data
            row={k:r[k] for k in ['id','task','app','stage','step','history','condition','input_tokens','output_tokens','eos_reached','truncated']}
            row.update(model=model,**audit_action(r['output']),**cache[key])
            (source_rows if prefix else rows).append(row)
    cachepath.write_text(json.dumps(cache))
(out/'query-measurements.json').write_text(json.dumps(rows))
(out/'source-query-measurements.json').write_text(json.dumps(source_rows))
print(json.dumps({'main_rows':len(rows),'source_rows':len(source_rows),'unique_tensors_processed':len(cache)}))
