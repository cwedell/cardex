"""
export_onnx.py

Exports the trained EfficientNet-B3 checkpoint to a self-contained FP32 ONNX
model suitable for in-browser inference via onnxruntime-web.

INT8 dynamic quantization is intentionally skipped: EfficientNet-B3's
depthwise separable convolutions are highly sensitive to weight quantization,
and dynamic INT8 reduces top-1 accuracy from ~92% to near-random (~4%).
The FP32 model (~47 MB) is the right tradeoff for correct predictions.

Usage:
    python scripts/export_onnx.py

Output:
    web/public/model.onnx         (FP32, self-contained, ~47 MB)
    web/public/model_classes.json (ordered class list matching model output indices)

Requirements:
    pip install torch torchvision onnx
"""

import io
import json
from pathlib import Path

import onnx
import torch
import torch.nn as nn
from torchvision import models

ROOT        = Path(__file__).parent.parent
CHECKPOINT  = ROOT / "checkpoints" / "best.pt"
OUT         = ROOT / "web" / "public" / "model.onnx"
CLASSES_OUT = ROOT / "web" / "public" / "model_classes.json"

INPUT_SIZE = 256  # must match val_tf CenterCrop in train.py


def build_model(num_classes: int) -> nn.Module:
    model = models.efficientnet_b3(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def main():
    print(f"Loading checkpoint: {CHECKPOINT}")
    ckpt = torch.load(CHECKPOINT, map_location="cpu")
    num_classes: int = ckpt["num_classes"]
    best_val_acc: float = ckpt.get("best_val_acc", 0.0)
    classes: list[str] | None = ckpt.get("classes")
    print(f"  num_classes : {num_classes}")
    print(f"  best_val_acc: {best_val_acc:.2f}%")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    if classes:
        print(f"  class list  : {len(classes)} labels stored in checkpoint")
        with open(CLASSES_OUT, "w", encoding="utf-8") as f:
            json.dump(classes, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  Wrote class list to {CLASSES_OUT}")
    else:
        print("  WARNING: checkpoint has no 'classes' key — re-run train.py to save it")

    print("Building model and loading weights...")
    model = build_model(num_classes)
    model.load_state_dict(ckpt["model"])
    model.eval()

    # Export to BytesIO first — forces all weight tensors inline (no .data sidecar)
    print("Exporting FP32 ONNX to memory buffer ...")
    dummy = torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)
    buf = io.BytesIO()
    torch.onnx.export(
        model, dummy, buf,
        input_names=["input"],
        output_names=["logits"],
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    fp32_mb = buf.getbuffer().nbytes / 1e6
    print(f"  In-memory size: {fp32_mb:.1f} MB")

    # Save self-contained FP32 to disk (save_as_external_data=False by default)
    buf.seek(0)
    onnx_proto = onnx.load(buf)
    onnx.save(onnx_proto, str(OUT))
    print(f"  Saved to {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")

    print(f"\nDone. Model saved to: {OUT}")
    print("Next: run  python scripts/assign_rarity.py")


if __name__ == "__main__":
    main()
