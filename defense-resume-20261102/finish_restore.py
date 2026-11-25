import ast,hashlib,itertools,json,pathlib,re,shutil,sys
B=pathlib.Path(__file__).parent;R=B/'restored-release'
M=json.loads((B/'appearance-absence-repair-development/stage-1793275195957987900/source-sha256.json').read_bytes())
rows=json.loads((B/'history-tool-calls.json').read_text(encoding='utf-8'));dec=json.JSONDecoder()

# Replay only the known historical fixture string edits, never their shell commands.
for x in rows:
 if x['timestamp']!='2026-10-25T07:42:38.439Z':continue
 s=x['payload']['input'];m=re.search(r'cmd\s*:\s*',s);cmd,_=dec.raw_decode(s[m.end():]);src=cmd.split("@'\n",1)[1].split("\n'@",1)[0]
 tree=ast.parse(src)
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='Path':
   node.args=[ast.Constant(str(R/node.args[0].value))]
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ['read_text','write_text']:
   node.keywords.append(ast.keyword(arg='encoding',value=ast.Constant('utf-8')))
 exec(compile(ast.fix_missing_locations(tree),'historical-fixture-restore','exec'),{})

p=R/'test_scene_only_readiness.py';p.write_text(p.read_text(encoding='utf-8').replace('Journal(Path(t))',"Journal(Path(t)/'journal')"),encoding='utf-8',newline='\n')
p=R/'test_pagination_count_reason_scope.py';s=p.read_text(encoding='utf-8').replace("for reason in ['There might be more pages beyond the shown buttons.', 'The total count is unknown.', 'Unknown total number of pages.']:","for reason, expected in [('There might be more pages beyond the shown buttons.', True), ('The total count is unknown.', False), ('Unknown total number of pages.', True)]:").replace("result = pagination_count_reason_check(self.row(reason=reason))", "result = pagination_count_reason_check(self.row(reason=reason))\n            self.assertEqual(result['reject'], expected)");p.write_text(s,encoding='utf-8',newline='\n')

# Some historical PowerShell edits introduced blank-line layout. Only search text-
# equivalent layout; a hash match is required to call a byte restoration exact.
for name in ['defense/prompts.py','test_pagination_count_reason_scope.py','test_scene_only_readiness.py','tests/test_history_report_probe.py','tests/test_history_schema.py']:
 p=R/name;raw=p.read_bytes();h=M['release/'+name]
 if hashlib.sha256(raw).hexdigest()==h:print('EXACT',name);continue
 text=raw.decode('utf-8');lines=text.splitlines(True);found=None
 for i in range(len(lines)+1):
  for op in ['add','remove']:
   if op=='remove' and (i==len(lines)or lines[i].strip()):continue
   trial=''.join(lines[:i]+(['\n']+lines[i:] if op=='add'else lines[i+1:]))
   for nl in ['\n','\r\n']:
    for bom in ['','\ufeff']:
     data=(bom+trial.replace('\r\n','\n').replace('\n',nl)).encode('utf-8')
     if hashlib.sha256(data).hexdigest()==h:found=data;break
 if found is not None:p.write_bytes(found);print('EXACT LAYOUT',name)
 else:print('UNRESOLVED',name)

test=R/'test_price_history_controller.py';s=test.read_text(encoding='utf-8').replace('from price_history_binding import check_price_history','from price_history_frame_binding import check_price_history').replace("a['frozen_sha256'],b['frozen_sha256']","a['frozen_records_sha256'],b['frozen_records_sha256']");(R/'test_price_frame_controller.py').write_text(s,encoding='utf-8',newline='\n')

root=B/'verified-release';root.mkdir(exist_ok=True)
checks=[]
for name,h in M.items():
 if not name.startswith('release/'):continue
 p=R/name[8:]
 if p.exists():
  actual=hashlib.sha256(p.read_bytes()).hexdigest();checks.append({'path':name[8:],'expected':h,'actual':actual,'exact':actual==h})
  target=root/name[8:];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(B/'source-restoration-verification.json').write_text(json.dumps(checks,indent=2))
print('Exact source files',sum(x['exact']for x in checks),'/',len(checks))
