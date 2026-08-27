#!/usr/bin/env python3
from pathlib import Path
import base64

root = Path(__file__).resolve().parent
src_dir = root / "binary_assets_v9"
out_dir = root / "generated_assets_v9"
out_dir.mkdir(parents=True, exist_ok=True)

assets = {
    "frog_helmet_mask": "frog_helmet_mask.webp",
    "ftf_home_frog": "ftf_home_frog.webp",
    "ftf_poison_frog_fixed": "ftf_poison_frog_fixed.webp",
}

for prefix, filename in assets.items():
    parts = sorted(src_dir.glob(f"{prefix}_*.b64"))
    if not parts:
        raise SystemExit(f"missing v0.8.5 asset chunks for {prefix}")
    encoded = "".join(p.read_text().strip() for p in parts)
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"invalid base64 for {prefix}: {exc}")
    if len(data) < 16 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise SystemExit(f"invalid WebP container for {prefix}")
    output = out_dir / filename
    output.write_bytes(data)
    print(f"reconstructed {filename}: {len(data)} bytes from {len(parts)} chunks")
