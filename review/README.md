# Agent-Mirage | Anonymous review code

This package accompanies *Agent-Mirage: From Visual Evidence Failures to Error Propagation in Multimodal Agents*. It contains selected experiment code, the browser test fixture, and measurements for independently recomputing the main benchmark table, the first-query attention comparisons, and the two observation-delivery results. It is an offline review artifact; it does not rerun entire trajectories or call any model service.

## Quick start

Use Python 3.11 or newer. From the extracted directory:

~~~sh
python -m pip install -r requirements.txt
python reproduce.py benchmark
python reproduce.py attention
python reproduce.py defense
python -m unittest discover -s tests -v
~~~

The benchmark and defense summaries use only the standard library. The attention analysis also needs NumPy. Pillow and cryptography are needed for the image and receipt code and its tests. All input data are included. No GPU, account, API key, network connection after installation, or private dataset path is required.

## Which evidence supports which numbers?

| Files | Computation and scope |
|---|---|
| `data/benchmark.json` | Original integer counts by model configuration, testbed, and intervention. Pooling counts gives 46.3% originally flagged and 62.1% task failures. The repair columns are historical aggregates; there is no per-run linkage to the gate experiment. |
| `observations.py` | Applies the missing, white, previous-frame, or annotated control-region intervention for offline analysis. A missing image means omitting the image block. A previous frame may happen to have identical pixels. The controls-only helper copies the supplied rectangles; it does not discover controls. |
| `data/attention.json` | Matched first-query language-attention mass for each model, task, position, history window, and condition in the ten-task OSWorld expansion. The script recomputes conditional history mass as (history prose + history action)/(1 − image), subtracts the matched clean value, averages three positions per task, and bootstraps whole tasks. Effects and intervals are in percentage points. Task UUIDs are public benchmark identifiers retained for the original reproducible resampling seed. |
| `data/full_task_exposures.json` | One row per confirmed faulty initial delivery in the audited full-task subset. A receipt or presence rejection and a usable replacement at the first actor forward are distinct. The enabled arm withheld 100% and recovered 94.1%. Exposure counts differ by arm. These are not trajectory-level Mirage reduction estimates. |
| `data/temporal_pairs.json`, `data/temporal_normal_controls.json` | Paired original and temporal policies in a separate browser study. Both arms really observed a premature first capture in the confirmed subset. Its within-window recovery was 90.0%; across all assigned delayed pairs, confirmed recovery was 75.0%. For usable fast-update, sparse, and boundary controls the initial false-hold rate was 6.25%. Null gate times indicate no delivery. |

## Verification implementation

The original attention collection code is included in `attention/run_attention.py`, with its action-span parser in `attention/action_audit.py`. It records language-layer attention alongside native generation and supports a baseline ID/logit preflight. Inspecting or recomputing the included measured comparisons does not require PyTorch or Transformers. A separate GPU replay with this optional runner needs a compatible local model and processor, its matching dependencies, a request plan and the original screenshot assets, which are not distributed here.

* `defense/gate_core.py` and `defense/receipt_protocol.py` implement the single-frame gate, same-decision recapture, native actor callback, and challenge-bound Ed25519 receipt checks. Freshly signed screenshots can still show the pre-update screen; identical pixels alone do not establish a replay.
* `defense/gate-contract.json` contains the frozen single-image YES/NO question and model revision. `defense/wire_contract.py` and `defense/temporal_request.py` construct the native verifier inputs. The temporal query receives the last accepted frame, one dispatched action, and the current candidate frame; neither interface receives the agent's reasoning history.
* `defense/temporal_controller.py` is the per-episode controller used in the browser panel. It checks presence and receipt first, then temporal consistency when applicable, then readability before forwarding. Its trusted boundary exception is specific to the static scroll fixture. Running the live controller requires capture and model-service adapters; those deployment services, weights, raw interaction histories, and private signing keys are not in this release.
* `examples/fixture.html` is the original self-contained browser fixture. To inspect a delayed state change, open the file in a browser with the query `?family=inventory&kind=toggle&mode=plain&delay=4500` and use the switch. A local fixture run is a demonstration, not a new measured trajectory.

The package reproduces the reported calculations from recorded measurements; it does not regenerate attention tensors, proprietary model outputs, or official task scores. Implementation tests use tiny generated images and ephemeral test keys; these fixtures are not observations from the experiments.

Original code in this package is distributed under the included MIT license. Third-party models, weights, benchmarks, and dependencies are not redistributed or relicensed here.
