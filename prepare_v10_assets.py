#!/usr/bin/env python3
from pathlib import Path
import base64
import struct
import zlib

root = Path(__file__).resolve().parent
src = root / 'binary_assets_v10'
out = root / 'generated_assets_v10'
out.mkdir(exist_ok=True)

assets = {
    'home': 'ftf_home_frog.png',
    'helmet': 'frog_helmet.png',
    'poison': 'ftf_poison_frog.png',
}


def validate_png(data: bytes, label: str) -> tuple[int, int]:
    sig = b'\x89PNG\r\n\x1a\n'
    if not data.startswith(sig):
        raise SystemExit(f'{label}: bad PNG signature')
    pos = 8
    width = height = None
    seen_iend = False
    while pos + 12 <= len(data):
        length = struct.unpack('>I', data[pos:pos+4])[0]
        kind = data[pos+4:pos+8]
        payload = data[pos+8:pos+8+length]
        crc_expected = struct.unpack('>I', data[pos+8+length:pos+12+length])[0]
        crc_actual = zlib.crc32(kind)
        crc_actual = zlib.crc32(payload, crc_actual) & 0xffffffff
        if crc_actual != crc_expected:
            raise SystemExit(f'{label}: corrupt PNG chunk {kind!r}')
        if kind == b'IHDR':
            width, height = struct.unpack('>II', payload[:8])
        if kind == b'IEND':
            seen_iend = True
            break
        pos += 12 + length
    if not seen_iend or not width or not height:
        raise SystemExit(f'{label}: incomplete PNG')
    return width, height

for prefix, filename in assets.items():
    parts = sorted(src.glob(f'{prefix}_*.b64'))
    if not parts:
        raise SystemExit(f'missing v10 chunks for {prefix}')
    encoded = ''.join(p.read_text().strip() for p in parts)
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f'{prefix}: base64 decode failed: {exc}')
    width, height = validate_png(data, prefix)
    destination = out / filename
    destination.write_bytes(data)
    print(f'{filename}: {len(data)} bytes, {width}x{height}, {len(parts)} chunks')
