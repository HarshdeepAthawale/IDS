# SecIDS-CNN input/output contract

## Discovery script

After placing `SecIDS-CNN.h5` in `SecIDS-CNN/` (or setting `SECIDS_MODEL_PATH`), run:

```bash
cd backend
python scripts/inspect_secids_model.py
```

The script prints:

- `model.input_shape` – e.g. `(None, N_features)` for flat input or `(None, T, F)` for temporal.
- `model.output_shape` – e.g. `(None, 1)` for single probability (malicious) or `(None, 2)` for two-class.
- A dummy run to confirm output format.

## Expected contract (from SecIDS-CNN README)

- **Input:** Flow/temporal network features (e.g. Packet_Length_Mean, Flow_Duration). Exact feature list and order depend on the model’s training data; use the discovery script to get the feature count and shape.
- **Output:** The repo wrapper uses threshold 0.5 on the model output: `"Attack"` if pred > 0.5 else `"Benign"`. So the model likely outputs a single probability (malicious) per sample. The adapter maps `Attack` → `malicious`, `Benign` → `benign` and derives `[p_benign, p_malicious]` as `[1-p, p]`.

## Feature mapping

- **CICIDS-style data:** Our preprocessor produces 39–79 features. The adapter builds a vector in the order expected by SecIDS (from discovery or a fixed list). Missing features → 0; extra features dropped.
- **Real-time packet features:** Our feature_extractor produces ~6 core features. If SecIDS expects a different set (e.g. flow-level only), use SecIDS only in contexts where CICIDS-like features are available (e.g. PCAP/batch) or document the limitation.
