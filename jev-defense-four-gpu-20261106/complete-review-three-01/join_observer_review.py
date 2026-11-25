import json,hashlib
from collections import Counter
from pathlib import Path
p=Path(__file__).parent/'observer-image-review-01'
read=lambda name:json.loads((p/name).read_text(encoding='utf-8'))
seal=read('source-first-visual-seal.json')
for name,sha in seal['files'].items():
    item=p/name if (p/name).exists() else p.parent/name
    assert hashlib.sha256(item.read_bytes()).hexdigest()==sha
notes=read('source-first-visual-review.json'); replies=read('replies.json')
rows=[]
for n,r in zip(notes['rows'],replies):
    assert n['index']==r['index']; body=r['response']; assert n['image_sha256']==body['image_sha256']
    answers=body['answers']; choices={k:v['choice'] for k,v in answers.items()}
    compatible={'frame_appearance':choices['frame_appearance']==n['frame_appearance'],
     'text_readability':choices['text_readability']==n['text_readability'],
     'visible_layout':choices['visible_layout'] in n['compatible_layouts']}
    rows.append({'index':n['index'],'image_sha256':n['image_sha256'],'choices':choices,'compatible':compatible,
      'probability_of_selected':{k:v['probabilities'][v['choice']] for k,v in answers.items()},
      'input_tokens':body['native_result']['usage']['input_tokens'],
      'seconds':body.get('seconds'),'per_device_memory':body['per_device_memory'],
      'meaning':'Compatibility of three coarse categories with sealed source-first notes, not task evidence or Mirage gold.'})
out={'count':20,'source_first_seal_sha256':hashlib.sha256((p/'source-first-visual-seal.json').read_bytes()).hexdigest(),
 'replies_sha256':hashlib.sha256((p/'replies.json').read_bytes()).hexdigest(),
 'compatible_counts':{k:sum(r['compatible'][k] for r in rows) for k in rows[0]['compatible']},
 'choice_counts':{k:dict(Counter(r['choices'][k] for r in rows)) for k in rows[0]['choices']},
 'input_tokens':sum(r['input_tokens'] for r in rows),'generation_tokens':sum(r['response']['generation_tokens'] for r in replies),
 'seconds_sum_if_present':sum(r['seconds'] or 0 for r in rows),
 'limitations':['All20 are selected coherent readable GUI frames from one trajectory, not negative/loading controls or general accuracy.',
 'Mixed layouts use accepted sets; no calibrated threshold or semantic success claim.',
 'No page/focus/clothing/price/coordinate/freshness/history/exhaustive-coverage result is supplied by these questions.'], 'rows':rows}
dest=p/'prediction-join-review.json'; assert not dest.exists(); dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ss=p/'prediction-join-seal.json'; assert not ss.exists(); ss.write_text(json.dumps({'files':{'prediction-join-review.json':hashlib.sha256(dest.read_bytes()).hexdigest(),
 Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}},indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='rows'},ensure_ascii=False,indent=2))
for row in rows:print(json.dumps({k:row[k] for k in ('index','choices','compatible','probability_of_selected','seconds')},ensure_ascii=False))
