"""Create a new linked source attempt; preserve original 27-test sources intact."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'launcher-linked02'
OUT.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


old_gate = HERE / 'resource_gate.py'
old_launch = HERE / 'launch_once.py'
assert sha(old_gate) == '7960d7a71b1bcb7bd5a3504207ac86a607752ab7cfee9d6badabba84a5e7dd22'
assert sha(old_launch) == 'bc925708df5aea4e1bb382493eb4b20405c962afee61aa1cb4868ecae5a414f8'
gate = old_gate.read_text(encoding='utf-8')
launch = old_launch.read_text(encoding='utf-8')
gate_changes = [
    ("        compute.append({'uuid': uuid, 'pid': int(pid), 'used_mib': memory,\n                        'actual_identity': identity(int(pid))})",
     "        row = {'uuid': uuid, 'pid': int(pid), 'used_mib': memory}\n        target_uuids = {cards[i]['uuid'] for i in PHYSICAL_INDICES if i in cards}\n        if uuid in target_uuids:\n            try:\n                row['actual_identity'] = identity(int(pid))\n            except Exception as exc:\n                row['identity_read_error'] = {'type': type(exc).__name__, 'detail': str(exc)}\n        else:\n            row['identity_not_required_outside_task_GPU_scope'] = True\n        compute.append(row)"),
    ("        require(not require_empty, 'Task GPU already has compute before initial load')",
     "        require(not row.get('identity_read_error'), 'Target GPU process identity is unreadable; refuse inference')\n        require(not require_empty, 'Task GPU already has compute before initial load')"),
    ("        require(row['pid'] in registered, 'Unregistered late compute entered GPUs4–7')",
     "        require(row['pid'] in registered, 'Unregistered late compute entered GPUs4–7')\n        if 'actual_identity' in row:\n            require(same_identity(row['actual_identity'], registered[row['pid']]), 'Actual compute identity differs from registration')"),
]
launch_changes = [
    ("class Journal:\n", "def failure_record(exc):\n    return {'error': traceback.format_exc(), 'time_unix': time.time(),\n            'resource_evidence': getattr(exc, 'resource_evidence', None)}\n\n\nclass Journal:\n"),
    ("        except Exception:\n            save_new(args.output / 'postexit-resource-failure.json', {'error': traceback.format_exc(), 'time_unix': time.time()})",
     "        except Exception as exc:\n            save_new(args.output / 'postexit-resource-failure.json', failure_record(exc))"),
    ("    except BaseException:\n        save_new(args.output / 'launcher-failure.json', {'error': traceback.format_exc(), 'time_unix': time.time(),\n                                                       'existing_outputs_not_removed': True})",
     "    except BaseException as exc:\n        save_new(args.output / 'launcher-failure.json', {**failure_record(exc),\n                                                       'existing_outputs_not_removed': True})"),
    ("    except BaseException:\n        # Pre-claim failures cannot alter a prior output; preserve separately.",
     "    except BaseException as exc:\n        # Pre-claim failures cannot alter a prior output; preserve separately."),
    ("        save_new(target / 'failure.json', {'error': traceback.format_exc(), 'time_unix': time.time(),\n                                           'no_automatic_retry': True, 'old_outputs_untouched': True})",
     "        save_new(target / 'failure.json', {**failure_record(exc),\n                                           'no_automatic_retry': True, 'old_outputs_untouched': True})"),
]
for label, source, changes in [('resource_gate.py', gate, gate_changes), ('launch_once.py', launch, launch_changes)]:
    for old, new in changes:
        assert source.count(old) == 1, 'Repair only applies to exact expected old source'
        source = source.replace(old, new)
    with (OUT / label).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(source)
for name in ['test_resource_and_launch_contract.py']:
    with (OUT / name).open('xb') as stream:
        stream.write((HERE / name).read_bytes())
receipt = {'type': 'linked_source_only_resource_failure_preservation_and_scope_repair',
           'old_resource_gate_SHA256': sha(old_gate), 'old_launcher_SHA256': sha(old_launch),
           'new_resource_gate_SHA256': sha(OUT / 'resource_gate.py'),
           'new_launcher_SHA256': sha(OUT / 'launch_once.py'),
           'old_CPU27_receipt_retained': True,
           'changes': ['Persist exception.resource_evidence in all three launcher failure paths.',
                       'Record raw global compute, require proc identities only for target GPU4–7.',
                       'Unreadable target identities still strictly reject and preserve partial evidence.'],
           'budget_or_input_or_GPU_scope_or_strict_lock_conditions_changed': False,
           'actual_stage_submit_model_GUI_resource_mutations': 0}
with (OUT / 'source-repair-receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps(receipt))
