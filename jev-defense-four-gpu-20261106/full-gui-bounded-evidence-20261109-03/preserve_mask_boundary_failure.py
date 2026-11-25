from prepare import HERE,RUNTIME,save,sha
import shutil

root=HERE/'mask-empty-array-boundary-failure-01';root.mkdir(exist_ok=False)
shutil.copy2(HERE/'test_no_reference_mask.py',root/'original-test.py')
shutil.copy2(HERE.parent/'bounded-evidence-20261109-02/runtime-package/grammar-vendor/lmformatenforcer/jsonschemaparser.py',root/'original-vendor-jsonschemaparser.py')
save(root/'receipt.json',{'observed_CPU_assertion':'maxItems=0 still allowed first reference array item',
    'source_test_sha256':sha(root/'original-test.py'),'original_vendor_sha256':sha(root/'original-vendor-jsonschemaparser.py'),
    'task_local_fixed_vendor_sha256':sha(RUNTIME/'grammar-vendor/lmformatenforcer/jsonschemaparser.py'),
    'repair':'Only maxItems=0 pushes a whitespace-capable empty parser instead of item union',
    'models_GPU_GUI_calls':0,'shared_environment_or_prior_terminal_modified':False})
print('CPU boundary failure source preserved; private vendor fix only.')
