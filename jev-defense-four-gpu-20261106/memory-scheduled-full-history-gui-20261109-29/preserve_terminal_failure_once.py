"""Preserve NEW29 terminal originals; no experimental invocation or retry."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))
source = (OLD / 'preserve_terminal_failure_once.py').read_text(encoding='utf8')
source = source.replace("'j23evidence'", "'j29evidence'")
namespace = {'__file__': str(Path(__file__).resolve()), '__name__': 'new29_preservation_source'}
exec(compile(source, str(Path(__file__).resolve()), 'exec'), namespace)
namespace['HERE'] = HERE
namespace['ROOT3090'] = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
namespace['ROOT4090'] = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
if __name__ == '__main__':
    namespace['main']()
