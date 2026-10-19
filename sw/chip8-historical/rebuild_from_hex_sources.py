#!/usr/bin/env python3
"""Rebuild 1979 Netronics CHIP-8 RAM tests from RCA VIP sources and Ipso Facto patch tables.
This NEVER generates a 32K AVI firmware image.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def read_hex(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        raw = bytes.fromhex(line.removeprefix(':'))
        assert line.startswith(':') and len(raw) == raw[0] + 5 and sum(raw) % 256 == 0, path
        if raw[3] == 1:
            assert raw[0] == 0
            continue
        assert raw[3] == 0
        offset = raw[1] * 256 + raw[2]
        for i, v in enumerate(raw[4:-1]):
            assert offset + i not in result
            result[offset+i] = v
    return result

def write_hex(path, arr):
    lines = []
    for a in range(0, len(arr), 16):
        b = bytes([min(16, len(arr)-a), a >> 8, a & 255, 0]) + arr[a:a+16]
        lines.append(':' + (b + bytes([-sum(b) & 255])).hex().upper())
    path.write_text('\n'.join(lines + [':00000001FF']) + '\n')

def load_512(path):
    values = read_hex(path)
    assert set(values) == set(range(512)), f'bad RCA source: {path}'
    return bytes(values[i] for i in range(512))

def rebuild():
    mem = bytearray(0xE00)
    chip = load_512(ROOT / 'vip-chip8-base.hex')
    rom = load_512(ROOT / 'vip-os-base.hex')
    assert chip[:4] == bytes.fromhex('91BBFF01')
    assert rom[:4] == bytes.fromhex('F880B2F8')
    mem[:512] = chip
    mem[0xC00:0xE00] = rom
    section = None
    counts = {'OS_TABLE1': 0, 'CHIP8_TABLE2': 0}
    for line in (ROOT / 'patches.txt').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            section = line.strip('[]')
            assert section in counts
            continue
        parts = line.split()
        assert section in counts and len(parts) == 9, line
        a = int(parts[0], 16)
        for s in parts[1:]:
            mem[a] = 0x10 if s == 'MODE' else int(s, 16)
            counts[section] += 1
            a += 1
    assert counts == {'OS_TABLE1': 232, 'CHIP8_TABLE2': 112}
    assert mem[0x10:0x18] == bytes.fromhex('B4F81BA4F801B5F8'), 'BOOT CODE CORRUPTED at $0010'
    assert mem[0x100:0x108] == bytes.fromhex('00000000F801B5F8'), 'MISSING TABLE 2 PATCH at $0100'
    assert mem[:3] == bytes.fromhex('C00C10')
    assert mem[0x1FA] == 0x9B
    assert mem[0xC70] == 0x69
    assert mem[0xC9E] == 0x0D and mem[0xCA1] == 0x46
    assert mem[0xB00:0xC00] == bytes(256)
    maze = bytearray(mem)
    maze[0x200:0x222] = bytes.fromhex('A21EC2013201A21AD014700430401200600071043120120012188040201020408010')
    squares = bytearray(mem)
    squares[0x200:0x21A] = bytes.fromhex('00E060086104A300D0186028D01860086114D0186028D0181218')
    squares[0x300:0x308] = bytes.fromhex('FF818181818181FF')
    assert (sum(maze) & 0xFFFF) == 0x07F7
    assert (sum(squares) & 0xFFFF) == 0x0D74
    for filename, image in (('Netronics-1979-CHIP8-Maze.hex', maze), ('Netronics-1979-CHIP8-Four-Squares.hex', squares)):
        write_hex(ROOT / filename, bytes(image))
        assert read_hex(ROOT / filename) == dict(enumerate(image))
        print('Verified', filename, len(image), 'bytes')
    print('NO ROM image modified; hardware validation pending')

if __name__ == '__main__':
    rebuild()
