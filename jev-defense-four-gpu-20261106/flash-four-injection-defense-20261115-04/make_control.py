"""Reuse the proven orchestration with only new package/count/CPU bindings."""
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    source = HERE.parent / 'flash-late-corruption-defense-20261115-02/control.py'
    text = source.read_text('utf8')
    start = text.index('PACKAGE = HERE /')
    end = text.index('\n\n\ndef sha', start)
    text = text[:start] + '''PACKAGE = Path(json.loads((HERE / 'preparation-current.json').read_bytes())['package'])
from remote_util import remote''' + text[end:]
    before = "assert json.loads((HERE / 'CPU-injection-order.json').read_bytes())['passed'] >= 20"
    assert text.count(before) == 1
    text = text.replace(before, "qualification=json.loads((HERE / 'CPU-routing-current.json').read_bytes()); assert qualification['passed'] and qualification['manifest_sha256']==sha(PACKAGE/'manifest.json')")
    text = text.replace("m['trajectories']==12", "m['trajectories']==8")
    text = text.replace("h['expected']==12", "h['expected']==8")
    text = text.replace("'expected_trajectories':12", "'expected_trajectories':8")
    text = text.replace('new-injection-first', 'new-four-native-injection')
    compile(text, str(HERE / 'control.py'), 'exec')
    with (HERE / 'control.py').open('x', encoding='utf8') as handle:
        handle.write(text)
    save(HERE / 'control-source-binding.json', {'parent_source': str(source), 'parent_sha256': sha(source),
         'new_sha256': sha(HERE / 'control.py'), 'changes': ['new isolated package', '8 new trajectories',
             '11 CPU routing tests required', 'new recorded SSH transport'], 'old_queue_execution': False})
    print('New isolated eight-trajectory orchestration prepared')


if __name__ == '__main__':
    main()
