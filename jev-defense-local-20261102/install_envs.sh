set -eu
cd /home/researcher/jev-defense-local-20261102
export PIP_CACHE_DIR="$PWD/pip-cache"
export TMPDIR="$PWD/tmp"
mkdir -p "$TMPDIR"
BASE=/opt/whz/conda-envs/webmall-vlm/bin/python
$BASE -m venv env-style
env-style/bin/python -m pip install 'torch==2.14.1' 'torchvision==0.29.1' --index-url https://download.pytorch.org/whl/cu126
env-style/bin/python -m pip install 'transformers==5.17.0' 'tokenizers==0.23.3' 'numpy==2.5.4' 'pillow==13.0.0' 'safetensors==0.8.0'
env-style/bin/python -m pip freeze > env-style-freeze.txt
$BASE -m venv env-neohorse
env-neohorse/bin/python -m pip install 'torch==2.8.0' --index-url https://download.pytorch.org/whl/cu126
env-neohorse/bin/python -m pip install 'transformers==5.17.0' 'safetensors==0.8.0' 'pydantic==2.13.5' 'pillow==12.3.0'
env-neohorse/bin/python -m pip freeze > env-neohorse-freeze.txt
