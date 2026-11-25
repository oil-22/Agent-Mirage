"""Parse proposed actions without executing them; preserve schema violations."""
import ast
import json
import re

ALLOWED = {'click','doubleClick','rightClick','moveTo','dragTo','scroll','hscroll','write','press','hotkey','keyDown','keyUp','mouseDown','mouseUp'}
TERMINALS = {'WAIT','DONE','FAIL'}

def action_spans(text):
    for pattern, wrapper in [
        (r'<action>(.*?)</action>', 'xml'),
        (r'<\|begin_of_box\|>(.*?)<\|end_of_box\|>', 'glm_box'),
        (r'```[\w+-]*[ \t]*\n(.*?)```', 'fenced'),
    ]:
        matches=list(re.finditer(pattern,text,re.S))
        if matches:return [(m.start(1),m.end(1),wrapper) for m in matches]
    matches=list(re.finditer(r'(?mi)^\s*(?:Action:\s*)?(WAIT|DONE|FAIL)\s*$',text))
    if matches:return [(m.start(1),m.end(1),'bare_terminal') for m in matches]
    matches=list(re.finditer(r'(?m)^Action:\s*(pyautogui\.[^\n]+)$',text))
    return [(m.start(1),m.end(1),'action_line') for m in matches]

def audit_action(text):
    spans=action_spans(text)
    base={'action':'NO_SINGLE_ACTION','action_intent':None,'action_kind':'unknown','action_schema':'unparsed','action_wrapper':None,'matches_main_action_schema':False}
    if len(spans)!=1:
        if len(spans)>1:base.update(action='AMBIGUOUS',action_schema='multiple_blocks')
        return base
    start,end,wrapper=spans[0];value=text[start:end].strip();base['action_wrapper']=wrapper
    if value.upper() in TERMINALS:
        base.update(action=value.upper(),action_intent=value.upper(),action_kind=value.lower(),action_schema='terminal' if value in TERMINALS else 'noncanonical_terminal_case',matches_main_action_schema=value in TERMINALS)
        return base
    try:
        obj=json.loads(value)
        if isinstance(obj,dict):
            name=str(obj.get('action',obj.get('action_type',obj.get('type','')))).lower()
            canonical='json:'+json.dumps(obj,sort_keys=True)
            base.update(action=canonical,action_intent=canonical,action_kind=name or 'json_action',action_schema='json_alternative')
            return base
    except (ValueError,TypeError):pass
    try:
        tree=ast.parse(value)
        if len(tree.body)!=1:
            base.update(action='MULTIPLE_STATEMENTS:'+value,action_schema='multiple_statements')
            return base
        node=tree.body[0]
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Attribute) and node.value.attr in TERMINALS:
            base.update(action=node.value.attr,action_intent=node.value.attr,action_kind=node.value.attr.lower(),action_schema='pseudo_terminal_attribute')
            return base
        if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call):raise ValueError('not one call')
        call=node.value
        name=call.func.attr if isinstance(call.func,ast.Attribute) else call.func.id if isinstance(call.func,ast.Name) else ''
        qualified=isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='pyautogui'
        literal=True
        try:
            keyword_names=[x.arg for x in call.keywords]
            if len(keyword_names)!=len(set(keyword_names)):raise ValueError('duplicate keyword argument')
            for x in call.args:ast.literal_eval(x)
            for x in call.keywords:
                if x.arg is None:raise ValueError('kwargs expansion')
                ast.literal_eval(x.value)
        except Exception:literal=False
        if name in TERMINALS:
            base.update(action=name,action_intent=name,action_kind=name.lower(),action_schema='pseudo_terminal_call')
        else:
            intent=None
            if literal:
                args=[ast.literal_eval(x) for x in call.args]
                kwargs={x.arg:ast.literal_eval(x.value) for x in call.keywords}
                positional={'click':['x','y'],'doubleClick':['x','y'],'rightClick':['x','y'],'moveTo':['x','y'],'dragTo':['x','y'],'write':['message'],'press':['keys'],'scroll':['clicks'],'hscroll':['clicks']}.get(name,[])
                for parameter in positional:
                    if parameter in kwargs and len(args)==positional.index(parameter):args.append(kwargs.pop(parameter))
                intent=json.dumps({'call':name,'args':args,'kwargs':kwargs},sort_keys=True)
            base.update(action=ast.dump(call,include_attributes=False),action_intent=intent,action_kind=name or 'unknown_call',action_schema='qualified_pyautogui_literal' if qualified and name in ALLOWED and literal else 'other_python_call',matches_main_action_schema=qualified and name in ALLOWED and literal and wrapper=='fenced')
        return base
    except Exception:
        base.update(action='UNPARSED:'+value)
        return base
