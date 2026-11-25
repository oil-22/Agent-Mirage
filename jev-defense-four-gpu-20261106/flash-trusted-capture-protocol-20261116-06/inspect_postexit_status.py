"""Compact actual identity snapshot; full original inspection receipts retained."""
import contextlib
import io
import json

import control

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    control.inspect()
for line in buffer.getvalue().splitlines():
    row = json.loads(line)
    print(json.dumps({'host': row['host'], 'status': row['status'],
                      'actual': row['actual'], 'failure': row['failure']}))
