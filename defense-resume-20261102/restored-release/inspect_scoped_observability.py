"""Same post-exit sealing/chain checks, scoped to the new isolated development root."""
import json
from pathlib import Path
import inspect_native_direction_development as inspector
inspector.PREP=Path(__file__).resolve().parent/'scoped-observability-development'
if __name__=='__main__':
    result=inspector.inspect()
    if result.get('process'):
        assert any(x['target'].endswith('/scoped-observability-development.lock')for x in result['process']['held_locks'])
    print(json.dumps(result))
