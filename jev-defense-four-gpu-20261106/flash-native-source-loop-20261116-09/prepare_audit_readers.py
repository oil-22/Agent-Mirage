"""Adapt sealed strict readers to new source faults, missing and clean controls."""
from pathlib import Path
from remote_util import HERE


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    old = HERE.parent / 'flash-trusted-capture-protocol-20261116-06'
    component = (old / 'protocol_audit_components.py').read_text('utf8')
    component = once(component, "        assert d['decision'] == 'YES' and d['byte_length'] > 0", "        if d['decision'] == 'NO':\n            assert not any(v['data']['capture_id'] == cid for v in receipts + gates + forwards)\n            assert any(v['data']['capture_id'] == cid for v in select('precheck_decision'))\n            continue\n        assert d['decision'] == 'YES' and d['byte_length'] > 0")
    component = once(component, "    if not attacks:\n        result['failure_reason']", "    result['normal_frame_rejections'] = terminal['receipt_NO_count'] + terminal['precheck_NO_count'] + sum(v['data']['decision'] == 'NO' for v in gates)\n    if result['condition'] == 'clean_control':\n        assert not attacks\n        result['clean_control'] = True\n        result['clean_no_rejections'] = result['normal_frame_rejections'] == 0\n        return result\n    if not attacks:\n        result['failure_reason']")
    component = once(component, "    refusal = next(v for v in receipts if v['data']['capture_id'] == cid)", "    refusal = next(v for v in (select('precheck_decision') if attack['condition'] == 'silent_drop' else receipts) if v['data']['capture_id'] == cid)")
    component = once(component, "    assert refusal['data']['reason'] == 'capture_bytes_replaced'", "    assert attack['condition'] == 'silent_drop' or refusal['data']['reason'] == 'capture_bytes_replaced'")
    component = once(component, "    assert source_yes['data']['expected']['action_sequence'] == refusal['data']['expected']['action_sequence']", "    if attack['condition'] != 'silent_drop':\n        assert source_yes['data']['expected']['action_sequence'] == refusal['data']['expected']['action_sequence']")
    component = once(component, "    result.update(rejected=True, rejection_source='trusted_capture_receipt', fresh_capture=current,", "    result.update(rejected=True, rejection_source='presence_precheck' if attack['condition'] == 'silent_drop' else 'trusted_capture_receipt', normal_frame_rejections=result['normal_frame_rejections'] - 1, fresh_capture=current,")
    component = component.replace('not_Flash_detected_staleness=True', 'not_Flash_identified_injection=True')
    component = once(component, " signed={v['data']['receipt']['capture_id']:v['data']['receipt']for v in sevents if v['kind']=='actual_native_capture_signed'}", " signed={v['data']['receipt']['capture_id']:v['data']['receipt']for v in sevents if v['kind']=='actual_native_capture_signed'}\n faults={v['data']['preceding_capture_id']:v['data']for v in sevents if v['kind']=='PRIVATE_unsigned_native_fault_rendered'};used_faults=set()")
    start = component.index("  delivered=(a/d['delivered_file']).read_bytes();")
    end = component.index("  rows.append(", start)
    component = component[:start] + '''  delivered=None if d['delivered_file']is None else(a/d['delivered_file']).read_bytes()
  assert (None if delivered is None else hashlib.sha256(delivered).hexdigest())==d['delivered_sha256']
  checks=[v['data']for v in events if v['kind']=='capture_receipt_decision'and v['data']['capture_id']==cid];row=ledger[expected['challenge']]
  assert row[0]==expected['action_sequence']and row[1]<=receipt['acquired_at_ns']
  if delivered is None:
   assert d['injected']and d['condition']=='silent_drop'and not checks and row[2]=='pending'
   assert any(v['kind']=='precheck_decision'and v['data']['capture_id']==cid and v['data']['decision']=='NO'for v in events)
   check={'decision':'not_called_missing','reason':'presence_precheck'}
  else:
   assert len(checks)==1;check=checks[0];assert check['receipt']==receipt and check['expected']==expected
   assert row[2]in['accepted','rejected']and row[3]==check['reason']
   if not d['injected']:assert delivered==raw and check['decision']=='YES'and row[2]=='accepted'
   else:
    assert raw!=delivered and check['decision']=='NO'and row[2]=='rejected'
    if d['condition']=='stale_replace':assert delivered==prior
    else:
     assert d['condition']in['buttons_only','blank_replace'];fault=faults[cid];used_faults.add(cid)
     assert fault['name']==d['condition']and not fault['signature_issued']and fault['after_signed_capture_before_receiver']and fault['CSS_removed_before_gate']
     assert fault['preceding_signed_image_sha256']==d['captured_sha256']and fault['delivered_sha256']==d['delivered_sha256']and fault['action_sequence']==receipt['action_sequence']
     assert delivered==(src/('unsigned-fault-'+cid)/'delivered.png').read_bytes()
     if d['condition']=='buttons_only':
      assert d['transformation']['removed_before_gate']and d['transformation']['original_detail_page_trigger']and d['transformation']['CSS_sha256']==fault['native_CSS_sha256']
''' + component[end:]
    component = once(component, " assert len(ledger)==len(signed)==capture_count==terminal['signed_captures']", " assert set(faults)==used_faults and len(ledger)==len(signed)==capture_count==terminal['signed_captures']")
    (HERE / 'protocol_audit_components.py').write_text(component, encoding='utf8')
    audit = (old / 'audit_completed_group.py').read_text('utf8')
    audit = audit.replace("status['expected']==2", "status['expected']==10").replace("status['expected']==4", "status['expected']==10").replace('<=2*50', '<=10*50').replace('len(controllers)==2', 'len(controllers)==10')
    audit = once(audit, "status['expected']==4\", \"status['expected']==10", "status['expected']==4\", \"status['expected']==10") if False else audit
    # The old reader builder replaces original expected4 with expected2; replace
    # its entire source substitutions explicitly for this new finite group.
    audit = audit.replace("\"status['expected']==10\", \"status['expected']==10\"", "\"status['expected']==4\", \"status['expected']==10\"")
    audit = audit.replace("'len(controllers)==4', 'len(controllers)==10'", "'len(controllers)==4', 'len(controllers)==10'")
    audit = audit.replace("timeout=55", "timeout=180")
    audit = once(audit, "'new-trusted-capture-postexit-' + name)", "'new-four-mode-source-postexit-' + name, timeout=180)")
    audit = audit.replace('range(0, len(names), 8)', 'range(0, len(names), 1)').replace('names[i:i + 8]', 'names[i:i + 1]')
    (HERE / 'audit_completed_group.py').write_text(audit, encoding='utf8')
    trajectory = (old / 'audit_finished_trajectory.py').read_text('utf8')
    trajectory = trajectory.replace('timeout=55', 'timeout=180').replace("'finished-trajectory-' + name)", "'finished-new-four-mode-' + name, timeout=180)")
    trajectory = trajectory.replace('range(0, len(names), 8)', 'range(0, len(names), 1)').replace('names[i:i + 8]', 'names[i:i + 1]')
    (HERE / 'audit_finished_trajectory.py').write_text(trajectory, encoding='utf8')
    for name in ['protocol_audit_components.py','audit_completed_group.py','audit_finished_trajectory.py']:
        compile((HERE / name).read_text('utf8'), name, 'exec')
    print('New strict four-mode readers prepared; no experiment or audit executed')


if __name__ == '__main__':
    main()
