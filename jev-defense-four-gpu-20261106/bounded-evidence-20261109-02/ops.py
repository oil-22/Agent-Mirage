from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
spec=importlib.util.spec_from_file_location('immutable_remote_transport',BASE/'full-gui-single-evidence-20261108-01/remote_control.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
transport.HERE=HERE
remote=transport.remote
save=transport.save
sha=transport.sha
ROOT='/home/researcher/jev-defense-four-gpu-20261106/bounded-evidence-20261109-02'
PACKAGE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/bounded-evidence-20261109-02'
GUI_ROOT='/data/researcher/jev-defense-four-gpu-20261106/bounded-evidence-20261109-02'
