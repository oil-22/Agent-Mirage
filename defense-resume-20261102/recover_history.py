import io, json, pathlib, zstandard, hashlib

OUT=pathlib.Path(__file__).parent
source=pathlib.Path(r'C:\Users\researcher\.codex\sessions')
keys=['appearance_absence','epistemic','inference_server.py','core.py','prompts.py','HISTORY_REPORT','test_scene_only_readiness','test_history_schema','pagination_count_reason_scope','*** Add File:','*** Update File:']
rows=[]; count=0
for p in sorted(source.rglob('*01a151bb-be3f-74c2-982d-a004f4a51038*')):
    with p.open('rb') as f:
        reader=zstandard.ZstdDecompressor().stream_reader(f) if p.suffix=='.zst' else f
        for i,line in enumerate(io.TextIOWrapper(reader, encoding='utf-8')):
            count+=1
            if not any(k in line for k in keys):continue
            e=json.loads(line); payload=e.get('payload',{})
            if e.get('type')=='response_item' and payload.get('type') in ['function_call','custom_tool_call']:
                rows.append({'source':p.name,'line':i,'timestamp':e.get('timestamp'),'payload':payload})
(OUT/'history-tool-calls.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'lines':count,'calls':len(rows),'bytes':(OUT/'history-tool-calls.json').stat().st_size}))
for j,r in enumerate(rows):
    s=str(r['payload'].get('arguments',r['payload'].get('input','')))
    if 'appearance_absence' in s or ('inference_server.py' in s and ('*** Add File:' in s or '.write_text' in s)):
        print(j,r['timestamp'],r['payload'].get('name'),len(s),s[:120].replace('\n',' '))
