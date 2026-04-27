"""
assign_rarity.py

Reconstructs the model's class mapping (filtered + sorted subset of VMMRdb),
assigns a rarity tier to each class, and writes web/public/car_data.json.

The class index (idx) written here must match the model's output indices.
The model is trained with --min-images N (default 50), which filters classes
and remaps them alphabetically to 0..K-1 (see dataset.py CarGenerationDataset).
This script applies the same filter so the indices align.

Rarity tiers (ascending):
  common     – mass-market models, high training-image volume
  uncommon   – everything else; default for unknown brands
  rare       – performance/luxury brands
  epic       – exotic brands
  legendary  – ultra-rare marques

Usage:
    python scripts/assign_rarity.py [--min-images N]

Output:
    web/public/car_data.json
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
MANIFEST_FILE = ROOT / "dataset_manifest.csv"
OUT = ROOT / "web" / "public" / "car_data.json"

# ─── Brand → rarity overrides (checked first, case-insensitive prefix match) ──

LEGENDARY_BRANDS = {
    "Bugatti", "Koenigsegg", "Pagani", "SSC",
    "Hennessey", "Rimac", "Czinger",
}

EPIC_BRANDS = {
    "Ferrari", "Lamborghini", "McLaren", "Rolls-Royce",
    "Bentley", "Aston Martin", "Lotus",
}

RARE_BRANDS = {
    "Porsche", "Jaguar", "Maserati", "Alfa Romeo",
    "Land Rover", "Morgan",
}

# Specific label substrings that bump rarity regardless of brand
RARE_KEYWORDS = {
    "Viper", "Corvette ZR1", "Corvette Z06", "Shelby",
    "AMG GT", "M3", "M4", "M5", "M6", "M8",
    "RS ", "GT3", "GT4", "GTS",
}

# Multi-word brands that must be matched as a prefix
MULTI_WORD_BRANDS = [
    "AM General", "Land Rover", "Rolls-Royce", "Aston Martin",
    "Alfa Romeo", "Mercedes-Benz",
]

# ── Volume thresholds (images in full dataset) ────────────────────────────────
COMMON_THRESHOLD_PERCENTILE = 60   # top 40% by image count → common


def extract_make(label: str) -> str:
    for brand in MULTI_WORD_BRANDS:
        if label.lower().startswith(brand.lower()):
            return brand
    return label.split()[0]


def brand_rarity(make: str) -> str | None:
    make_l = make.lower()
    for b in LEGENDARY_BRANDS:
        if b.lower() == make_l:
            return "legendary"
    for b in EPIC_BRANDS:
        if b.lower() == make_l:
            return "epic"
    for b in RARE_BRANDS:
        if b.lower() == make_l:
            return "rare"
    return None


def keyword_rarity(label: str) -> str | None:
    for kw in RARE_KEYWORDS:
        if kw.lower() in label.lower():
            return "rare"
    return None


RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]


def max_rarity(*tiers: str | None) -> str:
    candidates = [t for t in tiers if t is not None]
    if not candidates:
        return "uncommon"
    return max(candidates, key=lambda t: RARITY_ORDER.index(t))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--min-images", type=int, default=50,
        help="Minimum images per class — must match the value used in train.py (default: 50)"
    )
    args = parser.parse_args()

    print(f"Counting images per label from {MANIFEST_FILE} ...")
    image_counts: Counter = Counter()
    with open(MANIFEST_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            image_counts[row["label"]] += 1
    print(f"  {sum(image_counts.values())} total images, {len(image_counts)} unique labels")

    # Reconstruct the exact same class mapping as CarGenerationDataset:
    # filter to labels with >= min_images, then sort alphabetically → idx 0..K-1
    filtered_labels = sorted(
        lbl for lbl, cnt in image_counts.items() if cnt >= args.min_images
    )
    label_to_idx = {lbl: i for i, lbl in enumerate(filtered_labels)}
    print(f"  After filtering (>= {args.min_images} images): {len(filtered_labels)} classes")
    print(f"  Excluded {len(image_counts) - len(filtered_labels)} sparse classes")

    # Determine the volume threshold for "common"
    filtered_counts = sorted(image_counts[lbl] for lbl in filtered_labels)
    threshold_idx = int(len(filtered_counts) * COMMON_THRESHOLD_PERCENTILE / 100)
    common_threshold = filtered_counts[threshold_idx] if filtered_counts else 0
    print(f"  Common threshold: >= {common_threshold} images (top {100 - COMMON_THRESHOLD_PERCENTILE}%)")

    print("Assigning rarities ...")
    cars = []
    for label, idx in sorted(label_to_idx.items(), key=lambda x: x[1]):
        make = extract_make(label)
        img_count = image_counts.get(label, 0)

        b_rarity = brand_rarity(make)
        k_rarity = keyword_rarity(label)
        vol_rarity = "common" if img_count >= common_threshold else None

        rarity = max_rarity(b_rarity, k_rarity, vol_rarity)

        cars.append({
            "idx": idx,
            "label": label,
            "make": make,
            "rarity": rarity,
            "rarityRank": RARITY_ORDER.index(rarity),
            "imageCount": img_count,
        })

    tier_counts = Counter(c["rarity"] for c in cars)
    for tier in RARITY_ORDER:
        print(f"  {tier:12s}: {tier_counts.get(tier, 0)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\nWrote {len(cars)} entries to {OUT}  ({OUT.stat().st_size / 1e3:.0f} KB)")
    print("Next: cd web && npm run dev")


if __name__ == "__main__":
    main()
