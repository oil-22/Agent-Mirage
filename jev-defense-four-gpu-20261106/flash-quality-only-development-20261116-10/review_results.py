"""Apply presealed criteria to actual audited decisions; never tune thresholds."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    pp = json.loads((HERE / 'preparation-current.json').read_bytes()); prep = Path(pp['root'])
    audit = json.loads((HERE / 'completed-audit-current.json').read_bytes()); root = Path(audit['root'])
    assert sha(root / 'seal.json') == audit['seal_sha256']
    for name, h in json.loads((root / 'seal.json').read_bytes()).items(): assert sha(root / name) == h
    summary = json.loads((root / 'summary.json').read_bytes()); rows = {v['case_id']: v for v in summary['request_rows']}
    assert summary['status'] == 'passed' and len(rows) == summary['actual_Flash_requests'] == 20
    plan = json.loads((prep / 'PRIVATE-evaluation-plan.json').read_bytes())
    false_blocks = [name for name in plan['normal_required_YES'] if rows[name]['decision'] != 'YES']
    unusable_passes = [name for name in plan['unusable_required_NO'] if rows[name]['decision'] != 'NO']
    result = {'passed': not false_blocks and not unusable_passes, 'before_GUI': True, 'audit': audit, 'preparation_manifest_sha256': pp['manifest_sha256'], 'fixed_contract_sha256': rows['n01']['contract_sha256'], 'normal': len(plan['normal_required_YES']), 'false_blocks': false_blocks, 'unusable': len(plan['unusable_required_NO']), 'unusable_passes': unusable_passes, 'minimal_n01': rows['n01'], 'sparse_diagnostics': [rows[v] for v in ['c09','b01']], 'boundary_c18': rows['c18'], 'all_20_results': rows, 'not_a_GUI_success_or_model_efficacy_rate': True}
    report = HERE / ('quality-review-' + str(time.time_ns())); report.mkdir()
    save(report / 'result.json', result)
    text = '单图质量提示开发审查\n\n实际20个完整PNG各调用一次，原生单图无任务/主历史/KV、同revision/BF16/argmax。\n\n正常对照%d张，误拦%s；不可用对照%d张，漏放%s。合法单按钮n01=%s。\n\n稀疏遮罩b01/c09仅作视觉诊断，其来源问题交给可信回执；不把Flash YES称为识别攻击。c18边界继续未决。全部20原始结果、单次探针原NO、上一严格提示单按钮误拦完整保留。该结果不是完整GUI成功或总体Mirage率降低。\n' % (result['normal'], str(false_blocks), result['unusable'], str(unusable_passes), rows['n01']['decision'])
    (report / '单图质量提示与正常误拦审查-20261116.md').write_text(text, encoding='utf8')
    save(report / 'seal.json', {q.name: sha(q) for q in report.iterdir() if q.is_file()})
    save(HERE / 'release-readiness-current.json', {'root': str(report), 'seal_sha256': sha(report / 'seal.json'), 'passed': result['passed'], 'audit': audit, 'contract_sha256': result['fixed_contract_sha256']})
    print(json.dumps({'root': str(report), 'passed': result['passed'], 'false_blocks': false_blocks, 'unusable_passes': unusable_passes, 'n01': rows['n01']['decision'], 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
