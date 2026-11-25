"""Read-only process/held-lock evidence and post-exit terminal/chain collection."""
import json
from pathlib import Path
import inspect_native_direction_development as inspector
inspector.PREP=Path(__file__).resolve().parent/'focus-conflict-repair-development'
if __name__=='__main__':print(json.dumps(inspector.inspect()))
