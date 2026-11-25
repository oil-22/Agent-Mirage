from ops import HERE,BASE

text=(BASE/'repair-evidence-20261109-01/collect_completed.py').read_text(encoding='utf8')
text=text.replace("list(sorted((r/'worker/auxiliary').iterdir()))+list(sorted((r/'worker/judges').iterdir()))", "list(sorted((r/'worker/auxiliary').iterdir()))")
text=text.replace(" actual=json.loads((folder/'actual-generation.json').read_bytes());cfg=json.loads((folder/'effective-generation.json').read_bytes())", """ actual=json.loads((folder/'actual-generation.json').read_bytes());cfg=json.loads((folder/'effective-generation.json').read_bytes())
 mask=json.loads((folder/'actual-mask-steps.json').read_bytes())
 assert mask['all_actual_selected_tokens_allowed'] and len(mask['steps'])==len(actual['output_ids'])
 assert all(s['selected_allowed']and s['selected_id']==t for s,t in zip(mask['steps'],actual['output_ids']))
 response=json.loads((folder/'response.json').read_bytes())
 assert response['strict_native_UTF8_roundtrip']
 raw_bytes=(folder/'generated-raw-utf8.bin').read_bytes()
 assert raw_bytes.decode('utf8')==response['raw_output']==(folder/'raw-output.txt').read_text()
 assert response['image_sha256']==sha(folder/'original.png')""")
with(HERE/'collect_completed.py').open('x',encoding='utf8')as f:f.write(text)
print('New six-call terminal auditor prepared.')
