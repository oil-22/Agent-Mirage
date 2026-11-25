"""Grammar controls verifier syntax only; semantic/citation checks remain independent."""
def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
STR={'type':'string'}
REASON={'type':'string','maxLength':480}
DESCRIPTION={'type':'string','maxLength':320}
BOOL={'type':'boolean'}
STAT={'type':'string','enum':['supported','contradicted','insufficient','uncertain']}
KINDS=['button','link','input','menu_option','image','content','background','unknown','not_applicable']
def array(item):return {'type':'array','items':item}

def judge_schema(view,candidate=None,phase=None):
    if phase not in {None,'history_report','exact_source_reference'}:raise ValueError('Unknown verifier schema phase')
    sources=[]
    if view.images:
        sources.append(obj({'observation_id':{'type':'string','enum':[view.observation_id]},
            'image_index':{'type':'integer','enum':list(range(len(view.images)))},
            'coordinate_space':{'type':'string','enum':['normalized_1000','pixels']},
            'box_xyxy':{'type':'array','items':{'type':'number'},'minItems':4,'maxItems':4},'description':DESCRIPTION}))
    if isinstance(candidate,dict)and candidate.get('mode')=='point_probe':
        return obj({'kind':{'type':'string','enum':KINDS[:-1]},'visible_text':DESCRIPTION,
            'evidence':array({'anyOf':sources}if sources else STR),'reason':REASON})
    indices=[i for i,m in enumerate(view.messages)if (bool(m['content'])if isinstance(m['content'],str)else any(b.get('text')for b in m['content']if b.get('type')=='text'))]
    if indices:sources.append(obj({'message_index':{'type':'integer','enum':indices},'span_id':{'type':'string','enum':['full']}}))
    if candidate is not None:
        sources.append(obj({'source':{'type':'string','enum':['candidate']},'span_id':{'type':'string','enum':['full']}}))
    evidence=array({'anyOf':sources}if sources else STR)
    if phase=='history_report':
        if view.images or candidate is None:raise ValueError('History comparison needs text-only inputs')
        assistants=[i for i in indices if view.messages[i].get('role')=='assistant']
        # This is a format/source restriction, never a forced support label.
        # All non-support labels remain available, including when history is empty.
        branches=[]
        if assistants:
            cited_actor=obj({'message_index':{'type':'integer','enum':assistants},'span_id':{'type':'string','enum':['full']}})
            branches.append(obj({'status':{'type':'string','enum':['supported']},'reason':REASON,
                'evidence':{**array(cited_actor),'minItems':1}}))
        branches.append(obj({'status':{'type':'string','enum':['contradicted','insufficient','uncertain']},
            'reason':REASON,'evidence':evidence}))
        # A dedicated relation object avoids the installed grammar engine's
        # maxItems=0 first-item bug and Python-cased boolean enum bug.
        return {'anyOf':branches}
    if candidate is None:
        return obj({'status':{'type':'string','enum':['usable','limited','unknown']},'visible':array(STR),
            'limitations':array(STR),'loading':{'type':'string','enum':['visible','not_observed','uncertain']},
            'evidence':evidence,'reason':REASON})
    # Enforce only the already-required mechanical citation condition. The grammar
    # cannot force a semantic label or make a citation truthful; validators still
    # check source, coordinates and visual grounding independently.
    action_branches=[]
    for supported in [True,False]:
        action_branches.append(obj({'status':{'type':'string','enum':['supported']if supported else['contradicted','insufficient','uncertain']},
            'target_kind':{'type':'string','enum':KINDS},'reason':REASON,
            'evidence':{**evidence,**({'minItems':1}if supported else{})}}))
    result = obj({'claims':array(obj({'id':{'type':'string','maxLength':32},'kind':{'type':'string','enum':['gui_fact','history_report','intent','hypothesis']},'text':{'type':'string','maxLength':max(1,len(candidate))},'status':STAT,'evidence':evidence,
        'reason':REASON,'dependent_decisions':array(STR)})),
        'action':{'anyOf':action_branches},
        'acknowledges_visual_deficit':BOOL,'pure_wait':BOOL})
    if phase=='exact_source_reference':
        from source_quote_references import bind_reference_schema
        result=bind_reference_schema(result,candidate)
    return result
