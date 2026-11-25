"""Prepare a new postexit audit; does not contact a model or remote host."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'audit_first_gpu_four02.py').read_text(encoding='utf8')
s=s.replace("T=R/'gpu-four-terminal-collection-01/original'","T=R/'gpu-compact-four-terminal-collection-02/original'")
s=s.replace("C=R/'native-auxiliary-admission-01/cpu-native-four-linked02/collected/admission-01'","C=R/'native-auxiliary-admission-compact02/cpu-native-compact-four-02/collected/admission-01'")
s=s.replace("O=R/'first-four-root-technical-audit-02'","O=R/'compact-four-root-technical-audit-02'")
s=s.replace("row['current_sha256']","row['reused_full_sha256']")
s=s.replace("    assert result['contract_valid']is False and not(d/'evidence-packet.json').exists()", "    assert result['contract_valid']==(d/'evidence-packet.json').exists()\n    if result['contract_valid']:\n        packet=read(d/'evidence-packet.json')\n        assert packet['raw_output_sha256']==result['raw_output_sha256']\n        assert packet['image_sha256']==result['image_sha256']\n        assert packet['inventory_is_exhaustive']is False and packet['automatic_allow_or_block']is False\n        assert packet['semantic_correctness_established']is False and result['natural_eos']is True")
s=s.replace("    assert read(d/'contract-failure.json')==result['contract_error']", "    if not result['contract_valid']:assert read(d/'contract-failure.json')==result['contract_error']")
s=s.replace("'usable_evidence_packets':0", "'usable_evidence_packets':sum(x['contract_valid']for x in rows)")
s=s.replace("'gpu-four-terminal-collection-01/remote-audit.json'", "'gpu-compact-four-terminal-collection-02/remote-audit.json'")
s=s.replace("write(O/'seal.json',{'receipt.json':sha(O/'receipt.json'),'audit_source':sha(Path(__file__))})", "with(O/'audit_source').open('xb')as f:f.write(Path(__file__).read_bytes())\nwrite(O/'seal.json',{'receipt.json':sha(O/'receipt.json'),'audit_source':sha(O/'audit_source')})")
s=s.replace("'full_current_four_shards_official_pin_bound':True", "'full_current_four_shards_official_pin_bound':True,'current_identity_uses_sealed_prior_full_hash_and_current_stat_not_rehash':True")
with(R/'audit_compact_gpu_four02.py').open('x',encoding='utf8',newline='\n')as f:f.write(s)
print('New postexit audit source prepared; not run.')
