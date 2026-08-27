#!/usr/bin/env python3
from pathlib import Path
import base64
import struct

root = Path(__file__).resolve().parent
src = root / "binary_assets_v10"
out = root / "generated_assets_v11"
out.mkdir(exist_ok=True)

parts = sorted(src.glob("homev2_*.b64"))
if not parts:
    raise SystemExit("missing v0.8.8 home-screen chunks")

encoded = "".join(p.read_text().strip() for p in parts)
try:
    data = base64.b64decode(encoded, validate=True)
except Exception as exc:
    raise SystemExit(f"homev2 base64 decode failed: {exc}")

if len(data) < 32 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
    raise SystemExit("homev2 is not a complete JPEG")

pos = 2
width = height = None
while pos + 4 <= len(data):
    if data[pos] != 0xFF:
        pos += 1
        continue
    while pos < len(data) and data[pos] == 0xFF:
        pos += 1
    if pos >= len(data):
        break
    marker = data[pos]
    pos += 1
    if marker in (0xD8, 0xD9):
        continue
    if marker == 0xDA:
        break
    if pos + 2 > len(data):
        break
    seglen = struct.unpack(">H", data[pos:pos+2])[0]
    if seglen < 2 or pos + seglen > len(data):
        raise SystemExit("homev2 JPEG has an invalid segment")
    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
        if seglen < 7:
            raise SystemExit("homev2 JPEG SOF segment is too short")
        height = struct.unpack(">H", data[pos+3:pos+5])[0]
        width = struct.unpack(">H", data[pos+5:pos+7])[0]
        break
    pos += seglen

if not width or not height:
    raise SystemExit("homev2 JPEG dimensions could not be read")

destination = out / "ftf_home_screen_v2.jpg"
destination.write_bytes(data)
print(f"{destination.name}: {len(data)} bytes, {width}x{height}, {len(parts)} chunks")
