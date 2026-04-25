"""
build_manifest.py

Scans VMMRdb/, joins against generation_map.json, performs a stratified
train/val/test split, and writes:
  - dataset_manifest.csv   (one row per image)
  - label_classes.json     (label <-> index mapping + metadata)

Usage:
    python build_manifest.py [options]

Options:
    --vmm-root DIR        VMMRdb directory (default: VMMRdb)
    --map FILE            generation_map.json path (default: generation_map.json)
    --out-csv FILE        output CSV path (default: dataset_manifest.csv)
    --out-labels FILE     output label JSON path (default: label_classes.json)
    --seed INT            random seed for split (default: 42)
    --val-frac FLOAT      fraction for validation split (default: 0.1)
    --test-frac FLOAT     fraction for test split (default: 0.1)
    --group-by-folder     keep all images from one source folder in the same split
    --verify              after writing, verify every row is valid
"""

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def scan_images(vmm_root: Path, gen_map: dict) -> list:
    """
    Walk each folder listed in gen_map. For each image file emit a dict:
        rel_path      forward-slash path relative to project root
        label         human-readable generation label
        source_folder folder name (make_model_year)
    Warns to stderr for folders in the map but missing on disk.
    """
    records = []
    project_root = vmm_root.parent
    for folder_name, label in gen_map.items():
        folder_path = vmm_root / folder_name
        if not folder_path.is_dir():
            print(f"WARNING: {folder_name} in generation_map but not found on disk", file=sys.stderr)
            continue
        with os.scandir(folder_path) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                if Path(entry.name).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                rel = Path(entry.path).relative_to(project_root)
                records.append({
                    "rel_path": rel.as_posix(),
                    "label": label,
                    "source_folder": folder_name,
                })
    return records


def build_label_index(records: list) -> dict:
    """Return {label: idx} sorted alphabetically. Deterministic."""
    labels = sorted({r["label"] for r in records})
    return {label: idx for idx, label in enumerate(labels)}


def stratified_split(records: list, label_index: dict, seed: int,
                     val_frac: float, test_frac: float,
                     group_by_folder: bool) -> list:
    """
    Assign a 'split' key ('train'/'val'/'test') to each record in place.
    Strategy:
      - Sparse classes (< 3 images): all train
      - 3-5 images: 1 val, 1 test, rest train
      - Otherwise: proportional random split, per class
    group_by_folder: treat all images in the same source_folder as a unit;
                     the whole folder goes to one split (prevents year-leakage).
    """
    rng = random.Random(seed)

    # Group records by label
    by_label = defaultdict(list)
    for r in records:
        by_label[r["label"]].append(r)

    for label, recs in by_label.items():
        if group_by_folder:
            _split_by_folder(recs, rng, val_frac, test_frac)
        else:
            _split_flat(recs, rng, val_frac, test_frac)

    return records


def _split_flat(recs: list, rng: random.Random, val_frac: float, test_frac: float):
    """Split image-by-image within one class."""
    rng.shuffle(recs)
    n = len(recs)
    if n < 3:
        for r in recs:
            r["split"] = "train"
        return
    if n <= 5:
        recs[0]["split"] = "val"
        recs[1]["split"] = "test"
        for r in recs[2:]:
            r["split"] = "train"
        return
    n_val = max(1, round(n * val_frac))
    n_test = max(1, round(n * test_frac))
    n_train = n - n_val - n_test
    if n_train < 1:
        # If rounding causes all images to go to val/test, force at least 1 train
        n_val = max(0, n_val - 1)
        n_train = n - n_val - n_test
    for r in recs[:n_val]:
        r["split"] = "val"
    for r in recs[n_val:n_val + n_test]:
        r["split"] = "test"
    for r in recs[n_val + n_test:]:
        r["split"] = "train"


def _split_by_folder(recs: list, rng: random.Random, val_frac: float, test_frac: float):
    """
    Group recs by source_folder, shuffle the groups, then assign whole groups
    to splits until the fractions are met.
    """
    by_folder = defaultdict(list)
    for r in recs:
        by_folder[r["source_folder"]].append(r)

    folders = list(by_folder.items())
    rng.shuffle(folders)
    n_total = len(recs)

    if n_total < 3:
        for r in recs:
            r["split"] = "train"
        return

    target_val = max(1, round(n_total * val_frac))
    target_test = max(1, round(n_total * test_frac))

    val_count = test_count = 0
    for folder_name, folder_recs in folders:
        if val_count < target_val:
            split = "val"
            val_count += len(folder_recs)
        elif test_count < target_test:
            split = "test"
            test_count += len(folder_recs)
        else:
            split = "train"
        for r in folder_recs:
            r["split"] = split


def write_csv(records: list, out_path: Path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["rel_path", "label", "label_idx", "split", "source_folder"],
        )
        writer.writeheader()
        writer.writerows(records)


def write_label_classes(label_index: dict, records: list, out_path: Path):
    split_counts = defaultdict(int)
    for r in records:
        split_counts[r["split"]] += 1

    idx_to_label = {str(v): k for k, v in label_index.items()}
    payload = {
        "label_to_idx": label_index,
        "idx_to_label": idx_to_label,
        "num_classes": len(label_index),
        "build_date": date.today().isoformat(),
        "total_images": len(records),
        "split_counts": dict(split_counts),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def verify(csv_path: Path, label_classes_path: Path, project_root: Path) -> bool:
    print("\n--- Verification ---")
    ok = True

    with open(label_classes_path, encoding="utf-8") as f:
        lc = json.load(f)
    label_to_idx = lc["label_to_idx"]

    seen_paths = set()
    split_counts = defaultdict(int)
    label_counts = defaultdict(int)
    errors = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rel = row["rel_path"]
            abs_path = project_root / rel
            if not abs_path.exists():
                print(f"  ERROR row {i}: file not found: {abs_path}", file=sys.stderr)
                errors += 1
                ok = False
                if errors > 20:
                    print("  (too many missing files, stopping check)", file=sys.stderr)
                    break
            if rel in seen_paths:
                print(f"  ERROR row {i}: duplicate rel_path: {rel}", file=sys.stderr)
                ok = False
            seen_paths.add(rel)

            expected_idx = label_to_idx.get(row["label"])
            if expected_idx is None:
                print(f"  ERROR row {i}: label not in label_classes: {row['label']}", file=sys.stderr)
                ok = False
            elif int(row["label_idx"]) != expected_idx:
                print(f"  ERROR row {i}: label_idx mismatch for {row['label']}", file=sys.stderr)
                ok = False

            split_counts[row["split"]] += 1
            label_counts[row["label"]] += 1

    total = sum(split_counts.values())
    print(f"  Total rows : {total}")
    print(f"  Unique paths: {len(seen_paths)}")
    print(f"  Split counts: {dict(split_counts)}")
    print(f"  Unique labels in CSV: {len(label_counts)}")
    print(f"  num_classes in JSON : {lc['num_classes']}")

    # Warn on sparse classes
    sparse = [(lbl, cnt) for lbl, cnt in label_counts.items() if cnt < 20]
    if sparse:
        print(f"  WARNING: {len(sparse)} classes have fewer than 20 images total")

    # Check label index is contiguous
    indices = sorted(label_to_idx.values())
    if indices != list(range(len(indices))):
        print("  ERROR: label indices are not contiguous 0..N-1", file=sys.stderr)
        ok = False

    if ok:
        print("  All checks passed.")
    else:
        print("  Verification FAILED — see errors above.", file=sys.stderr)
    return ok


def main():
    parser = argparse.ArgumentParser(description="Build dataset manifest CSV from VMMRdb + generation_map.json")
    parser.add_argument("--vmm-root",    default="VMMRdb",                type=Path)
    parser.add_argument("--map",         default="generation_map.json",   type=Path)
    parser.add_argument("--out-csv",     default="dataset_manifest.csv",  type=Path)
    parser.add_argument("--out-labels",  default="label_classes.json",    type=Path)
    parser.add_argument("--seed",        default=42,    type=int)
    parser.add_argument("--val-frac",    default=0.1,   type=float)
    parser.add_argument("--test-frac",   default=0.1,   type=float)
    parser.add_argument("--group-by-folder", action="store_true",
                        help="Keep all images from a source folder in the same split")
    parser.add_argument("--verify",      action="store_true",
                        help="Verify output CSV after writing")
    args = parser.parse_args()

    # Resolve paths relative to this script's directory
    base = Path(__file__).parent
    vmm_root    = base / args.vmm_root
    map_path    = base / args.map
    out_csv     = base / args.out_csv
    out_labels  = base / args.out_labels

    print(f"Loading {map_path} ...")
    with open(map_path, encoding="utf-8") as f:
        gen_map = json.load(f)
    print(f"  {len(gen_map)} entries in generation map")

    print(f"Scanning images in {vmm_root} ...")
    records = scan_images(vmm_root, gen_map)
    print(f"  {len(records)} images found")

    label_index = build_label_index(records)
    print(f"  {len(label_index)} unique generation labels")

    # Attach label_idx to each record
    for r in records:
        r["label_idx"] = label_index[r["label"]]

    print(f"Splitting (seed={args.seed}, val={args.val_frac}, test={args.test_frac}, "
          f"group_by_folder={args.group_by_folder}) ...")
    stratified_split(records, label_index, args.seed, args.val_frac, args.test_frac,
                     args.group_by_folder)

    # Count sparse classes
    label_counts = defaultdict(int)
    for r in records:
        label_counts[r["label"]] += 1
    n_sparse = sum(1 for c in label_counts.values() if c < 20)
    if n_sparse:
        print(f"  WARNING: {n_sparse} classes have fewer than 20 images (all assigned to train)")

    print(f"Writing {out_csv} ...")
    write_csv(records, out_csv)

    print(f"Writing {out_labels} ...")
    write_label_classes(label_index, records, out_labels)

    # Summary
    from collections import Counter
    splits = Counter(r["split"] for r in records)
    print(f"\nDone.")
    print(f"  Classes : {len(label_index)}")
    print(f"  Images  : {len(records)}")
    print(f"  train   : {splits['train']}")
    print(f"  val     : {splits['val']}")
    print(f"  test    : {splits['test']}")

    if args.verify:
        success = verify(out_csv, out_labels, base)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
