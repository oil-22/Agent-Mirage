set -eu
cd /home/researcher/jev-defense-local-20261102
export PIP_CACHE_DIR="$PWD/pip-cache"
export TMPDIR="$PWD/tmp"
# Python 3.11 is supported by the model interface. NumPy 2.5 requires 3.12;
# record 2.4.6 as a deployment dependency deviation, not an algorithm alteration.
env-style/bin/python -m pip install 'transformers==5.17.0' 'tokenizers==0.23.3' 'numpy==2.4.6' 'pillow==13.0.0' 'safetensors==0.8.0'
env-style/bin/python -m pip freeze > env-style-freeze.txt
