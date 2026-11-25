"""Static argument binding against signatures actually listed in a legal prompt.

No model, GUI, action rewriting, annotation evaluation or source import occurs.
This is a CPU contract audit, not a replacement for the native environment parser.
"""
import ast
import copy
import hashlib
import inspect
import re


def extract_contract(messages):
    sections = []
    for message in messages:
        if message.get('role') != 'user':
            continue
        content = message['content']
        texts = [content] if isinstance(content, str) else [
            block['text'] for block in content if block.get('type') == 'text']
        for text in texts:
            if re.search(r'^# Action space:\s*$', text, re.MULTILINE):
                sections.append(text)
    if len(sections) != 1:
        raise ValueError('Exactly one actual action-space prompt block is required')
    original_block = sections[0]
    markers = list(re.finditer(r'^# Action space:\s*$', original_block, re.MULTILINE))
    if len(markers) != 1:
        raise ValueError('Ambiguous action-space section boundary')
    # History may contain literal action calls. They are not declarations in
    # the later Action space section; retain the full block hash separately.
    section = original_block[markers[0].start():]
    next_heading = re.search(r'^# ', section[1:], re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start() + 1]
    count = re.findall(r'^(\d+) different types of actions are available\.$', section, re.MULTILINE)
    if len(count) != 1 or 'Only a single action can be provided at once.' not in section:
        raise ValueError('Native action count or single-action declaration is missing')
    before_examples = section.split('Only a single action can be provided at once.', 1)[0]
    headers = re.findall(r'^([A-Za-z_]\w*\(.*\))\s*$', before_examples, re.MULTILINE)
    if len(headers) != int(count[0]):
        raise ValueError('Delivered signature count mismatch')
    signatures = {}
    for header in headers:
        node = ast.parse('def ' + header + ':\n    pass\n').body[0]
        if node.name in signatures:
            raise ValueError('Duplicate delivered action signature')
        args = node.args
        if args.posonlyargs or args.vararg or args.kwonlyargs or args.kwarg:
            raise ValueError('Unexpected native signature shape; preserve it for review')
        defaults = [inspect.Parameter.empty] * (len(args.args) - len(args.defaults))
        defaults += [ast.literal_eval(value) for value in args.defaults]
        parameters = [inspect.Parameter(arg.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                        default=copy.deepcopy(default))
                      for arg, default in zip(args.args, defaults)]
        signatures[node.name] = {
            'native_header': header,
            'signature': inspect.Signature(parameters),
            'argument_ast': ast.dump(args, include_attributes=False),
        }
    return {
        'section_sha256': hashlib.sha256(section.encode()).hexdigest(),
        'source_block_sha256': hashlib.sha256(original_block.encode()).hexdigest(),
        'section': section,
        'single_action': True,
        'signatures': signatures,
        'scope': 'Exported legal prompt only; current runtime/source/wire provenance is separate',
    }


def bind_parsed_call(contract, function_name, function_args, named_argument_type):
    """Bind the unchanged output of the frozen native literal parser.

    Only parameter shape is checked. Defaults and annotations are not used to
    infer targets, enforce extra type/range rules or alter the native action.
    """
    if function_name not in contract['signatures']:
        raise ValueError('Action absent from this delivered action space')
    positional, keywords = [], {}
    seen_named = False
    for value in function_args:
        if isinstance(value, named_argument_type):
            seen_named = True
            if value.name in keywords:
                raise ValueError('Duplicate named argument')
            keywords[value.name] = value.value
        else:
            if seen_named:
                raise ValueError('Positional argument after a named argument')
            positional.append(value)
    signature = contract['signatures'][function_name]['signature']
    bound = signature.bind(*positional, **keywords)
    return {
        'function': function_name,
        'explicit_argument_names': list(bound.arguments),
        'native_header': contract['signatures'][function_name]['native_header'],
        'defaults_inserted': False,
        'annotations_evaluated': False,
        'action_modified': False,
        'environment_or_target_confirmed': False,
    }
