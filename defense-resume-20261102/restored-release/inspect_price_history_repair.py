"""Read-only process/locks/logs/chains; after exit preserve all terminal artifacts."""
import json
from pathlib import Path
import inspect_native_direction_development as inspector
inspector.PREP=Path(__file__).resolve().parent/'price-history-repair-development'
if __name__=='__main__':print(json.dumps(inspector.inspect()))
