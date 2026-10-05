Put a detection model in models/default/ before building, or run:

    python scripts/fetch_model.py

The shipped model is our per-channel int8 clinical build; install it with:

    scripts/install_model.sh models/scotoma-v0-int8pc 0.02 clinical

The folder needs: model_quantized.onnx (or model.onnx), tokenizer.json,
config.json. A config.json may carry "scotoma_threshold" (and
"scotoma_domain") to set the default redaction threshold this model runs at;
0.02 is the clinical operating point. Without it the app still works, on
rules alone, and says so in the window.
Shipped model: v1-small (sha256 f3ea1a68...), installed with scripts/install_model.sh models/v1-small 0.02 on 2026-10-05 after sealed evaluation 2.
