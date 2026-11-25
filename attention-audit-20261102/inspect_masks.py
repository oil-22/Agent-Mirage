import gzip,json,pathlib,collections
r=pathlib.Path('/data/researcher/attention-audit-20261031');i=r/'inputs'
pp=list(i.glob('attention-experiment/**/crossmodel*/**/paired-*-buttons_only/input-metadata.json'))
print('buttons metadata',len(pp))
for p in pp[:2]:
 d=json.loads(p.read_text());print(p,json.dumps({k:v for k,v in d.items() if k not in ['input_ids','source_turns','input_groups','prompt','decoded_prompt']},ensure_ascii=False)[:4500])
rows=[json.loads(x) for x in gzip.open(r/'members.jsonl.gz','rt')]
selected=[a for a in rows if any(s in a[0].lower() for s in ['buttons-only','buttons_only','intervention']) and a[0].endswith(('.md','.json')) and any(s in a[0] for s in ['config','ledger','manifest','summary','report'])]
print('possible button provenance',len(selected))
for a in selected[-5:]:print(a)
pp=list(i.glob('attention-experiment/_shared/**/corpus/**/002.json'))
c=[]
for p in pp:
 if not (p.parent/'summary_info.json').exists():continue
 d=json.loads(p.read_text());summ=json.loads((p.parent/'summary_info.json').read_text())
 if summ.get('condition') in ['blank_replace','loading_blank','silent_drop']:
  c.append({'trajectory':p.parent.name,'task':summ['task'],'condition':summ['condition'],'steps':summ['n_steps'],'injected':d['injection_fired'],'response':d['original_response'],'ledger':d.get('ledger')})
(r/'expansion-source-candidates.json').write_text(json.dumps(c,ensure_ascii=False,indent=2))
print('source candidates',len(c));print(json.dumps(c[:2],ensure_ascii=False)[:5000])
