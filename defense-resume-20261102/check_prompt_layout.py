import ast,hashlib,itertools,json,pathlib
B=pathlib.Path(__file__).parent;p=B/'restored-release/defense/prompts.py';text=p.read_text(encoding='utf-8');lines=text.splitlines(True);tree=ast.parse(text)
starts=sorted(set([0]+[x.lineno-1 for x in tree.body]));chunks=[''.join(lines[a:b])for a,b in zip(starts,starts[1:]+[len(lines)])]
expected=json.loads((B/'appearance-absence-repair-development/stage-1793275195957987900/source-sha256.json').read_bytes())['release/defense/prompts.py']
for bits in itertools.product([False,True],repeat=len(chunks)):
 data=''.join(c.replace('\n','\r\n')if bit else c for c,bit in zip(chunks,bits)).encode()
 for bom in [b'',b'\xef\xbb\xbf']:
  if hashlib.sha256(bom+data).hexdigest()==expected:
   p.write_bytes(bom+data);(B/'verified-release/defense/prompts.py').write_bytes(bom+data);print('EXACT PROMPTS',bits,bool(bom));raise SystemExit
print('No block layout match; constants require independent service-request binding')
