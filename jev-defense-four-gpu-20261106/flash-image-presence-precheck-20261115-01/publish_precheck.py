"""Publish qualified local source and preserve the previous handoff heads."""
import hashlib
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def verify_seal(root, expected):
    assert sha((root / 'seal.json').read_bytes()) == expected
    for name, digest in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha((root / name).read_bytes()) == digest, (root, name)


def replace(path, raw):
    temporary = path.with_name(path.name + '.precheck-update-' + str(time.time_ns()))
    with temporary.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def main():
    assert not (HERE / 'publication-current.json').exists(), 'Already published; inspect receipt instead of republishing'
    qualification = HERE / 'cpu-qualification-1794755447375972400'
    qualification_sha = '64f0ccc24a3070a887bee5fb889ddc2938da848bc79d22567960a9f2f163279d'
    verify_seal(qualification, qualification_sha)
    result = json.loads((qualification / 'result.json').read_bytes())
    assert result['passed'] and result['tests_run'] == 18
    for name, expected in result['source_snapshot_sha256'].items():
        assert sha((HERE / name).read_bytes()) == expected, name
    failures = []
    for prior in sorted(HERE.glob('cpu-qualification-*')):
        if prior == qualification:
            continue
        seal_sha = sha((prior / 'seal.json').read_bytes())
        verify_seal(prior, seal_sha)
        failures.append({'root': str(prior), 'seal_sha256': seal_sha})
    parent = json.loads((HERE / 'parent-binding.json').read_bytes())['parent_publication']
    verify_seal(Path(parent['root']), parent['seal_sha256'])

    publication = HERE / ('source-publication-' + str(time.time_ns()))
    publication.mkdir()
    files = sorted(p for p in (HERE / 'source').rglob('*') if p.is_file())
    files += [HERE / name for name in ['README.md', 'parent-binding.json', 'user-authorization.json',
                                     'test_presence_precheck.py', 'qualify_precheck.py', 'publish_precheck.py']]
    source_manifest = {}
    for file in files:
        relative = file.relative_to(HERE)
        raw = file.read_bytes()
        destination = publication / 'snapshot' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as handle:
            handle.write(raw)
        source_manifest[relative.as_posix()] = sha(raw)
    for file in HERE.glob('cpu-local-encoder-diagnostic-*.json'):
        (publication / file.name).write_bytes(file.read_bytes())

    head = ('## 最新：按用户要求加入缺图前置 NO 与同 live 复拍\n\n'
            '当前源码权威 flash-framework-current.json → flash-image-presence-precheck-20261115-01/source；'
            '资格与发布回执见该目录 qualification-current.json / publication-current.json。'
            '文件缺失、None、空图片数据先判确定性 NO，跳过 Flash/主模型并真实复拍；有图才调用单 Flash，'
            '仅同图 Flash YES 入主。缺图 NO 与 Flash NO 独立计数，持续复拍至 YES/手停。'
            '动作后 observation 缺图的日志路径已兼容，原动作派发未变。\n\n'
            '18 CPU 边界/接线测试通过；前两次 CPU 尝试、原代码/日志/seal 与 PNG 编码预期修复诊断保留。'
            '修复测试预期而非改实验图像。固定 Flash prompt/revision/单图无上下文KV、主模型全史/system/预算保持。'
            '本次只发布本地新源码，0真实模型/GUI/评分/付费调用，未部署。'
            '新 GUI 必须新组包并更新审计以区分缺图 capture 与实际注入 delivery；'
            '不重开任何旧终局/队列。此前4次真实闭环验收与全部旧终局保持原样。以下旧快照。\n\n')
    prior_heads = {}
    for name in ['HANDOFF.md', 'README.md', 'flash-framework-current.json']:
        path = BASE / name
        if path.exists():
            raw = path.read_bytes()
            target = publication / 'prior-heads' / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
            prior_heads[name] = sha(raw)
    manifest = {'version': HERE.name, 'source_files': source_manifest,
                'parent_publication': parent, 'qualification_root': str(qualification),
                'qualification_seal_sha256': qualification_sha,
                'preserved_CPU_attempts': failures, 'previous_heads_sha256': prior_heads,
                'changed_production_files': ['source/flash/gate_core.py', 'source/gui_experiment.py'],
                'tests_passed': 18, 'real_model_calls': 0, 'real_GUI_calls': 0,
                'scorer_calls': 0, 'paid_API_calls': 0, 'deployed': False,
                'status': 'qualified_local_source_revision'}
    save(publication / 'manifest.json', manifest)
    for name in ['HANDOFF.md', 'README.md']:
        prior = (publication / 'prior-heads' / name).read_bytes()
        (publication / ('next-' + name)).write_bytes(head.encode('utf8') + prior)
    seal = {p.relative_to(publication).as_posix(): sha(p.read_bytes())
            for p in sorted(publication.rglob('*')) if p.is_file()}
    save(publication / 'seal.json', seal)
    publication_sha = sha((publication / 'seal.json').read_bytes())
    pointer = {'root': str(publication), 'seal_sha256': publication_sha,
               'source_root': str(HERE / 'source'), 'version': HERE.name,
               'status': 'qualified_local_source_revision', 'tests_passed': 18,
               'deployed': False, 'real_model_calls': 0, 'real_GUI_calls': 0}
    save(HERE / 'qualification-current.json', {'root': str(qualification),
                                             'seal_sha256': qualification_sha, 'tests_passed': 18})
    save(HERE / 'publication-current.json', pointer)
    for name in ['HANDOFF.md', 'README.md']:
        assert sha((BASE / name).read_bytes()) == prior_heads[name]
        replace(BASE / name, (publication / ('next-' + name)).read_bytes())
    replace(BASE / 'flash-framework-current.json', json.dumps(pointer, ensure_ascii=False, indent=2).encode('utf8'))
    verify_seal(publication, publication_sha)
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
