"""Linked CPU-only repair of the local DP marker; first script/error retained."""
from pathlib import Path
original=Path(__file__).with_name('plan_seven.py');source=original.read_text(encoding='utf8')
assert source.count("code.index('dp={(0,0)}')")==1
source=source.replace("code.index('dp={(0,0)}')","code.index('dp={(0,0)')")
exec(compile(source,str(Path(__file__)),'exec'))
