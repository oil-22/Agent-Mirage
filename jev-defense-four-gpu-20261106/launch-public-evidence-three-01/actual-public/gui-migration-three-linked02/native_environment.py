"""Exact native GUI environment from the already-successful transport preflight."""
PARENT_PREFLIGHT_SOURCE_SHA256='1ac2b1371ce82bdf297a113b97e9e40ade47b0bead6691d6d6f7f99083d055f2'
NATIVE_ENV={
    'CUDA_VISIBLE_DEVICES':'', 'OMP_NUM_THREADS':'2', 'OPENBLAS_NUM_THREADS':'2',
    'DATASET':'visualwebarena', 'CLASSIFIEDS':'http://192.0.2.10:29980',
    'REDDIT':'http://192.0.2.10:29999', 'SHOPPING':'http://127.0.0.1:1',
    'WIKIPEDIA':'http://127.0.0.1:1', 'HOMEPAGE':'http://127.0.0.1:1',
    'CLASSIFIEDS_RESET_TOKEN':'unused-no-site-reset',
    'REDDIT_RESET_URL':'http://127.0.0.1:1/no-reset',
    'OPENAI_API_KEY':'unused-local-url-evaluator', 'OPENAI_BASE_URL':'http://127.0.0.1:1/v1',
    'PLAYWRIGHT_BROWSERS_PATH':'/data/researcher/playwright-browsers'}
