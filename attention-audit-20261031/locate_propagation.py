import gzip,json,pathlib
root=pathlib.Path('/data/researcher/attention-audit-20261031')
rows=[json.loads(s) for s in gzip.open(root/'members.jsonl.gz','rt')]
for name,size,typ,link in rows:
    if '/qwen27-propagation-20261020/' in name and name.endswith('.json'):
        print(name,size,typ,link)
print('calendar')
base=root/'inputs/mirage-trace/Qwen3.5-9B/AndroidWorld__blank_replace/androidworld-uitars7-2026-10-15/qwen35-9b-full-20261019/001-SimpleCalendarEventOnDateAtTime/blank_replace/requests'
for step in [2,3,5,7]:
    p=base/f'{step:03d}-response.json'
    if p.exists():print(step,p.read_text()[:1500])
