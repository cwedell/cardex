"""
train.py

Train EfficientNet-B3 on the VMMRdb generation-class dataset.

Usage:
    python train.py [options]

Options:
    --manifest FILE      Path to dataset_manifest.csv (default: dataset_manifest.csv)
    --labels FILE        Path to label_classes.json (default: label_classes.json)
    --root DIR           Project root; rel_path values are relative to this (default: .)
    --epochs INT         Number of training epochs (default: 30)
    --batch-size INT     Batch size (default: 64)
    --lr FLOAT           Initial learning rate (default: 1e-3)
    --min-images INT     Exclude classes with fewer than this many images (default: 50)
    --workers INT        DataLoader workers (default: 4)
    --log-interval INT   Print progress every N batches (default: 50)
    --out-dir DIR        Where to save checkpoints (default: checkpoints)
    --resume FILE        Resume from a checkpoint file
    --no-amp             Disable mixed-precision (FP16) training
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import models, transforms

from dataset import CarGenerationDataset


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def make_transforms():
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(256, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize(288),
        transforms.CenterCrop(256),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


# ---------------------------------------------------------------------------
# Dataset / loader helpers
# ---------------------------------------------------------------------------

def get_label_filter(manifest_path, min_images):
    """Return labels whose total image count across all splits >= min_images."""
    counts = Counter()
    import csv
    with open(manifest_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            counts[row["label"]] += 1
    return [lbl for lbl, cnt in counts.items() if cnt >= min_images]


def build_loaders(args):
    label_filter = get_label_filter(args.manifest, args.min_images)
    n_excluded = None
    with open(args.labels, encoding="utf-8") as f:
        lc = json.load(f)
    n_excluded = lc["num_classes"] - len(label_filter)

    print(f"Classes after filtering (>= {args.min_images} images): {len(label_filter)}")
    print(f"  Excluded {n_excluded} sparse classes")

    train_tf, val_tf = make_transforms()

    train_ds = CarGenerationDataset(
        args.manifest, args.root, split="train",
        transform=train_tf, label_filter=label_filter,
    )
    val_ds = CarGenerationDataset(
        args.manifest, args.root, split="val",
        transform=val_tf, label_filter=label_filter,
    )

    sampler = WeightedRandomSampler(
        weights=train_ds.get_class_weights(),
        num_samples=len(train_ds),
        replacement=True,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=args.workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size * 2,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=True,
    )

    return train_loader, val_loader, len(label_filter)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_model(num_classes):
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


# ---------------------------------------------------------------------------
# Training / evaluation
# ---------------------------------------------------------------------------

def run_epoch(model, loader, criterion, optimizer, scaler, device, use_amp,
              epoch, num_epochs, log_interval, phase):
    is_train = phase == "train"
    model.train() if is_train else model.eval()

    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    t0 = time.time()

    ctx = torch.enable_grad() if is_train else torch.no_grad()
    with ctx:
        for batch_idx, (images, labels) in enumerate(loader):
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            with autocast(enabled=use_amp):
                logits = model(images)
                loss = criterion(logits, labels)

            if is_train:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

            bs = images.size(0)
            total_loss += loss.item() * bs
            total_correct += (logits.argmax(1) == labels).sum().item()
            total_samples += bs

            if is_train and (batch_idx + 1) % log_interval == 0:
                elapsed = time.time() - t0
                avg_loss = total_loss / total_samples
                avg_acc = total_correct / total_samples * 100
                batches_done = batch_idx + 1
                batches_total = len(loader)
                lr = optimizer.param_groups[0]["lr"]
                print(
                    f"  Epoch [{epoch}/{num_epochs}]  "
                    f"Batch [{batches_done}/{batches_total}]  "
                    f"Loss: {avg_loss:.4f}  Acc: {avg_acc:.2f}%  "
                    f"LR: {lr:.2e}  Elapsed: {elapsed:.0f}s"
                )

    epoch_loss = total_loss / total_samples
    epoch_acc = total_correct / total_samples * 100
    return epoch_loss, epoch_acc


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def save_checkpoint(state, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, path)


def load_checkpoint(path, model, optimizer, scaler):
    ckpt = torch.load(path, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    scaler.load_state_dict(ckpt["scaler"])
    return ckpt["epoch"], ckpt["best_val_acc"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B3 on VMMRdb generation classes")
    parser.add_argument("--manifest",      default="dataset_manifest.csv", type=Path)
    parser.add_argument("--labels",        default="label_classes.json",   type=Path)
    parser.add_argument("--root",          default=".",                     type=Path)
    parser.add_argument("--epochs",        default=30,   type=int)
    parser.add_argument("--batch-size",    default=64,   type=int)
    parser.add_argument("--lr",            default=1e-3, type=float)
    parser.add_argument("--min-images",    default=50,   type=int)
    parser.add_argument("--workers",       default=4,    type=int)
    parser.add_argument("--log-interval",  default=50,   type=int)
    parser.add_argument("--out-dir",       default="checkpoints", type=Path)
    parser.add_argument("--resume",        default=None,  type=Path)
    parser.add_argument("--no-amp",        action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = not args.no_amp and device.type == "cuda"
    print(f"Device: {device}  |  AMP: {use_amp}")

    # Resolve manifest/labels relative to script directory if not absolute
    base = Path(__file__).parent
    if not args.manifest.is_absolute():
        args.manifest = base / args.manifest
    if not args.labels.is_absolute():
        args.labels = base / args.labels
    if not args.root.is_absolute():
        args.root = base / args.root

    print(f"Building data loaders ...")
    train_loader, val_loader, num_classes = build_loaders(args)
    print(f"  Train batches : {len(train_loader)}  ({len(train_loader.dataset)} samples)")
    print(f"  Val batches   : {len(val_loader)}  ({len(val_loader.dataset)} samples)")
    print(f"  Num classes   : {num_classes}")

    print(f"Building model (EfficientNet-B3, {num_classes} classes) ...")
    model = build_model(num_classes).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = GradScaler(enabled=use_amp)

    start_epoch = 1
    best_val_acc = 0.0

    if args.resume:
        print(f"Resuming from {args.resume} ...")
        start_epoch, best_val_acc = load_checkpoint(args.resume, model, optimizer, scaler)
        start_epoch += 1
        print(f"  Resuming at epoch {start_epoch}, best val acc so far: {best_val_acc:.2f}%")

    print(f"\n{'='*70}")
    print(f"Starting training: {args.epochs} epochs, batch {args.batch_size}, lr {args.lr}")
    print(f"{'='*70}\n")

    for epoch in range(start_epoch, args.epochs + 1):
        ep_t0 = time.time()

        train_loss, train_acc = run_epoch(
            model, train_loader, criterion, optimizer, scaler,
            device, use_amp, epoch, args.epochs, args.log_interval, "train",
        )

        val_loss, val_acc = run_epoch(
            model, val_loader, criterion, optimizer, scaler,
            device, use_amp, epoch, args.epochs, args.log_interval, "val",
        )

        scheduler.step()
        ep_elapsed = time.time() - ep_t0

        is_best = val_acc > best_val_acc
        if is_best:
            best_val_acc = val_acc

        print(
            f"\nEpoch {epoch}/{args.epochs} complete in {ep_elapsed:.0f}s\n"
            f"  Train  loss: {train_loss:.4f}  acc: {train_acc:.2f}%\n"
            f"  Val    loss: {val_loss:.4f}  acc: {val_acc:.2f}%"
            + ("  <-- best" if is_best else "")
            + f"\n  Best val acc so far: {best_val_acc:.2f}%\n"
        )

        ckpt_state = {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scaler": scaler.state_dict(),
            "best_val_acc": best_val_acc,
            "num_classes": num_classes,
        }
        save_checkpoint(ckpt_state, args.out_dir / "latest.pt")
        if is_best:
            save_checkpoint(ckpt_state, args.out_dir / "best.pt")
            print(f"  Saved best checkpoint to {args.out_dir / 'best.pt'}")

    print(f"\nTraining complete. Best val acc: {best_val_acc:.2f}%")
    print(f"Best checkpoint: {args.out_dir / 'best.pt'}")


if __name__ == "__main__":
    main()
