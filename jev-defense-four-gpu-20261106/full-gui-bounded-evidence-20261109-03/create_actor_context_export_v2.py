from remote_control import HERE,save,sha

old=HERE/'collect_source_first_packets.py';text=old.read_text(encoding='utf8')
text=text.replace(" observation={};wire=None"," observation={};wire=None;actor_context=None")
text=text.replace("  if e['kind']=='actual_actor_wire_request':wire=e", "  if e['kind']=='actor_request':actor_context=e\n  if e['kind']=='actual_actor_wire_request':wire=e")
text=text.replace("  obs=observation[e['data']['observation_id']]", "  obs=observation[e['data']['observation_id']]\n  assert actor_context is not None and actor_context['data']['public']['observation_id']==e['data']['observation_id']\n  actor_public=actor_context['data']['public']")
text=text.replace("'observation_id':obs['data']['public']['observation_id'],'recent_action':obs['data']['public']['recent_action'],\n    'execution_feedback':obs['data']['public']['execution_feedback']", "'observation_id':actor_public['observation_id'],'recent_action':actor_public['recent_action'],\n    'execution_feedback':actor_public['execution_feedback'],'actor_context_event_sha256':actor_context['sha256'],\n    'context_metadata_source':'actual actor_request, never preceding scene-only checker projection'")
text=text.replace("'source-first-candidate-public-export'", "'source-first-candidate-public-export-v2-actual-actor-context'")
with(HERE/'collect_source_first_packets_v2.py').open('x',encoding='utf8')as f:f.write(text)
save(HERE/'actor-export-metadata-repair.json',{'parent_exporter_sha256':sha(old),
    'new_exporter_sha256':sha(HERE/'collect_source_first_packets_v2.py'),
    'issue':'observation IDs also appear in reduced scene-only checker projection, so old ancillary recent_action/feedback could be projected metadata',
    'actual_actor_messages_candidate_images_unchanged':True,
    'repair':'Use nearest actual actor_request public metadata; actual actor wire still authoritative for messages/images',
    'previous_packets_preserved':True,'model_GUI_calls':0})
print('Source export metadata binding repaired; no model/GUI mutation.')
