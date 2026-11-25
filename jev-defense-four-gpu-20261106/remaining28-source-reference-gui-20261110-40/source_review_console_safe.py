"""Read-only console formatting; image bytes stay in original sealed files."""
import hashlib
import json


def messages_text(messages):
    result = []
    for index, message in enumerate(messages):
        content = message['content']
        if isinstance(content, str):
            texts, other = [content], []
        else:
            texts = [block['text'] for block in content if block.get('type') == 'text']
            other = [block.get('type') for block in content if block.get('type') != 'text']
        result.append(dict(index=index, role=message['role'], texts=texts,
                           nontext_block_types=other))
    return result


def canonical_sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {key: '[image/binary bytes retained in sealed source]'
                if key in {'raw_base64', 'image_base64', 'files_base64', 'exports'}
                else safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, str) and value.startswith('data:') and ';base64,' in value:
        return '[image data URL retained in sealed source]'
    return value


def print_safe(value):
    print(json.dumps(safe(value), ensure_ascii=False))
