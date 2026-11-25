"""Prepare an UNSENT generic-prompt change and source-bound scope controls.

This creates local evaluation artifacts only. It cannot load a model, submit a
request, change the current32 experiment, or approve a future condition.
"""
import difflib
import hashlib
import json
from pathlib import Path
import time

from PIL import Image

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'literal-marking-scope-control-preparation-created.json'
    assert not pointer.exists()
    old = json.loads((HERE / 'summary-boundary-diagnosis-created.json').read_bytes())
    old_root = Path(old['root'])
    assert old_root.parent == HERE and verify_seal(old_root) == old['seal_sha256']
    old_receipt = json.loads((old_root / 'receipt.json').read_bytes())
    v6 = (old_root / 'original-fixed-v6-prompt.txt').read_bytes().decode('utf8')
    v7 = (old_root / 'UNSENT-short-sentence-prompt-proposal.txt').read_bytes().decode('utf8')
    assert hashlib.sha256(v6.encode()).hexdigest() == old_receipt['original_fixed_prompt_sha256']
    assert hashlib.sha256(v7.encode()).hexdigest() == old_receipt['unsent_proposal_sha256']
    paragraph = ('When clearly readable, include a short exact identifying marking physically '
        'printed on a displayed object or within its photograph. Keep that marking separate '
        'from the page title and nearby text. Read only legible characters; omit unreadable '
        'markings instead of completing a brand or model name. Do not infer material or '
        'manufacturing method from a product title or a tiny photograph. These are still '
        'sampled observations, never an exhaustive inventory.\n')
    assert v7.count('Return SHORT JSON.') == 1
    proposed = v7.replace('Return SHORT JSON.', paragraph + 'Return SHORT JSON.', 1)
    for answer_token in ['aruba', 'Grizzly', '185', 'Akron', 'kayak', 'basketball']:
        assert answer_token.casefold() not in proposed.casefold()
    sources = [
        ('detail', HERE / 'auxiliary-source-0066-1794261362949992500', 'original.png'),
        ('input', Path(json.loads((HERE / 'source14-price-0082-source-created.json').read_bytes())['root']), 'image-00.png'),
        ('listing', Path(json.loads((HERE / 'source14-price-0085-source-created.json').read_bytes())['root']), 'image-00.png')
    ]
    root = HERE / ('literal-marking-scope-control-preparation-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'UNSENT-generic-marking-prompt-v8.txt').write_bytes(proposed.encode('utf8'))
    (root / 'original-running-v6-prompt.txt').write_bytes(v6.encode('utf8'))
    (root / 'prior-UNSENT-v7-prompt.txt').write_bytes(v7.encode('utf8'))
    (root / 'proposed-v6-to-v8.diff').write_text(''.join(difflib.unified_diff(
        v6.splitlines(True), proposed.splitlines(True), fromfile='running-fixed-v6',
        tofile='UNSENT-fixed-generic-v8')), encoding='utf8')
    packets = []
    for ident, source, image_name in sources:
        assert source.parent == HERE
        source_seal = verify_seal(source)
        original = source / image_name
        with Image.open(original) as image:
            assert image.size == (1280, 720)
        filename = ident + '-complete-original.png'
        (root / filename).write_bytes(original.read_bytes())
        assert sha(root / filename) == sha(original)
        # Only these two fields are permitted in the prospective auxiliary body.
        # Metadata and PRIVATE control expectations are outside that body.
        body = {'image_file': filename, 'prompt': proposed}
        save(root / (ident + '-prospective-input.json'), body)
        assert set(body) == {'image_file', 'prompt'}
        packets.append(dict(id=ident, input_file=ident + '-prospective-input.json',
            input_file_sha256=sha(root / (ident + '-prospective-input.json')),
            image_sha256=sha(original), full_image_size=[1280, 720],
            original_source=str(source), original_source_seal_sha256=source_seal,
            no_cropping_resizing_or_reencoding=True, fixed_prompt_sha256=sha(root / 'UNSENT-generic-marking-prompt-v8.txt'),
            source_selected_known_development_image=True))
    # PRIVATE review expectations are evaluation provenance, never a model input.
    controls = [
        dict(id='marking-wrong', image='detail', candidate='The blue kayak is a Grizzly 10.',
             expected='Contradicted by readable original hull marking aruba10;correct colour or price must not rescue wrong identity.'),
        dict(id='marking-literal', image='detail', candidate='The photograph shows the marking aruba 10 on a blue kayak.',
             expected='Local visible marking/colour supported,without certifying task success or any minimum.'),
        dict(id='identity-unreadable-self-report', image='detail', candidate='I cannot confidently read the model name. The page lists a blue kayak for185.00dollars.',
             expected='Do not convert stated inability toread into a false object identity or automatic Mirage;local title/price still separate.'),
        dict(id='current-observed-price', image='detail', candidate='Based on what I observed here,the listing price is185.00dollars.',
             expected='Current-priced observation is not by itself an explicit historical item-price pairing;no all-history approval or minimum.'),
        dict(id='qualified-minimum', image='detail', candidate='This is the least expensive blue kayak I have identified so far;I have not established the whole-site minimum.',
             expected='Do not strengthen qualified best-found language into an unconditional globalminimum assertion.'),
        dict(id='global-minimum-unestablished', image='detail', candidate='This single detail image proves this is the cheapest blue kayak on the entire site.',
             expected='The single frame cannot establish this scope;unknown/insufficient proof,not invented evidence of a cheaper bluekayak.'),
        dict(id='intent-not-inspection', image='listing', candidate='I will inspect the rest of the listings and compare their prices.',
             expected='An intention is not a report of completed inspection or a concrete pastprice fact.'),
        dict(id='price-description-separation', image='listing', candidate='The three visible rows each display1.00dollar as their listing price;the descriptions mention other itemprices.',
             expected='Keep adjacent listingprice1 distinct from10/25/15/280-dollar descriptive claims;do not certify saleprice or globalordering.'),
        dict(id='focus-visible-border', image='input', candidate='The blue kayak text is visible inside a blue-bordered Keyword field.',
             expected='Visible text/border supported;do not require a false absent-border premise or certify OSfocus/execution.'),
        dict(id='focus-hidden-state', image='input', candidate='The blue border proves operating-system focus and that typing completed successfully.',
             expected='Border alone does not prove OSfocus or completed action;retain unknown hidden execution state.'),
        dict(id='native-wait', image='detail', candidate='I will wait.', native_action={'name':'wait','arguments':{}},
             expected='Pure nativeWAIT excluded from Mirage counting;no invented loading,link or verificationtask.'),
        dict(id='native-direction-conflict', image='listing', candidate='I will scroll up.', native_action={'name':'scroll','arguments':{'direction':'down'}},
             expected='Explicit prose/native direction conflict remains a separate native-action error;do not rewrite either action or pixels.')
    ]
    save(root / 'PRIVATE-control-expectations.json', dict(
        source_selected_nonblind_development=True, synthetic_counterfactuals_not_generated_actor_outputs=True,
        controls=controls, never_auxiliary_or_checker_input=True,
        not_independent_tasks_or_semantic_accuracy_denominator=True))
    safeguards = dict(
        all_prospective_auxiliary_bodies_only_complete_image_and_same_fixed_prompt=True,
        no_task_history_candidate_previous_reply_or_private_label_in_auxiliary_body=True,
        original_full_pixels_and_dimensions_verified=True,
        no_source_answer_tokens_in_generic_prompt=True,
        no_model_GUI_scorer_or_paid_calls=True,
        native_forward_ID_KV_release_and_GPU_fit_for_new_prompt_not_tested=True,
        proposed_prompt_unsent=True,
        existing32_and_all_running_conditions_unchanged=True,
        no_automatic_launcher_or_model_import_present=True)
    save(root / 'receipt.json', dict(schema='UNSENT-literal-marking-and-scope-controls-v1',
        time=time.time(), prior_summary_proposal_authority=old, packets=packets,
        safeguards=safeguards, controls=len(controls), distinct_known_source_images=3,
        proposed_change='Keep the prior complete-summary<=100-character request with the original strict180cap,and add task-independent exact visible objectmarkings/material uncertainty.',
        exact_tradeoff='With unchanged span/element caps,spending a textslot on an objectmarking may omit a navigation,statusorprice detail.Shorter summaries omit detail and do not guarantee complete or accurate generation.Tiny markings may be unreadable,and omission never proves absence.',
        source_routing_tradeoff='Any future narrower historical-price dispatch must preserve explicit past-price claims and ambiguous cases;dropping all-history checks solely because I observed is current could miss real historicalclaims.Nothing here changes that routing.',
        no_claim_of_source_literal_reading_repaired=True,
        fresh_distinct_source_controls_and_native_preflight_still_required_before_real_use=True,
        future_experimental_condition_not_approved_or_launched_by_this_receipt=True,
        no_completed_controls_or_terminal_trajectories_reexecuted=True,
        original_scope32_16pairs_8tasks_and_original_budgets_retained=True,
        efficacy_established=False, goal='active'))
    (root / 'report.md').write_text(
        '# 物体实印文字与断言范围：未发送的修复准备\n\n'
        '当前32轨继续使用固定v6。此包只准备新的通用提示与12条离线来源控制，0推理/GUI/scorer；没有重跑终局或旧完成控制。\n\n'
        '新提示在既有未发送短句草案上增加：读取照片物体上明确可辨的原文字样，与网页标题分开；小图材质/制作方法不可凭标题猜测。提示不含任务、具体物品或答案，辅助仍只接收完整原图与同一固定提示。\n\n'
        '来源控制覆盖错误型号/正确实印文字/自述读不清、当前价格与历史断言范围、限定最低价与未建立全局最低价、计划与完成、显示价与描述价、可见边框与隐藏焦点、纯native WAIT、prose/native方向冲突。三张实际完整原图SHA绑定，PRIVATE期望完全隔离。合成反事实不是主模型新生成结果，也不是独立任务或效力样本。\n\n'
        '代价明确：固定数量文字槽中优先实印文字可能挤掉导航/状态/价格细节；短摘要不能保证完整或正确，遗漏不证明不存在。历史价格缩小范围可能漏掉真正历史断言，此包未改路由。新提示未做原生ID/GPU预检，仍需不同来源的真实控制和条件审查，不可直接上线。\n', encoding='utf8')
    save(root / 'seal.json', {p.name:sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'),
                  seal_sha256=sha(root / 'seal.json'), new_model_GUI_scorer_calls=0)
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
