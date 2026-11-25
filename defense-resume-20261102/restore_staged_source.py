"""Restore only recorded pure source-string transformations into a separate release."""
import hashlib,json,pathlib,shutil,textwrap
B=pathlib.Path(__file__).parent
R=B/'restored-release';shutil.copytree(B/'recovered-patches',R,dirs_exist_ok=True)
M=json.loads((B/'appearance-absence-repair-development/stage-1793275195957987900/source-sha256.json').read_bytes())

# core must start at the original source, not its still-unrestored staged version.
(R/'defense/core.py').write_bytes((B/'recovered-patches/defense/core.py').read_bytes())
sequence=[
 ('stage_native_direction_development',31,42),
 ('stage_native_direction_feedback_origin',11,18),
 ('stage_scoped_observability',11,35),
 ('stage_scoped_fullgui_preflight',12,13),
 ('stage_focus_history_repair',11,19),
 ('stage_focus_readiness_supplement',18,37),
 ('stage_focus_conflict_repair',13,45),
 ('stage_focus_conflict_typing_edge',17,21),
 ('stage_plan_present_report_repair',18,23),
 ('stage_price_history_repair',13,36),
 ('stage_price_frame_repair',14,17),
 ('stage_pagination_count_repair',21,34),
 ('stage_strict_price_repair',21,48),
 ('stage_completion_source_repair',19,35),
 ('stage_scene_only_repair',15,21),
]
audit=[]
for name,start,end in sequence:
 lines=(B/'recovered-patches'/(name+'.py')).read_text(encoding='utf-8').splitlines()
 code=textwrap.dedent('\n'.join(lines[start-1:end]))
 try:exec(compile(code,name,'exec'),{'release':R,'r':R})
 except Exception as e:
  print('FAILED',name,start,end,repr(e));print(code);raise
 audit.append({'stage':name,'lines':[start,end],'core_sha256':hashlib.sha256((R/'defense/core.py').read_bytes()).hexdigest()})

name='stage_appearance_absence_repair';lines=(B/'recovered-patches'/(name+'.py')).read_text(encoding='utf-8').splitlines()
start=next(i for i,s in enumerate(lines) if s.startswith("core=r/'defense/core.py'"))
end=next(i for i,s in enumerate(lines[start:],start)if 'core.write_text(s' in s)
exec(compile('\n'.join(lines[start:end+1]),name,'exec'),{'r':R})
audit.append({'stage':name,'core_sha256':hashlib.sha256((R/'defense/core.py').read_bytes()).hexdigest()})
(B/'staged-source-transformation-audit.json').write_text(json.dumps(audit,indent=2))
bad=[]
for n,h in M.items():
 if not n.startswith('release/'):continue
 p=R/n[8:]
 if p.name!='core.py' and (B/'source-versions'/(h+'.py')).exists():
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((B/'source-versions'/(h+'.py')).read_bytes())
 if not p.exists():bad.append({'file':n,'status':'missing'})
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=h:bad.append({'file':n,'status':'different'})
print(json.dumps(bad,indent=2));(B/'remaining-source-differences.json').write_text(json.dumps(bad,indent=2))
