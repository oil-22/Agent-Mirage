# Jev trajectory dataset code

| Version | Source |
| --- | --- |
| v1 | [Extraction, archive alignment, and pairing](jev-trajectory-v1/) |
| v2 | [Collection, matched controls, assembly, and validation](jev-trajectory-v2/build/) |
| v2.1 | [Validation extension and review](jev-trajectory-v2.1/build/) |
| v3 | [Balanced split construction](jev-trajectory-v3/build/), [input verifier](jev-trajectory-v3/verify.py), [dataset documentation](jev-trajectory-v3/README.md) |

The version directories contain build and verification code, protocol metadata, and the original dataset guides. Links in those guides to PNGs, training manifests, receipts, and audit records refer to the separate data bundles. The historical builders read the source observations and annotations from their respective experiments.

For LoRA training, extract the complete v3 bundle into its own directory and pass that directory to the trainer with `--data`. It must contain the supplied manifests and the `images/` directory; preserve their relative paths. Do not combine v3 with the earlier splits.
