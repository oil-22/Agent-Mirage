import io,json,pathlib,zstandard
B=pathlib.Path(__file__).parent;rows=json.loads((B/'history-tool-calls.json').read_text(encoding='utf-8'))
want={x['payload']['call_id']:x for x in rows if x['timestamp']<'2026-10-30' and 'prompts.py' in x['payload'].get('input',x['payload'].get('arguments','')) and 'apply_patch' in x['payload'].get('input',x['payload'].get('arguments',''))}
out=[]
for p in sorted(pathlib.Path(r'C:\Users\researcher\.codex\sessions').rglob('*01a151bb-be3f-74c2-982d-a004f4a51038*')):
 with p.open('rb')as f:
  reader=zstandard.ZstdDecompressor().stream_reader(f)if p.suffix=='.zst' else f
  for line in io.TextIOWrapper(reader,encoding='utf-8'):
   if 'call_id'not in line:continue
   e=json.loads(line);pl=e.get('payload',{})
   if pl.get('type')not in ['custom_tool_call_output','function_call_output']or pl.get('call_id')not in want:continue
   s=str(pl.get('output',''));src=want[pl['call_id']]
   out.append({'timestamp':src['timestamp'],'call_id':pl['call_id'],'output':s})
(B/'prompt-patch-outcomes.json').write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
for x in out:
 if any(k in x['output'].lower()for k in ['failed to find','invalid patch','error:','iserror']):print(x['timestamp'],x['output'][:2000])
print('outputs',len(out),'wanted',len(want))
