"""Freeze distinct archived complete images and exact provenance for new controls.

Observer only. Does not run archived experiments, a browser, or a model. Original
responses and source-selection annotations are evaluation provenance, never an
auxiliary input. No semantic labels or live-readiness claim are produced here.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import time

import orchestrate


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf8')


SOURCE = r'''
from pathlib import Path
import base64,copy,hashlib,json,os
base=Path('/data/researcher/attention-audit-20261031')
assets=base/'inputs/mirage-trace/_shared/input-images/_embedded-input-images'
assert os.getuid()==1015 and assets.is_dir()
def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
out=[]
for row in ROWS:
 source=(base/row['source_artifact']).resolve()
 assert source.is_relative_to(base.resolve()) and source.is_file()
 raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['source_artifact_sha256']
 data=json.loads(raw);request=copy.deepcopy(data['body'])
 for message in request['messages']:
  if isinstance(message['content'],list):
   for block in message['content']:
    if block.get('type')=='image_url':
     original=block['image_url']['url'];assert original.startswith('blob:sha256:')
     block['image_url']['url']='archive-image://sha256/'+original.split(':')[-1]
 assert hashlib.sha256(canonical(request)).hexdigest()==row['exported_request_canonical_sha256']
 current=[image for image in data['images']if image['current']]
 assert len(current)==1 and current[0]['sha256']==row['current_image_sha256']
 item=current[0]
 assert data['body']['messages'][item['mi']]['content'][item['bi']]['image_url']['url']=='blob:sha256:'+item['sha256']
 files={'evaluation-only/original-source-artifact.json':base64.b64encode(raw).decode(),
        'evaluation-only/original-request.json':base64.b64encode(canonical(data['body'])).decode()}
 bindings=[]
 for image in data['images']:
  digest=image['sha256'];candidates=sorted(assets.glob('*/'+digest+'.*'))
  assert candidates,('missing original image',digest)
  path=candidates[0];assert path.resolve().is_relative_to(base.resolve())
  picture=path.read_bytes();assert hashlib.sha256(picture).hexdigest()==digest
  assert len(picture)==image['bytes']
  name='originals/'+digest+'.png';files[name]=base64.b64encode(picture).decode()
  bindings.append(dict(image,original_file=str(path),local_file=name))
 out.append(dict(id=row['id'],source_artifact=str(source),
  source_artifact_sha256=row['source_artifact_sha256'],current_image_sha256=item['sha256'],
  current_message_index=item['mi'],current_block_index=item['bi'],bindings=bindings,files_base64=files,
  native_body_exported_request_canonical_identity_verified=True))
print(json.dumps({'rows':out,'remote_uid':os.getuid(),'read_only':True,
 'source_replies_are_private_provenance_not_reviewed_or_auxiliary_input':True,
 'new_model_GUI_capture_action_scorer_paid_calls':0}))
'''


def main():
    root = orchestrate.HERE
    pointer = root / 'distinct-archived-current-frames-created.json'
    assert not pointer.exists(), 'Inspect the completed source freeze; do not repeat it'
    original = Path('D:/MultiModel/attention-audit-20261102/source-raw.json')
    rows = json.loads(original.read_bytes())
    wanted = ['S08-03', 'S09-03', 'S10-03', 'S11-03']
    selected = []
    for ident in wanted:
        row = next(value for value in rows if value['id'] == ident)
        refs = [block['image_url']['url'] for message in row['request']['messages']
                if isinstance(message['content'], list) for block in message['content']
                if block.get('type') == 'image_url']
        assert refs and all(value.startswith('archive-image://sha256/') for value in refs)
        selected.append(dict(
            **{key: row[key] for key in ['id', 'task', 'source_artifact', 'source_artifact_sha256']},
            current_image_sha256=refs[-1].rsplit('/', 1)[-1],
            exported_request_canonical_sha256=hashlib.sha256(canonical(row['request'])).hexdigest()))
    plan = json.loads((orchestrate.PACKAGE / 'plan.json').read_bytes())
    current_tasks = [task['pilot_task_id'] for task in plan['tasks']['vwa']]
    assert all(value['task'] not in current_tasks for value in selected)
    target = root / ('distinct-archived-current-frames-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(target / 'intent.json', dict(
        selection='First followup step03 in four explicit archived Reddit task sources; deterministic selected nonblind development, not random independent efficacy sampling.',
        source_index=str(original), source_index_sha256=orchestrate.sha(original), selected=selected,
        original32_tasks=current_tasks, original32_plan_sha256=orchestrate.sha(orchestrate.PACKAGE / 'plan.json'),
        no_existing_terminal_or_attention_queue_execution=True,
        no_auxiliary_semantic_or_native_WAIT_control_pass_claim=True))
    try:
        output, operation = orchestrate.remote('4090', 'ROWS=' + repr(selected) + '\n' + SOURCE,
            'freeze-distinct-complete-archived-source-images-no-model-or-GUI', timeout=55)
        result = json.loads(output)
        for row in result['rows']:
            folder = target / row['id']
            for name, encoded in row.pop('files_base64').items():
                destination = folder / name
                assert destination.resolve().is_relative_to(target.resolve())
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(base64.b64decode(encoded, validate=True))
            assert orchestrate.sha(folder / 'evaluation-only/original-source-artifact.json') == row['source_artifact_sha256']
            for image in row['bindings']:
                assert orchestrate.sha(folder / image['local_file']) == image['sha256']
            current = folder / 'originals' / (row['current_image_sha256'] + '.png')
            from PIL import Image
            with Image.open(current) as picture:
                row['current_original_size'] = list(picture.size)
            row['current_local_file'] = str(current)
            row['model_input_prepared'] = False
        result.update(remote_operation=str(operation), input_images_complete_and_unmodified=True,
            semantic_source_review_required=True, source_labels_not_created=True,
            fixed_generic_prompt_change_or_formal32_change=False,
            native_WAIT_negative_normal_control_package_ready=False,
            real_GPU_inference_or_defense_efficacy_established=False)
        orchestrate.save(target / 'receipt.json', result)
    except BaseException as error:
        orchestrate.save(target / 'failure.json', dict(error_type=type(error).__name__, error=str(error),
            original_inputs_and_experiments_unchanged=True, new_model_GUI_calls=0))
        orchestrate.save(target / 'seal.json', {p.relative_to(target).as_posix(): orchestrate.sha(p)
            for p in target.rglob('*') if p.is_file()})
        raise
    orchestrate.save(target / 'seal.json', {p.relative_to(target).as_posix(): orchestrate.sha(p)
        for p in target.rglob('*') if p.is_file()})
    authority = dict(root=str(target), receipt_sha256=orchestrate.sha(target / 'receipt.json'),
                     seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, authority)
    print(json.dumps(dict(authority, current_images=[dict(id=row['id'],
        sha256=row['current_image_sha256'],size=row['current_original_size'],path=row['current_local_file'])
        for row in result['rows']], new_model_GUI_calls=0), ensure_ascii=True))


if __name__ == '__main__':
    main()
